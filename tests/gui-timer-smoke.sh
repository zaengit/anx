#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
mkdir -p build/test-gui-timer
find src/main/java src/demo/java -name '*.java' -print > build/test-gui-timer-sources.txt
javac --release 8 -encoding UTF-8 -d build/test-gui-timer @build/test-gui-timer-sources.txt
cat > build/mock-timer-wayland <<'MOCK'
#!/usr/bin/env bash
set -euo pipefail
printf 'READY\n'
sleep 0.35
printf 'PULSE\n'
IFS= read -r update
printf '%s\n' "$update" > "$ANX_TIMER_CAPTURE"
printf 'UPDATED\nCLOSE\n'
MOCK
chmod +x build/mock-timer-wayland
ANX_BACKEND=wayland \
ANX_WAYLAND_BINARY="$ROOT/build/mock-timer-wayland" \
ANX_TIMER_CAPTURE="$ROOT/build/timer-update.txt" \
ANX_GUI_TEST_CLOSE_ON_UPDATE=1 \
ANX_APP_DATA_HOME="$ROOT/build/timer-app-data" \
timeout 20 java -cp build/test-gui-timer \
    org.anx.launcher.Main org.demo.TimerActivity org.demo org.demo.HelloApplication \
    > build/gui-timer.out
grep -Fq '[demo] Delayed Handler fired' build/gui-timer.out
grep -Fq '[anx-wayland] label updated' build/gui-timer.out
grep -Fq '[anx] onDestroy' build/gui-timer.out
python3 - <<'PY'
import base64
from pathlib import Path
line = Path("build/timer-update.txt").read_text().strip()
assert line.startswith("TEXT\t"), line
assert base64.b64decode(line[5:]).decode() == "Delayed callback fired", line
PY
echo '[PASS] Looper.postDelayed repaints the GUI without a user click.'
