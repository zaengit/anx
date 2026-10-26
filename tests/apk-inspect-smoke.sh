#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

bash scripts/build-demo-apk.sh
python3 scripts/anx.py inspect build/demo.apk > build/apk-inspect.out
grep -Fq 'Package: org.demo' build/apk-inspect.out
grep -Fq 'Launcher activity: org.demo.HelloActivity' build/apk-inspect.out
grep -Fq 'DEX: classes.dex' build/apk-inspect.out
if grep -Fq 'Native ABIs: none' build/apk-inspect.out; then
    cat build/apk-inspect.out
    echo '[PASS] APK metadata and launcher were read from binary AndroidManifest.xml.'
else
    cat build/apk-inspect.out >&2
    echo '[FAIL] Demo APK unexpectedly contains native ABI entries.' >&2
    exit 1
fi

# Refuse unsafe host execution by default, before launching a runtime.
cat > build/fake-art <<'FAKE_ART'
#!/bin/sh
touch build/unsafe-art-was-invoked
exit 0
FAKE_ART
chmod +x build/fake-art
rm -f build/unsafe-art-was-invoked
if python3 scripts/anx.py run build/demo.apk --art build/fake-art > build/unsafe-denied.out 2>&1; then
    echo '[FAIL] Unsafe host execution without consent was accepted' >&2
    exit 1
fi
grep -Fq -- '--unsafe-host-execution' build/unsafe-denied.out
if [[ -e build/unsafe-art-was-invoked ]]; then
    echo '[FAIL] ART was executed despite missing consent' >&2
    exit 1
fi
python3 scripts/anx.py run build/demo.apk --art build/fake-art \
    --unsafe-host-execution > build/unsafe-optin.out
test -f build/unsafe-art-was-invoked || {
    echo '[FAIL] Explicit opt-in did not reach the expected runtime' >&2
    exit 1
}
echo '[PASS] Untrusted APK launch is denied by default and explicit opt-in is tested.'

printf 'not a ZIP archive' > build/not-an-apk.apk
if python3 scripts/anx.py inspect build/not-an-apk.apk >/dev/null 2>&1; then
    echo '[FAIL] Corrupted APK was accepted.' >&2
    exit 1
fi

python3 - <<'PY'
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path("scripts").resolve()))
import apk_inspector

oversized = Path("build/oversized.apk")
with zipfile.ZipFile(oversized, "w", compression=zipfile.ZIP_DEFLATED) as archive:
    archive.writestr("AndroidManifest.xml", b"x" * 8)
apk_inspector.MAX_ENTRY_SIZE = 4
try:
    apk_inspector.inspect_apk(oversized)
except apk_inspector.ApkError as error:
    assert "limit" in str(error)
else:
    raise SystemExit("oversized APK entry was accepted")

multidex = Path("build/multidex.apk")
missing_dex = Path("build/missing-dex.apk")
with zipfile.ZipFile("build/demo.apk") as source:
    entries = [(entry.filename, source.read(entry)) for entry in source.infolist()]
for path, extra in ((multidex, ("classes2.dex", b"secondary dex")),
                    (missing_dex, ("classes3.dex", b"gap in multidex"))):
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in entries:
            archive.writestr(name, data)
        archive.writestr(*extra)

apk_inspector.MAX_ENTRY_SIZE = 512 * 1024 * 1024
assert apk_inspector.inspect_apk(multidex).dex_files == ("classes.dex", "classes2.dex")
try:
    apk_inspector.inspect_apk(missing_dex)
except apk_inspector.ApkError as error:
    assert "missing DEX" in str(error)
else:
    raise SystemExit("multidex gap was accepted")
PY
echo '[PASS] Corrupt and oversized APK inputs were rejected.'
echo '[PASS] Multidex files are listed in order; gaps are rejected.'
