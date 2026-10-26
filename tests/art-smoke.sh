#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ "${ANX_SKIP_BUILD:-0}" != "1" ]]; then
    bash scripts/build.sh
fi

DEX="$ROOT/build/dex/classes.dex"
if [[ ! -s "$DEX" ]]; then
    echo "[FAIL] DEX file is missing: $DEX" >&2
    echo "Install Android SDK Build-Tools, set D8=/path/to/d8, or set R8_JAR=/path/to/r8.jar, then rerun this script." >&2
    exit 1
fi

ART_CMD="${ART_CMD:-dalvikvm64}"
ART_BIN="$(command -v "$ART_CMD" 2>/dev/null || true)"
if [[ -z "$ART_BIN" || ! -x "$ART_BIN" ]]; then
    echo "[FAIL] ART executable '$ART_CMD' was not found or is not executable." >&2
    echo "Install a compatible host ART runtime and set ART_CMD=/path/to/dalvikvm64. See docs/build-art-host.md." >&2
    exit 1
fi

LOG_DIR="${ART_SMOKE_LOG_DIR:-$ROOT/build/art-smoke}"
export ANDROID_DATA="${ANDROID_DATA:-$ROOT/build/android-data}"
mkdir -p "$ANDROID_DATA" "$LOG_DIR"
HELLO_LOG="$LOG_DIR/hello-dex.log"
FRAMEWORK_LOG="$LOG_DIR/framework-launcher.log"
VERSION_LOG="$LOG_DIR/art-version.log"

echo "[art-smoke] ART executable: $(readlink -f "$ART_BIN" 2>/dev/null || printf '%s' "$ART_BIN")"
echo "[art-smoke] host: $(uname -srm)"
echo "[art-smoke] DEX: $DEX"
echo "[art-smoke] DEX SHA-256: $(sha256sum "$DEX" | cut -d ' ' -f 1)"
echo "[art-smoke] ANDROID_DATA: $ANDROID_DATA"

if "$ART_BIN" -showversion >"$VERSION_LOG" 2>&1; then
    :
else
    status=$?
    echo "[FAIL] ART version query failed (exit $status). Runtime output:" >&2
    cat "$VERSION_LOG" >&2
    exit "$status"
fi
cat "$VERSION_LOG"

failures=0
run_art_case() {
    local label="$1" log="$2" status=0 initial_failures
    shift 2
    local -a command_args=() expected=()
    while (($#)) && [[ "$1" != "--" ]]; do
        command_args+=("$1")
        shift
    done
    if (($#)); then shift; fi
    expected=("$@")
    initial_failures="$failures"

    if "$ART_BIN" -cp "$DEX" "${command_args[@]}" >"$log" 2>&1; then
        status=0
    else
        status=$?
    fi
    cat "$log"

    if ((status != 0)); then
        echo "[FAIL] $label exited with status $status. Runtime output: $log" >&2
        if grep -Fq 'JavaVM::GetEnv() failed' "$log"; then
            echo "[FAIL] The ART/libcore runtime aborted during JNI_OnUnload; this runtime does not pass the clean-shutdown gate." >&2
        fi
        failures=$((failures + 1))
    fi
    for text in "${expected[@]}"; do
        if ! grep -Fq "$text" "$log"; then
            echo "[FAIL] $label output did not contain: $text. See $log." >&2
            failures=$((failures + 1))
        fi
    done
    if ((failures == initial_failures)); then
        echo "[PASS] $label. Log: $log"
    fi
}

run_art_case \
    'Standalone DEX' "$HELLO_LOG" \
    org.demo.HelloDex -- \
    '[hello-dex] ART executed DEX bytecode.'
run_art_case \
    'ANX framework lifecycle' "$FRAMEWORK_LOG" \
    org.anx.launcher.Main org.demo.HelloActivity -- \
    '[anx] onCreate' \
    '[anx] onStart' \
    '[anx] onResume' \
    '[linux-console-backend] TextView: Halo dari API Android minimal!' \
    '[anx] onDestroy'

if ((failures)); then
    echo "[FAIL] ART smoke test recorded $failures failure(s)." >&2
    exit 1
fi
