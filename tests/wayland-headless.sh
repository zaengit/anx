#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
[[ -x build/native/anx-wayland ]] || { echo 'Build the backend first.' >&2; exit 1; }
command -v weston >/dev/null || { echo 'Weston is required.' >&2; exit 1; }
mkdir -p build
RUNTIME="$(mktemp -d)"
chmod 700 "$RUNTIME"
cleanup() {
    if [[ -n "${WESTON_PID:-}" ]]; then kill "$WESTON_PID" 2>/dev/null || true; fi
    rm -rf "$RUNTIME"
}
trap cleanup EXIT
XDG_RUNTIME_DIR="$RUNTIME" weston --backend=headless-backend.so \
    --socket=anx-ci --no-config --idle-time=0 > build/weston-headless.out 2>&1 &
WESTON_PID=$!
for i in $(seq 1 60); do
    [[ -S "$RUNTIME/anx-ci" ]] && break
    sleep 0.25
done
if [[ ! -S "$RUNTIME/anx-ci" ]]; then
    cat build/weston-headless.out >&2
    echo '[FAIL] Weston socket missing' >&2
    exit 1
fi
{ sleep 1; } | env XDG_RUNTIME_DIR="$RUNTIME" WAYLAND_DISPLAY=anx-ci \
    GSK_RENDERER=cairo timeout 20 build/native/anx-wayland \
    "ANX CI" "TextView render test" "Button render test" > build/wayland-headless.out
grep -Fxq READY build/wayland-headless.out
grep -Fxq CLOSE build/wayland-headless.out
echo '[PASS] Native GTK4 client connected and exited under Weston headless.'
