#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
mkdir -p build/test-classes
find src/main/java src/test/java -name '*.java' -print > build/test-sources.txt
javac --release 8 -encoding UTF-8 -d build/test-classes @build/test-sources.txt
ANX_APP_DATA_HOME="$ROOT/build/storage-test" java -cp build/test-classes org.anx.tests.StorageTest
java -cp build/test-classes org.anx.tests.FrameworkLifecycleTest
if java -cp build/test-classes org.anx.launcher.Main \
    org.anx.tests.ThrowingActivity org.anx.tests \
    org.anx.tests.ThrowingApplication > build/lifecycle-failure.out 2>&1; then
    echo '[FAIL] Deliberate lifecycle exception did not fail process' >&2
    exit 1
fi
grep -Fq '[test] stop despite pause failure' build/lifecycle-failure.out
grep -Fq '[test] destroy despite pause failure' build/lifecycle-failure.out
grep -Fq '[test] app terminated despite pause failure' build/lifecycle-failure.out
echo '[PASS] Lifecycle cleanup persists after onPause exception.'
