#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
ANX_FIXTURE_SOURCE=tests/fixtures/third-party/chiuki \
ANX_FIXTURE_OUTPUT_DIR=build/chiuki-third-party \
ANX_FIXTURE_APK=build/chiuki-third-party.apk \
    bash scripts/build-external-apk.sh
python3 scripts/anx.py inspect build/chiuki-third-party.apk | grep -Fq \
    'Launcher activity: com.sqisland.android.hello.MainActivity'
echo '[PASS] Pinned, unmodified Apache-2.0 third-party Android source built against official SDK.'
