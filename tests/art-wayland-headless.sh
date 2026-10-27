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
    if [[ -n "${WESTON_PID:-}" ]]; then
        kill "$WESTON_PID" 2>/dev/null || true
        wait "$WESTON_PID" 2>/dev/null || true
    fi
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
    --unsafe-host-execution --art "$ART_CMD" --backend wayland \
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

# A separate APK class exercises Handler.postDelayed during an idle Wayland window.
unset ANX_GUI_TEST_AUTOCLICK
export ANX_GUI_TEST_CLOSE_ON_UPDATE=1
export ANX_BACKEND=wayland
export ANX_WAYLAND_BINARY="$NATIVE_BIN"
export ANDROID_DATA="$RUNTIME/android-data"
export ANX_APP_DATA_HOME="$RUNTIME/apps"
if ! timeout 40 "$ART_CMD" -cp "$ROOT/build/framework/classes.dex:$ROOT/build/demo.apk" \
    org.anx.launcher.Main org.demo.TimerActivity org.demo org.demo.HelloApplication \
    "$ROOT/build/demo.apk" >"$LOG_DIR/art-wayland-timer.log" 2>&1; then
    cat "$LOG_DIR/art-wayland-timer.log" >&2
    echo '[FAIL] ART Wayland timer integration' >&2
    exit 1
fi
for expected in \
    '[demo] Delayed Handler fired' \
    '[anx-wayland] window ready' \
    '[anx-wayland] label updated' \
    '[anx-wayland] window closed' \
    '[anx] onDestroy'; do
    grep -Fq "$expected" "$LOG_DIR/art-wayland-timer.log" || {
        cat "$LOG_DIR/art-wayland-timer.log" >&2
        echo "[FAIL] Missing ART timer output: $expected" >&2
        exit 1
    }
done
echo '[PASS] Host ART scheduled Handler callback advanced on live Wayland compositor.'

# Actual Java bytecode below was compiled against the SDK android.jar, not
# against ANX classes. The same GUI bridge must accept a real API ABI.
unset ANX_GUI_TEST_CLOSE_ON_UPDATE
export ANX_GUI_TEST_AUTOCLICK=1
if ! timeout 40 python3 scripts/anx.py run build/external.apk \
    --unsafe-host-execution --art "$ART_CMD" --backend wayland \
    --wayland-binary "$NATIVE_BIN" \
    --framework-dex build/framework/classes.dex \
    --android-data "$RUNTIME/android-data" \
    > "$LOG_DIR/external-art-wayland.log" 2>&1; then
    cat "$LOG_DIR/external-art-wayland.log" >&2
    echo '[FAIL] Official Android SDK APK and ART GUI failed' >&2
    exit 1
fi
for expected in \
    '[android/INFO] External: SDK ABI matched: org.anx.external' \
    '[anx-wayland] window ready' \
    '[external] click updated label' \
    '[anx-wayland] label updated' \
    '[anx-wayland] window closed'; do
    grep -Fq "$expected" "$LOG_DIR/external-art-wayland.log" || {
        cat "$LOG_DIR/external-art-wayland.log" >&2
        echo "[FAIL] Missing external APK evidence: $expected" >&2
        exit 1
    }
done
echo '[PASS] SDK-compiled external APK runs on host ART and native GTK Wayland.'

# Nested Java Activity compiled against Android SDK uses findViewById
# and a click listener attached after the compiled XML tree is inflated.
if ! timeout 40 python3 scripts/anx.py run build/nested-fixture.apk \
    --unsafe-host-execution --art "$ART_CMD" --backend wayland \
    --wayland-binary "$NATIVE_BIN" \
    --framework-dex build/framework/classes.dex \
    --android-data "$RUNTIME/android-data" \
    > "$LOG_DIR/nested-art-wayland.log" 2>&1; then
    cat "$LOG_DIR/nested-art-wayland.log" >&2
    echo '[FAIL] Nested XML SDK APK on ART and GTK Wayland' >&2
    exit 1
fi
for expected in \
    '[nested] XML hierarchy and IDs resolved' \
    '[anx-wayland] window ready' \
    '[nested] invalid XML callback rejected' \
    '[nested] XML android:onClick updated label' \
    '[anx-wayland] button clicked' \
    '[anx-wayland] label updated' \
    '[anx-wayland] window closed'; do
    grep -Fq "$expected" "$LOG_DIR/nested-art-wayland.log" || {
        cat "$LOG_DIR/nested-art-wayland.log" >&2
        echo "[FAIL] Missing nested XML ART/Wayland evidence: $expected" >&2
        exit 1
    }
done
echo '[PASS] SDK-compiled nested XML inflates, findViewById binds, GTK click repaints.'

# Genuine independent Apache-2.0 app, unmodified from upstream.
unset ANX_GUI_TEST_AUTOCLICK
export ANX_GUI_TEST_AUTOCLOSE_TEXT_ONLY=1
if ! timeout 40 python3 scripts/anx.py run build/chiuki-third-party.apk \
    --unsafe-host-execution --art "$ART_CMD" --backend wayland \
    --wayland-binary "$NATIVE_BIN" \
    --framework-dex build/framework/classes.dex \
    --android-data "$RUNTIME/android-data" \
    > "$LOG_DIR/third-party-art-wayland.log" 2>&1; then
    cat "$LOG_DIR/third-party-art-wayland.log" >&2
    echo '[FAIL] Independent Apache-2.0 APK on ART + GTK Wayland' >&2
    exit 1
fi
for expected in \
    '[anx-wayland] window ready' \
    '[anx-wayland] text-only GTK label verified' \
    '[anx-wayland] window closed' \
    '[anx] onDestroy'; do
    grep -Fq "$expected" "$LOG_DIR/third-party-art-wayland.log" || {
        cat "$LOG_DIR/third-party-art-wayland.log" >&2
        echo "[FAIL] Third-party Wayland log absent: $expected" >&2
        exit 1
    }
done
echo '[PASS] Genuine independently authored APK XML TextView rendered in GTK Wayland.'

