#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
NATIVE_BIN="${ANX_WAYLAND_BINARY:-$ROOT/build/native/anx-wayland}"
[[ -x "$NATIVE_BIN" ]] || { echo "Missing native backend: $NATIVE_BIN" >&2; exit 1; }
command -v weston >/dev/null || { echo 'Missing Weston' >&2; exit 1; }
ART_CMD="${ART_CMD:-dalvikvm64}"
LOG_DIR="${ART_SMOKE_LOG_DIR:-$ROOT/build/art-smoke}"
mkdir -p "$LOG_DIR"
RUNTIME="$(mktemp -d)"
chmod 700 "$RUNTIME"
cleanup() {
    if [[ -n "${WESTON_PID:-}" ]]; then kill "$WESTON_PID" 2>/dev/null || true; fi
    rm -rf "$RUNTIME"
}
trap cleanup EXIT
XDG_RUNTIME_DIR="$RUNTIME" weston --backend=headless-backend.so \
    --socket=anx-art-headless --no-config --idle-time=0 \
    >"$LOG_DIR/art-weston.log" 2>&1 &
WESTON_PID=$!
for i in $(seq 1 80); do
    [[ -S "$RUNTIME/anx-art-headless" ]] && break
    if ! kill -0 "$WESTON_PID" 2>/dev/null; then break; fi
    sleep 0.25
done
if [[ ! -S "$RUNTIME/anx-art-headless" ]]; then
    cat "$LOG_DIR/art-weston.log" >&2
    echo '[FAIL] Headless Weston did not start' >&2
    exit 1
fi
export XDG_RUNTIME_DIR="$RUNTIME"
export WAYLAND_DISPLAY=anx-art-headless
export GDK_BACKEND=wayland
export GSK_RENDERER=cairo
export ANX_GUI_TEST_AUTOCLICK=1
if ! timeout 40 python3 scripts/anx.py run build/demo.apk \
    --art "$ART_CMD" --backend wayland \
    --wayland-binary "$NATIVE_BIN" \
    --framework-dex build/framework/classes.dex \
    --android-data "$RUNTIME/android-data" \
    >"$LOG_DIR/art-wayland-e2e.log" 2>&1; then
    cat "$LOG_DIR/art-wayland-e2e.log" >&2
    cat "$LOG_DIR/art-weston.log" >&2
    echo '[FAIL] ART + GTK4 + Weston integration' >&2
    exit 1
fi
for expected in \
    '[demo] Application ready: org.demo' \
    '[anx-wayland] window ready' \
    '[anx-wayland] button clicked' \
    '[anx-wayland] label updated' \
    '[anx-wayland] window closed' \
    '[anx] onDestroy'; do
    grep -Fq "$expected" "$LOG_DIR/art-wayland-e2e.log" || {
        cat "$LOG_DIR/art-wayland-e2e.log" >&2
        echo "[FAIL] Missing ART/Wayland log: $expected" >&2
        exit 1
    }
done
cat "$LOG_DIR/art-wayland-e2e.log"
echo '[PASS] Standalone APK on host ART, live GTK4 Wayland window, synthetic GTK click, label repaint, clean close.'
