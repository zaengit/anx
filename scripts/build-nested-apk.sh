#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
ANX_FIXTURE_SOURCE=tests/fixtures/nested-app \
ANX_FIXTURE_OUTPUT_DIR=build/nested-fixture \
ANX_FIXTURE_APK=build/nested-fixture.apk \
    bash scripts/build-external-apk.sh
python3 scripts/anx.py inspect build/nested-fixture.apk | grep -Fq 'Launcher activity: org.anx.nested.NestedActivity'
echo '[PASS] Independently official-SDK-compiled nested XML APK fixture.'
