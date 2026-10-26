#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEX="$ROOT/build/dex/classes.dex"
# ART_CMD menunjuk pada host ART dalvikvm64 hasil build art_standalone.
ART_CMD="${ART_CMD:-dalvikvm64}"
if [[ $# -gt 0 && "$1" == "--apk" ]]; then
    shift
    if [[ $# -ne 1 ]]; then
        echo "Usage: $0 --apk <file.apk>" >&2
        exit 2
    fi
    exec python3 "$ROOT/scripts/anx.py" run "$1" \
        --art "$ART_CMD" \
        --framework-dex "$ROOT/build/framework/classes.dex"
fi

if [[ ! -f "$DEX" ]]; then
    echo "Missing $DEX; run scripts/build.sh after installing D8." >&2
    exit 1
fi
if ! command -v "$ART_CMD" >/dev/null 2>&1 && [[ ! -x "$ART_CMD" ]]; then
    echo "ART_CMD='$ART_CMD' was not found. Build/install host ART first." >&2
    exit 1
fi
export ANDROID_DATA="${ANDROID_DATA:-$ROOT/build/android-data}"
mkdir -p "$ANDROID_DATA"
ACTIVITY="${1:-org.demo.HelloActivity}"
exec "$ART_CMD" -cp "$DEX" org.anx.launcher.Main "$ACTIVITY"
