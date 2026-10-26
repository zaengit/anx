#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

CONTAINER_ENGINE="${CONTAINER_ENGINE:-podman}"
ART_IMAGE="${ANX_ART_IMAGE:-localhost/anx-art-smoke:0_git20261018-r0}"

if ! command -v "$CONTAINER_ENGINE" >/dev/null 2>&1; then
    echo "Container engine '$CONTAINER_ENGINE' was not found. Install Podman or set CONTAINER_ENGINE." >&2
    exit 1
fi

bash scripts/build.sh
bash tests/apk-inspect-smoke.sh
if [[ ! -s "$ROOT/build/dex/classes.dex" ]]; then
    echo "DEX file was not generated. Install Android SDK Build-Tools or set D8/R8_JAR, then retry." >&2
    exit 1
fi
mkdir -p "$ROOT/build/art-smoke"

echo "[art-container] building patched ART reference image: $ART_IMAGE"
"$CONTAINER_ENGINE" build \
    --file "$ROOT/containers/art-smoke/Containerfile" \
    --tag "$ART_IMAGE" \
    "$ROOT"
echo "[art-container] image: $ART_IMAGE"
echo "[art-container] ART source commit: a1edfc40e8cea3644d80e4e776d3fa7fc397a1c2 (with local JNI_OnUnload fix)"
"$CONTAINER_ENGINE" run --rm \
    --security-opt label=disable \
    --volume "$ROOT:/anx:ro" \
    --volume "$ROOT/build/art-smoke:/anx/build/art-smoke:rw" \
    --workdir /anx \
    "$ART_IMAGE" \
    sh -ec '
        if command -v dalvikvm64 >/dev/null 2>&1; then
            art_cmd="$(command -v dalvikvm64)"
        else
            art_cmd="$(command -v dalvikvm)"
        fi
        env \
            ART_CMD="$art_cmd" \
            ANX_SKIP_BUILD=1 \
            ANDROID_DATA=/tmp/anx-art-data \
            ART_SMOKE_LOG_DIR=/anx/build/art-smoke \
            bash tests/art-smoke.sh
        if python3 scripts/anx.py run \
            --unsafe-host-execution \
            --art "$art_cmd" \
            --framework-dex build/framework/classes.dex \
            --android-data /tmp/anx-app-data \
            build/demo.apk > /anx/build/art-smoke/apk-run.log 2>&1; then
            cat /anx/build/art-smoke/apk-run.log
        else
            status=$?
            cat /anx/build/art-smoke/apk-run.log >&2
            exit "$status"
        fi
        grep -Fq "[anx] Application.onCreate" /anx/build/art-smoke/apk-run.log
        grep -Fq "[demo] Application ready: org.demo" /anx/build/art-smoke/apk-run.log
        grep -Fq "[anx] onCreate" /anx/build/art-smoke/apk-run.log
        grep -Fq "[linux-console-backend] TextView: Halo dari API Android minimal!" /anx/build/art-smoke/apk-run.log
        grep -Fq "[anx] onDestroy" /anx/build/art-smoke/apk-run.log
        echo "[PASS] Standalone demo APK loaded from its own DEX on ART. Log: build/art-smoke/apk-run.log"
        ART_CMD="$art_cmd" ART_SMOKE_LOG_DIR=/anx/build/art-smoke bash tests/art-gui-protocol.sh
        ANX_NATIVE_OUTPUT_DIR=/anx/build/art-smoke/native bash scripts/build-wayland.sh
        ANX_WAYLAND_BINARY=/anx/build/art-smoke/native/anx-wayland ART_CMD="$art_cmd" ART_SMOKE_LOG_DIR=/anx/build/art-smoke bash tests/art-wayland-headless.sh
    '
