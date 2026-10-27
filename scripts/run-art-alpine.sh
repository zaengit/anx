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
        grep -Fq "[android/INFO] ANX: Own package: org.demo" /anx/build/art-smoke/apk-run.log
        grep -Fq "[anx] onCreate" /anx/build/art-smoke/apk-run.log
        grep -Fq "[linux-console-backend] TextView: Halo dari API Android minimal!" /anx/build/art-smoke/apk-run.log
        grep -Fq "[anx] onDestroy" /anx/build/art-smoke/apk-run.log
        echo "[PASS] Standalone demo APK loaded from its own DEX on ART. Log: build/art-smoke/apk-run.log"
        if ! python3 scripts/anx.py run build/external.apk --unsafe-host-execution \
            --art "$art_cmd" --backend console \
            --framework-dex build/framework/classes.dex \
            --android-data /tmp/anx-external-data \
            > /anx/build/art-smoke/external-apk-run.log 2>&1; then
            cat /anx/build/art-smoke/external-apk-run.log >&2
            exit 1
        fi
        grep -Fq "[android/INFO] External: SDK ABI matched: org.anx.external" \
            /anx/build/art-smoke/external-apk-run.log
        grep -Fq "[linux-console-backend] TextView: External APK from Android SDK" \
            /anx/build/art-smoke/external-apk-run.log
        grep -Fq "[external] color and dimension resources ok" \
            /anx/build/art-smoke/external-apk-run.log
        grep -Fq "[external] resource references resolved" \
            /anx/build/art-smoke/external-apk-run.log
        grep -Fq "[external] boolean integer and formatted strings ok" \
            /anx/build/art-smoke/external-apk-run.log
        echo "[PASS] Official Android SDK ABI APK executed its Application and Activity on ART."
        if ! python3 scripts/anx.py run build/multidex-fixture.apk \
            --unsafe-host-execution --art "$art_cmd" --backend console \
            --framework-dex build/framework/classes.dex \
            --android-data /tmp/anx-multidex-data \
            > /anx/build/art-smoke/multidex-run.log 2>&1; then
            cat /anx/build/art-smoke/multidex-run.log >&2
            exit 1
        fi
        grep -Fq "[anx] secondary DEX files: 1" /anx/build/art-smoke/multidex-run.log
        grep -Fq "[external] DEX helper: loaded-from-classes2" /anx/build/art-smoke/multidex-run.log
        grep -Fq "[anx] onDestroy" /anx/build/art-smoke/multidex-run.log
        echo "[PASS] Host ART resolved an SDK-compiled Java method from classes2.dex."
        if ! python3 scripts/anx.py run build/chiuki-third-party.apk \
            --unsafe-host-execution --art "$art_cmd" --backend console \
            --framework-dex build/framework/classes.dex \
            --android-data /tmp/anx-third-party-data \
            > /anx/build/art-smoke/chiuki-third-party.log 2>&1; then
            cat /anx/build/art-smoke/chiuki-third-party.log >&2
            exit 1
        fi
        grep -Fq "[linux-console-backend] TextView: Hello world!" /anx/build/art-smoke/chiuki-third-party.log
        grep -Fq "[anx] onDestroy" /anx/build/art-smoke/chiuki-third-party.log
        echo "[PASS] Unmodified Apache-2.0 third-party source runs using XML TextView on ART."
        if ! python3 scripts/anx.py run build/nested-fixture.apk \
            --unsafe-host-execution --art "$art_cmd" --backend console \
            --framework-dex build/framework/classes.dex \
            --android-data /tmp/anx-nested-data \
            > /anx/build/art-smoke/nested-apk.log 2>&1; then
            cat /anx/build/art-smoke/nested-apk.log >&2
            exit 1
        fi
        grep -Fq "[nested] XML hierarchy and IDs resolved" /anx/build/art-smoke/nested-apk.log
        grep -Fq "[nested] invalid XML callback rejected" /anx/build/art-smoke/nested-apk.log
        grep -Fq "[linux-console-backend] TextView: Nested XML ready" /anx/build/art-smoke/nested-apk.log
        grep -Fq "[linux-console-backend] Button: Update nested" /anx/build/art-smoke/nested-apk.log
        grep -Fq "[anx] onDestroy" /anx/build/art-smoke/nested-apk.log
        echo "[PASS] SDK APK nested XML view IDs, text and button on host ART."
        if ! python3 scripts/anx.py run build/self-aware-third-party.apk \
            --unsafe-host-execution --art "$art_cmd" --backend console \
            --framework-dex build/framework/classes.dex \
            --android-data /tmp/anx-self-aware-data \
            > /anx/build/art-smoke/self-aware-third-party.log 2>&1; then
            cat /anx/build/art-smoke/self-aware-third-party.log >&2
            exit 1
        fi
        grep -Fq "[linux-console-backend] TextView: hello world" \
            /anx/build/art-smoke/self-aware-third-party.log
        grep -Fq "anx-host-not-an-android-device" /anx/build/art-smoke/self-aware-third-party.log
        grep -Fq "ANX-host-compatibility" /anx/build/art-smoke/self-aware-third-party.log
        grep -Fq "[anx] onDestroy" /anx/build/art-smoke/self-aware-third-party.log
        echo "[PASS] Second independently authored MIT APK runs with synthetic device metadata on host ART."
        ART_CMD="$art_cmd" ART_SMOKE_LOG_DIR=/anx/build/art-smoke bash tests/art-gui-protocol.sh
        ART_CMD="$art_cmd" ART_SMOKE_LOG_DIR=/anx/build/art-smoke bash tests/art-jni-smoke.sh
        ANX_NATIVE_OUTPUT_DIR=/anx/build/art-smoke/native bash scripts/build-wayland.sh
        ANX_WAYLAND_BINARY=/anx/build/art-smoke/native/anx-wayland ART_CMD="$art_cmd" ART_SMOKE_LOG_DIR=/anx/build/art-smoke bash tests/art-wayland-headless.sh
    '
