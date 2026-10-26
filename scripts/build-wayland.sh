#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
if ! pkg-config --exists gtk4; then
    echo 'GTK4 development headers required (Fedora: gtk4-devel; Debian/Ubuntu: libgtk-4-dev)' >&2
    exit 1
fi
mkdir -p build/native
"${CC:-cc}" -std=c11 -O2 -Wall -Wextra -Werror \
    $(pkg-config --cflags gtk4) \
    src/backends/wayland/anx-wayland.c \
    -o build/native/anx-wayland $(pkg-config --libs gtk4)
echo '[PASS] Wayland GTK4 host binary: build/native/anx-wayland'
