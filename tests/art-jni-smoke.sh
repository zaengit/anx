#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
ART_CMD="${ART_CMD:-dalvikvm64}"
LOG_DIR="${ART_SMOKE_LOG_DIR:-$ROOT/build/art-smoke}"
mkdir -p "$LOG_DIR/native-test"
JNI_H="$(find /usr/lib/jvm -name jni.h -type f -print -quit)"
if [[ -z "$JNI_H" ]]; then
    echo '[FAIL] JDK JNI headers not installed' >&2
    exit 1
fi
JNI_INCLUDE="$(dirname "$JNI_H")"
cc -shared -fPIC -O2 -Wall -Wextra -Werror \
    -I"$JNI_INCLUDE" -I"$JNI_INCLUDE/linux" \
    tests/fixtures/native-app/libanxfixture.c \
    -o "$LOG_DIR/native-test/libanxfixture.so"
python3 - "$LOG_DIR/native-test/libanxfixture.so" "$LOG_DIR/native-fixture.apk" <<'PY'
import sys
import zipfile
from pathlib import Path
library = Path(sys.argv[1])
result = Path(sys.argv[2])
with zipfile.ZipFile("build/native-fixture.apk") as source, zipfile.ZipFile(result, "w") as output:
    for entry in source.infolist():
        output.writestr(entry, source.read(entry))
    output.write(library, "lib/x86_64/libanxfixture.so")
print("[anx-jni] x86_64 native library packaged:", result)
PY
python3 scripts/anx.py inspect "$LOG_DIR/native-fixture.apk" > "$LOG_DIR/native-inspect.log"
grep -Fq "Native ABIs: x86_64 (1)" "$LOG_DIR/native-inspect.log"
if ! python3 scripts/anx.py run "$LOG_DIR/native-fixture.apk" \
    --unsafe-host-execution --backend console --art "$ART_CMD" \
    --framework-dex build/framework/classes.dex \
    --android-data /tmp/anx-art-native-data \
    >"$LOG_DIR/native-run.log" 2>&1; then
    cat "$LOG_DIR/native-run.log" >&2
    exit 1
fi
for expected in \
    "[anx] native ABI: x86_64 (1 libraries)" \
    "[anx-jni] nativeSum(7,9)=16" \
    "[linux-console-backend] TextView: Host JNI test: 16" \
    "[anx] onDestroy"; do
    grep -Fq "$expected" "$LOG_DIR/native-run.log" || {
        cat "$LOG_DIR/native-run.log" >&2
        echo "[FAIL] Missing JNI integration evidence: $expected" >&2
        exit 1
    }
done
echo '[PASS] Independently SDK-compiled APK called host-native x86_64 JNI on ART.'
