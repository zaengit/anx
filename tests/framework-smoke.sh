#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
mkdir -p build/test-classes
find src/main/java src/test/java -name '*.java' -print > build/test-sources.txt
javac --release 8 -encoding UTF-8 -d build/test-classes @build/test-sources.txt
java -cp build/test-classes org.anx.tests.FrameworkLifecycleTest
