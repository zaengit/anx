#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
mkdir -p build/sandbox-mock
cat > build/sandbox-mock/bwrap <<'MOCK'
#!/bin/sh
: "${ANX_BWRAP_TRACE:?}"
printf '%s\n' "$@" > "$ANX_BWRAP_TRACE"
exit 42
MOCK
chmod +x build/sandbox-mock/bwrap
TRACE="$ROOT/build/sandbox-options.txt"
rm -f "$TRACE"
set +e
PATH="$ROOT/build/sandbox-mock:$PATH" ANX_BWRAP_TRACE="$TRACE" \
    python3 scripts/anx.py run build/demo.apk \
    --art /usr/bin/true --framework-dex build/framework/classes.dex \
    --backend console --unsafe-host-execution --experimental-sandbox \
    > build/sandbox-mock.out 2>&1
status=$?
set -e
if [[ $status -ne 42 ]]; then
    cat build/sandbox-mock.out >&2
    echo "[FAIL] Sandbox command exit code $status (expected 42)" >&2
    exit 1
fi
test -s "$TRACE"
grep -Fxq -- '--unshare-all' "$TRACE"
grep -Fxq -- '--clearenv' "$TRACE"
grep -Fxq -- '--bind' "$TRACE"
if grep -Fxq -- '--share-net' "$TRACE"; then
    echo "[FAIL] Sandbox must never inherit the network" >&2
    exit 1
fi
grep -Fxq -- '/anx/app.apk' "$TRACE"
grep -Fxq -- '/anx/data' "$TRACE"
grep -Fxq -- '/anx/apps' "$TRACE"
echo '[PASS] Bubblewrap argv tested, failure propagates, no silent unsandboxed fallback.'

if python3 scripts/anx.py run build/demo.apk \
    --art /usr/bin/true --framework-dex build/framework/classes.dex \
    --backend wayland --unsafe-host-execution --experimental-sandbox \
    > build/sandbox-gui-denied.out 2>&1; then
    echo '[FAIL] Sandbox accepted unsupported Wayland socket sharing' >&2
    exit 1
fi
grep -Fq 'supports --backend console only' build/sandbox-gui-denied.out
echo '[PASS] Experimental sandbox refuses unsupported Wayland execution.'
