#!/usr/bin/env bash
# Build CI-only pointer injector; never install on a user's desktop.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
command -v wayland-scanner >/dev/null || { echo 'Missing wayland-scanner' >&2; exit 1; }
pkg-config --exists wayland-client
GENERATED_DIR="${ANX_VIRTUAL_POINTER_GENERATED_DIR:-build/virtual-pointer}"
OUTPUT_DIR="${ANX_VIRTUAL_POINTER_OUTPUT_DIR:-build/native}"
mkdir -p "$GENERATED_DIR" "$OUTPUT_DIR"
XML=third_party/protocols/wlr-virtual-pointer-unstable-v1.xml
wayland-scanner client-header "$XML" \
    $GENERATED_DIR/wlr-virtual-pointer-unstable-v1-client-protocol.h
wayland-scanner private-code "$XML" \
    $GENERATED_DIR/wlr-virtual-pointer-unstable-v1-client-protocol.c
"${CC:-cc}" -std=c11 -O2 -Wall -Wextra -Werror \
    -I "$GENERATED_DIR" $(pkg-config --cflags wayland-client) \
    tests/helpers/anx-virtual-pointer.c \
    $GENERATED_DIR/wlr-virtual-pointer-unstable-v1-client-protocol.c \
    -o "$OUTPUT_DIR/anx-virtual-pointer" $(pkg-config --libs wayland-client)
echo '[PASS] Persistent wlroots virtual pointer CI helper compiled.'
