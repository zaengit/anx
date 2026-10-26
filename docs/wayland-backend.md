# Experimental native Wayland window (M4/M5)

ANX implements a GTK4 window through the Linux-native GDK Wayland backend.
The GUI runs as a separate ordinary Linux process and communicates with the
ART Activity over stdin/stdout. The native process emits `READY`, `CLICK`
and `CLOSE`. Java dispatches `Button.performClick()` on the main thread and
sends back `TEXT<TAB>base64-UTF8` to repaint the `TextView`.

This avoids JNI or a Bionic linker. GDK manages xdg-shell/protocol internals.

## Build and run

Fedora: `sudo dnf install gtk4-devel pkgconf-pkg-config gcc`

Debian/Ubuntu: `sudo apt install libgtk-4-dev pkg-config build-essential`

```sh
bash scripts/build-wayland.sh
bash scripts/build-demo-apk.sh
./anx build/demo.apk --art /path/to/dalvikvm64 --backend wayland
```

With a running Wayland session, `./anx build/demo.apk --art ...`
defaults to `--backend auto`: selects Wayland when executable exists,
otherwise console. Override binary with `--wayland-binary /path/to/anx-wayland`.

## Supported UI

One `TextView`, optionally one `Button`, in a vertical `LinearLayout`.
A standalone `TextView` is also valid. GTK4 handles window-close, focus,
software rendering and button activation; button events update Java text.

There is **no** full Android measurement/layout engine, resource-table lookup,
touch event translation, scrolling, accessibility, services, navigation or
general APK compatibility. This is GTK4's Wayland backend, not a direct
xdg-shell client implemented from scratch by ANX.

## Verification gates

- `tests/gui-protocol-smoke.sh`: JDK process-to-process click/repaint mock.
- `scripts/build-wayland.sh`: GTK4 native compilation.
- `tests/wayland-headless.sh`: native window under a headless Weston compositor.
- `scripts/run-art-alpine.sh`: separate APK on ART **in console mode**.

**MVP not yet proven until an actual desktop runs the APK through host ART
with Wayland, the user clicks, and the label repaints visibly.**
Unknown APKs are not safe: there is no application sandbox.
