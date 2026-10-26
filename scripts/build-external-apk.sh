#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
SDK_ROOT="${ANDROID_SDK_ROOT:-${ANDROID_HOME:-${HOME:-}/Android/Sdk}}"
resolve_tool() {
    local override="$1" tool="$2" found=""
    if [[ -n "$override" ]]; then
        found="$(command -v "$override" 2>/dev/null || true)"
        [[ -n "$found" ]] || [[ -x "$override" ]] && found="$override"
    else
        found="$(command -v "$tool" 2>/dev/null || true)"
        if [[ -z "$found" ]]; then
            found="$(find "$SDK_ROOT/build-tools" -mindepth 2 -maxdepth 2 \
                -type f -name "$tool" -print 2>/dev/null | sort -V | tail -n 1)"
        fi
    fi
    [[ -n "$found" && -x "$found" ]] || {
        echo "Missing Android SDK tool: $tool" >&2
        return 1
    }
    printf '%s\n' "$found"
}
D8_CMD="$(resolve_tool "${D8:-}" d8)"
AAPT_CMD="$(resolve_tool "${AAPT:-}" aapt)"
ANDROID_JAR="${ANDROID_JAR:-}"
if [[ -z "$ANDROID_JAR" ]]; then
    ANDROID_JAR="$(find "$SDK_ROOT/platforms" -mindepth 2 -maxdepth 2 \
        -type f -name android.jar -print 2>/dev/null | sort -V | tail -n 1)"
fi
[[ -f "$ANDROID_JAR" ]] || { echo 'Missing SDK android.jar' >&2; exit 1; }
mkdir -p build/external/classes build/external/dex
find tests/fixtures/external-app -name '*.java' -print > build/external-sources.txt
# Key ABI test: javac sees ONLY the official Android SDK, not build/framework.
javac --release 8 -encoding UTF-8 -cp "$ANDROID_JAR" \
    -d build/external/classes @build/external-sources.txt
jar --create --file build/external/app.jar -C build/external/classes .
"$D8_CMD" --min-api 26 --lib "$ANDROID_JAR" \
    --output build/external/dex build/external/app.jar
"$AAPT_CMD" package -f \
    -M tests/fixtures/external-app/AndroidManifest.xml \
    -I "$ANDROID_JAR" -F build/external/metadata.apk
python3 scripts/package-demo-apk.py \
    build/external/metadata.apk build/external/dex/classes.dex build/external.apk
echo '[PASS] Independent Android-SDK-compiled APK: build/external.apk'
