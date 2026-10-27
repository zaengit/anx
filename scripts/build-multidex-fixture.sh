#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
if [[ ! -f build/external/metadata.apk ||
      ! -f build/external/classes/org/anx/external/SecondaryDexSentinel.class ]]; then
    bash scripts/build-external-apk.sh
fi
SDK_ROOT="${ANDROID_SDK_ROOT:-${ANDROID_HOME:-${HOME:-}/Android/Sdk}}"
D8_CMD="${D8:-}"
if [[ -z "$D8_CMD" ]]; then
    D8_CMD="$(command -v d8 || true)"
    if [[ -z "$D8_CMD" ]]; then
        D8_CMD="$(find "$SDK_ROOT/build-tools" -mindepth 2 -maxdepth 2 -type f -name d8 -print 2>/dev/null | sort -V | tail -n 1)"
    fi
fi
[[ -n "$D8_CMD" && -x "$D8_CMD" ]] || { echo "Missing D8" >&2; exit 1; }
ANDROID_JAR="${ANDROID_JAR:-}"
if [[ -z "$ANDROID_JAR" ]]; then
    ANDROID_JAR="$(find "$SDK_ROOT/platforms" -mindepth 2 -maxdepth 2 -type f -name android.jar -print 2>/dev/null | sort -V | tail -n 1)"
fi
[[ -f "$ANDROID_JAR" ]] || { echo "Missing Android SDK android.jar" >&2; exit 1; }
OUT="$ROOT/build/multidex-fixture"
mkdir -p "$OUT/primary-classes" "$OUT/primary-dex" "$OUT/secondary-dex"
cp -a build/external/classes/. "$OUT/primary-classes/"
jar --create --file "$OUT/secondary.jar" \
    -C build/external/classes org/anx/external/SecondaryDexSentinel.class
rm "$OUT/primary-classes/org/anx/external/SecondaryDexSentinel.class"
jar --create --file "$OUT/primary.jar" -C "$OUT/primary-classes" .
"$D8_CMD" --min-api 26 --lib "$ANDROID_JAR" \
    --output "$OUT/primary-dex" "$OUT/primary.jar"
"$D8_CMD" --min-api 26 --lib "$ANDROID_JAR" \
    --output "$OUT/secondary-dex" "$OUT/secondary.jar"
python3 - "$OUT/primary-dex/classes.dex" "$OUT/secondary-dex/classes.dex" <<'PY'
from pathlib import Path
import sys
import zipfile
primary = Path(sys.argv[1])
secondary = Path(sys.argv[2])
target = Path("build/multidex-fixture.apk")
with zipfile.ZipFile("build/external/metadata.apk") as source, zipfile.ZipFile(
        target, "w", compression=zipfile.ZIP_DEFLATED) as output:
    for entry in source.infolist():
        if entry.filename not in ("classes.dex", "classes2.dex"):
            output.writestr(entry, source.read(entry))
    output.write(primary, "classes.dex")
    output.write(secondary, "classes2.dex")
print("[PASS] SDK APK with separately compiled primary/secondary DEX:", target)
PY
