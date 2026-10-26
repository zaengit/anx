#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

SDK_ROOT="${ANDROID_SDK_ROOT:-${ANDROID_HOME:-${HOME:-}/Android/Sdk}}"
if [[ ! -d "$SDK_ROOT" ]]; then
    echo "Android SDK not found at '$SDK_ROOT'. Set ANDROID_SDK_ROOT." >&2
    exit 1
fi

resolve_tool() {
    local override="$1" name="$2" sdk candidate
    if [[ -n "$override" ]]; then
        candidate="$(command -v "$override" 2>/dev/null || true)"
        [[ -n "$candidate" ]] || [[ -x "$override" && -f "$override" ]] && candidate="$override"
        if [[ -n "$candidate" && -x "$candidate" ]]; then
            printf '%s\n' "$candidate"
            return 0
        fi
        echo "$name='$override' is not executable." >&2
        return 1
    fi
    if command -v "$name" >/dev/null 2>&1; then
        command -v "$name"
        return 0
    fi
    local -a candidates=()
    while IFS= read -r candidate; do
        [[ -x "$candidate" ]] && candidates+=("$candidate")
    done < <(find "$SDK_ROOT/build-tools" -mindepth 2 -maxdepth 2 -type f -name "$name" -print 2>/dev/null | sort -V)
    if ((${#candidates[@]})); then
        printf '%s\n' "${candidates[-1]}"
        return 0
    fi
    return 1
}

D8_CMD="$(resolve_tool "${D8:-}" d8 || true)"
AAPT_CMD="$(resolve_tool "${AAPT:-}" aapt || true)"
if [[ -z "$D8_CMD" ]]; then
    echo "D8 was not found. Install Android SDK Build-Tools or set D8=/path/to/d8." >&2
    exit 1
fi
if [[ -z "$AAPT_CMD" ]]; then
    echo "aapt was not found. Install Android SDK Build-Tools or set AAPT=/path/to/aapt." >&2
    exit 1
fi

ANDROID_JAR="${ANDROID_JAR:-}"
if [[ -z "$ANDROID_JAR" ]]; then
    mapfile -t PLATFORMS < <(find "$SDK_ROOT/platforms" -mindepth 2 -maxdepth 2 -type f -name android.jar -print 2>/dev/null | sort -V)
    if ((${#PLATFORMS[@]})); then ANDROID_JAR="${PLATFORMS[-1]}"; fi
fi
if [[ ! -f "$ANDROID_JAR" ]]; then
    echo "android.jar was not found. Install an SDK platform or set ANDROID_JAR=/path/to/android.jar." >&2
    exit 1
fi

FRAMEWORK_CLASSES="$ROOT/build/framework/classes"
DEMO_CLASSES="$ROOT/build/demo-apk/classes"
mkdir -p "$FRAMEWORK_CLASSES" "$DEMO_CLASSES" "$ROOT/build/demo-apk/dex"
find src/main/java -name '*.java' -print > build/framework-sources.txt
find src/demo/java -name '*.java' -print > build/demo-apk-sources.txt
javac --release 8 -encoding UTF-8 -d "$FRAMEWORK_CLASSES" @build/framework-sources.txt
javac --release 8 -encoding UTF-8 -cp "$FRAMEWORK_CLASSES" -d "$DEMO_CLASSES" @build/demo-apk-sources.txt
jar --create --file build/framework/framework.jar -C "$FRAMEWORK_CLASSES" .
jar --create --file build/demo-apk/demo.jar -C "$DEMO_CLASSES" .

"$D8_CMD" --min-api 26 --output build/framework build/framework/framework.jar
"$D8_CMD" --min-api 26 --output build/demo-apk/dex build/demo-apk/demo.jar
"$AAPT_CMD" package -f \
    -M examples/hello-apk/AndroidManifest.xml \
    -I "$ANDROID_JAR" \
    -F build/demo-apk/metadata.apk
python3 scripts/package-demo-apk.py \
    build/demo-apk/metadata.apk \
    build/demo-apk/dex/classes.dex \
    build/demo.apk
echo "[OK] Framework DEX: build/framework/classes.dex"
