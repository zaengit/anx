#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
ANX_FIXTURE_SOURCE=tests/fixtures/native-app \
ANX_FIXTURE_OUTPUT_DIR=build/native-fixture \
ANX_FIXTURE_APK=build/native-fixture.apk bash scripts/build-external-apk.sh
