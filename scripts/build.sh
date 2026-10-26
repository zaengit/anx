#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
mkdir -p build/classes build/dex
find src/main/java src/demo/java -name '*.java' -print > build/sources.txt
javac --release 8 -encoding UTF-8 -d build/classes @build/sources.txt
jar --create --file build/anx-all.jar -C build/classes .
echo "[OK] JVM smoke build: build/classes/"

resolve_d8() {
    local candidate sdk
    local -a sdk_roots=()
    local -a candidates=()

    if [[ -n "${D8:-}" ]]; then
        command -v "$D8" 2>/dev/null || [[ -x "$D8" ]] && { printf '%s\n' "$D8"; return 0; }
        echo "D8='$D8' was not found or is not executable." >&2
        return 1
    fi

    if command -v d8 >/dev/null 2>&1; then
        command -v d8
        return 0
    fi

    [[ -n "${ANDROID_SDK_ROOT:-}" ]] && sdk_roots+=("$ANDROID_SDK_ROOT")
    [[ -n "${ANDROID_HOME:-}" ]] && sdk_roots+=("$ANDROID_HOME")
    [[ -n "${HOME:-}" ]] && sdk_roots+=("$HOME/Android/Sdk")

    for sdk in "${sdk_roots[@]}"; do
        [[ -d "$sdk/build-tools" ]] || continue
        while IFS= read -r candidate; do
            [[ -x "$candidate" ]] && candidates+=("$candidate")
        done < <(find "$sdk/build-tools" -mindepth 2 -maxdepth 2 -type f -name d8 -print | sort -V)
    done
    if ((${#candidates[@]})); then
        printf '%s\n' "${candidates[-1]}"
        return 0
    fi

    for sdk in "${sdk_roots[@]}"; do
        candidate="$sdk/cmdline-tools/latest/bin/d8"
        if [[ -x "$candidate" ]]; then
            printf '%s\n' "$candidate"
            return 0
        fi
    done

    return 1
}

D8_CMD="$(resolve_d8 || true)"
if [[ -n "$D8_CMD" ]]; then
    echo "[build] D8: $D8_CMD"
    "$D8_CMD" --min-api 26 --output build/dex build/anx-all.jar
elif [[ -n "${R8_JAR:-}" && -f "$R8_JAR" ]]; then
    java -cp "$R8_JAR" com.android.tools.r8.D8 --min-api 26 --output build/dex build/anx-all.jar
else
    echo "[INFO] DEX not generated: install Android SDK Build-Tools or set D8=/path/to/d8 or R8_JAR=/path/to/r8.jar." >&2
    exit 0
fi
[[ -s build/dex/classes.dex ]] || { echo "classes.dex missing" >&2; exit 1; }
echo "[OK] ART bytecode: build/dex/classes.dex"
