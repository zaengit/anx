#!/usr/bin/env bash
# ART + APK: compositor virtual pointer into real GTK Wayland, no GTK signal synthesis.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
for binary in sway swaymsg jq dbus-run-session; do command -v "$binary" >/dev/null || exit 1; done
ART_CMD="${ART_CMD:-dalvikvm64}"
LOG_DIR="${ART_SMOKE_LOG_DIR:-$ROOT/build/art-smoke}"
NATIVE_BIN="${ANX_WAYLAND_BINARY:-$LOG_DIR/native/anx-wayland}"
POINTER_BIN="${ANX_VIRTUAL_POINTER_BINARY:-$LOG_DIR/native/anx-virtual-pointer}"
[[ -x "$NATIVE_BIN" && -x "$POINTER_BIN" && -f build/nested-fixture.apk && -f build/framework/classes.dex ]]
mkdir -p "$LOG_DIR"
RUNTIME="$(mktemp -d)"
chmod 700 "$RUNTIME"
SWAY_PID= APP_PID= POINTER_PID= POINTER_FD=
cleanup() {
    if [[ -n "$APP_PID" ]]; then kill "$APP_PID" 2>/dev/null || :; wait "$APP_PID" 2>/dev/null || :; fi
    if [[ -n "$POINTER_PID" ]]; then kill "$POINTER_PID" 2>/dev/null || :; wait "$POINTER_PID" 2>/dev/null || :; fi
    if [[ -n "$SWAY_PID" ]]; then kill "$SWAY_PID" 2>/dev/null || :; wait "$SWAY_PID" 2>/dev/null || :; fi
    rm -rf "$RUNTIME"
}
trap cleanup EXIT
cat > "$RUNTIME/sway.conf" <<'CONF'
output HEADLESS-1 resolution 1280x720
xwayland disable
default_border none
default_floating_border none
focus_follows_mouse yes
seat seat0 fallback true
CONF
export XDG_RUNTIME_DIR="$RUNTIME" SWAYSOCK="$RUNTIME/anx-sway-ipc.sock"
export WLR_BACKENDS=headless WLR_RENDERER=pixman
export WLR_HEADLESS_OUTPUTS=1 WLR_LIBINPUT_NO_DEVICES=1
export GDK_BACKEND=wayland GSK_RENDERER=cairo
unset DISPLAY WAYLAND_DISPLAY
dbus-run-session -- sway -c "$RUNTIME/sway.conf" --unsupported-gpu \
    > "$LOG_DIR/art-sway-compositor.log" 2>&1 &
SWAY_PID=$!
for i in $(seq 1 120); do
    [[ -S "$SWAYSOCK" ]] && break
    if ! kill -0 "$SWAY_PID" 2>/dev/null; then break; fi
    sleep 0.2
done
if [[ ! -S "$SWAYSOCK" ]]; then cat "$LOG_DIR/art-sway-compositor.log" >&2; exit 1; fi
for i in $(seq 1 30); do
    WAYLAND_DISPLAY=
    for socket in "$RUNTIME"/wayland-*; do
        [[ -S "$socket" ]] && { WAYLAND_DISPLAY="${socket##*/}"; break; }
    done
    [[ -n "$WAYLAND_DISPLAY" ]] && break
    sleep 0.2
done
[[ -n "${WAYLAND_DISPLAY:-}" ]] || { cat "$LOG_DIR/art-sway-compositor.log" >&2; exit 1; }
export WAYLAND_DISPLAY
swaymsg -r -t get_outputs > "$LOG_DIR/art-sway-outputs.json"
jq -e 'any(.[]; .active == true)' "$LOG_DIR/art-sway-outputs.json" >/dev/null

# A persistent wlroots virtual-pointer creates the seat capability GTK needs.
# One-shot pointer commands would add and remove that capability too quickly.
coproc ANX_POINTER {
    "$POINTER_BIN" > "$RUNTIME/pointer.log" 2>&1
}
POINTER_PID="$ANX_POINTER_PID"
POINTER_FD="${ANX_POINTER[1]}"
for i in $(seq 1 100); do
    grep -Fxq READY "$RUNTIME/pointer.log" && break
    if ! kill -0 "$POINTER_PID" 2>/dev/null; then break; fi
    sleep 0.1
