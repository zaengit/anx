#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
ART_CMD="${ART_CMD:-dalvikvm64}"
LOG_DIR="${ART_SMOKE_LOG_DIR:-$ROOT/build/art-smoke}"
mkdir -p "$LOG_DIR"
MOCK="$LOG_DIR/mock-wayland.sh"
CAPTURE="$LOG_DIR/art-wayland-protocol.txt"
LOG="$LOG_DIR/art-wayland-bridge.log"
cat >"$MOCK" <<'MOCK_SCRIPT'
#!/bin/sh
set -eu
printf 'READY\nCLICK\n'
IFS= read -r line
printf '%s\n' "$line" > "$ANX_PROTOCOL_CAPTURE"
printf 'CLOSE\n'
MOCK_SCRIPT
chmod +x "$MOCK"
export ANX_PROTOCOL_CAPTURE="$CAPTURE"
python3 scripts/anx.py run build/demo.apk \
    --art "$ART_CMD" --backend wayland --wayland-binary "$MOCK" \
    --framework-dex build/framework/classes.dex \
    --android-data "${ANDROID_DATA:-/tmp/anx-art-gui-data}" > "$LOG" 2>&1 || {
    cat "$LOG" >&2
    exit 1
}
grep -Fq '[anx-wayland] window ready' "$LOG"
grep -Fq '[anx-wayland] button clicked' "$LOG"
grep -Fq '[anx-wayland] window closed' "$LOG"
grep -Fq '[anx] onDestroy' "$LOG"
python3 - <<'PY'
import base64
import os
from pathlib import Path
text = Path(os.environ['ANX_PROTOCOL_CAPTURE']).read_text().strip()
assert text.startswith('TEXT\t'), text
assert base64.b64decode(text[5:]).decode('utf-8') == 'Tombol berhasil diklik!', text
PY
echo '[PASS] ART DEX APK -> external Wayland protocol -> Java Button callback -> repaint.'
