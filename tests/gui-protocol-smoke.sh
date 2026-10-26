#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
mkdir -p build/classes
find src/main/java src/demo/java -name '*.java' -print > build/gui-sources.txt
javac --release 8 -encoding UTF-8 -d build/classes @build/gui-sources.txt
cat > build/mock-wayland <<'MOCK'
#!/usr/bin/env bash
set -euo pipefail
printf 'READY\nCLICK\n'
IFS= read -r payload
printf '%s\n' "$payload" > "$ANX_PROTOCOL_CAPTURE"
printf 'CLOSE\n'
MOCK
chmod +x build/mock-wayland
ANX_BACKEND=wayland ANX_WAYLAND_BINARY="$ROOT/build/mock-wayland" \
    ANX_PROTOCOL_CAPTURE="$ROOT/build/wayland-protocol.out" \
    java -cp build/classes org.anx.launcher.Main \
    org.demo.HelloActivity org.demo org.demo.HelloApplication > build/gui-protocol-smoke.out
grep -Fq '[anx-wayland] window ready' build/gui-protocol-smoke.out
grep -Fq '[anx-wayland] button clicked' build/gui-protocol-smoke.out
grep -Fq '[anx-wayland] window closed' build/gui-protocol-smoke.out
grep -Fq '[anx] onDestroy' build/gui-protocol-smoke.out
python3 - <<'PY'
import base64
from pathlib import Path
raw = Path('build/wayland-protocol.out').read_text().strip()
assert raw.startswith('TEXT\t'), raw
assert base64.b64decode(raw[5:]).decode() == 'Tombol berhasil diklik!', raw
PY
echo '[PASS] GUI bridge click dispatch, label repaint, and clean lifecycle.'