done
if ! grep -Fxq READY "$RUNTIME/pointer.log"; then
    cat "$RUNTIME/pointer.log" >&2
    echo '[FAIL] Persistent virtual pointer did not initialize' >&2
    exit 1
fi
swaymsg -r -t get_seats > "$LOG_DIR/art-sway-seats.json"

# Only a real Wayland click should produce a Java label update and close GTK.
unset ANX_GUI_TEST_AUTOCLICK ANX_GUI_TEST_LONGPRESS_TEXT_ONLY
export ANX_GUI_TEST_CLOSE_ON_UPDATE=1 ANX_GUI_TEST_REPORT_BUTTON_GEOMETRY=1
export ANX_BACKEND=wayland ANX_WAYLAND_BINARY="$NATIVE_BIN"
timeout 55 python3 scripts/anx.py run build/nested-fixture.apk \
    --unsafe-host-execution --art "$ART_CMD" --backend wayland \
    --wayland-binary "$NATIVE_BIN" \
    --framework-dex build/framework/classes.dex \
    --android-data "$RUNTIME/android-data" \
    > "$LOG_DIR/art-sway-app.log" 2>&1 &
APP_PID=$!
target= geometry=
for i in $(seq 1 120); do
    if ! kill -0 "$APP_PID" 2>/dev/null; then break; fi
    target="$(sed -n 's/^ANX_POINTER_TARGET \([0-9]*\) \([0-9]*\)$/\1 \2/p' "$LOG_DIR/art-sway-app.log" | tail -1)"
    geometry="$(swaymsg -r -t get_tree | jq -r '[.. | objects | select((.app_id? == "org.anx.wayland") or (.name? == "ANX: org.anx.nested")) | .rect] | last // empty | "\(.x) \(.y) \(.width) \(.height)"' || :)"
    if [[ -n "$target" && -n "$geometry" ]]; then break; fi
    sleep 0.2
done
if [[ -z "$target" || -z "$geometry" ]]; then
    echo '[anx-test] Sway active window tree:' >&2
    swaymsg -r -t get_tree | jq -c '[.. | objects | select(.type? == "con") | {name,app_id,rect}]' >&2 || :
    cat "$LOG_DIR/art-sway-app.log" >&2
    cat "$LOG_DIR/art-sway-compositor.log" >&2
    echo '[FAIL] GTK geometry or Sway Wayland window unavailable' >&2
    exit 1
fi
read -r local_x local_y <<< "$target"
read -r win_x win_y win_w win_h <<< "$geometry"
screen_x=$((win_x + local_x)) screen_y=$((win_y + local_y))
echo "[anx-test] window=$geometry button=$target global=$screen_x,$screen_y"
if ((local_x <= 0 || local_y <= 0 || local_x >= win_w || local_y >= win_h)); then
    echo '[FAIL] GTK/Sway button outside window' >&2
    exit 1
fi
for command in "move $screen_x $screen_y" down up; do
    printf '%s\n' "$command" >&"$POINTER_FD"
    sleep 0.25
done
if ! kill -0 "$POINTER_PID" 2>/dev/null; then
    cat "$RUNTIME/pointer.log" >&2
    echo '[FAIL] Persistent virtual pointer exited early' >&2
    exit 1
fi
if ! wait "$APP_PID"; then cat "$LOG_DIR/art-sway-app.log" >&2; exit 1; fi
APP_PID=
for expected in \
    '[nested] XML hierarchy and IDs resolved' \
    '[nested] XML android:onClick updated label' \
    '[anx-wayland] window ready' \
    '[anx-wayland] button clicked' \
    '[anx-wayland] label updated' \
    '[anx-wayland] window closed' \
    '[anx] onDestroy'; do
    grep -Fq "$expected" "$LOG_DIR/art-sway-app.log" || {
        cat "$LOG_DIR/art-sway-app.log" >&2
        echo "[FAIL] Missing callback: $expected" >&2
        exit 1
    }
done
echo '[PASS] ART + official-SDK nested APK received compositor-generated GTK button event and repainted TextView.'
