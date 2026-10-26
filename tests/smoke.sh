#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
bash scripts/build.sh
java -cp build/classes org.anx.launcher.Main org.demo.HelloActivity > build/smoke.out
grep -Fq '[anx] onCreate' build/smoke.out
grep -Fq '[anx] onStart' build/smoke.out
grep -Fq '[anx] onResume' build/smoke.out
grep -Fq '[linux-console-backend] TextView: Halo dari API Android minimal!' build/smoke.out
grep -Fq '[anx] onDestroy' build/smoke.out
cat build/smoke.out
echo '[PASS] Smoke test JVM. ART belum divalidasi oleh tes ini.'
