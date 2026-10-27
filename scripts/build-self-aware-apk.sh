#!/usr/bin/env bash
# Official-SDK standalone build of pinned upstream source. Original files never modified.
# The build-only manifest projection supplies Gradle's namespace and removes
# icon / backup attributes referring to images/XML not required by this test.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
SOURCE=tests/fixtures/third-party/appliberated
PREPARED=build/self-aware-source
mkdir -p "$PREPARED"
cp -a "$SOURCE/java" "$PREPARED/"
cp -a "$SOURCE/res" "$PREPARED/"
python3 - "$SOURCE/AndroidManifest.xml" "$PREPARED/AndroidManifest.xml" <<'PY'
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

source, target = (Path(value) for value in sys.argv[1:])
android_ns = "http://schemas.android.com/apk/res/android"
root = ET.parse(source).getroot()
if root.attrib.get("package") not in (None, "com.appliberated.helloworldselfaware"):
    raise SystemExit("Unexpected upstream package in AndroidManifest.xml")
root.set("package", "com.appliberated.helloworldselfaware")
application = root.find("application")
if application is None:
    raise SystemExit("Missing upstream application")
for key in ("icon", "roundIcon", "dataExtractionRules", "fullBackupContent"):
    application.attrib.pop("{" + android_ns + "}" + key, None)
# Preserve Activity, intent filters, label and theme; only packaging metadata
# that Gradle or absent binary image resources otherwise supplies is adjusted.
ET.ElementTree(root).write(target, encoding="utf-8", xml_declaration=True)
print("[anx] generated standalone manifest projection from unchanged upstream manifest")
PY
ANX_FIXTURE_SOURCE="$PREPARED" \
ANX_FIXTURE_OUTPUT_DIR=build/self-aware-dex \
ANX_FIXTURE_APK=build/self-aware-third-party.apk \
    bash scripts/build-external-apk.sh
python3 scripts/anx.py inspect build/self-aware-third-party.apk \
    | grep -Fq 'Launcher activity: com.appliberated.helloworldselfaware.MainActivity'
echo '[PASS] Second independent MIT-licensed APK source compiled against official Android SDK.'
