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
./anx build/demo.apk --art /path/to/dalvikvm64 --unsafe-host-execution --backend wayland
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
- `scripts/run-art-alpine.sh`: the same standalone APK runs through ART with
  a **real GTK4 window on headless Weston** and a deterministic test-only GTK
  button-signal trigger; plus ART console and mock-subprocess regression tests.

The ART integration test runs the actual GTK4 native client and standalone APK
together on Alpine/musl ART against a Weston headless compositor. An explicit
`ANX_GUI_TEST_AUTOCLICK=1` fixture fires GTK's `clicked` signal after the
window is realized. The native client verifies that its live label was updated,
then closes. This proves real ART + Wayland integration **without pretending
to emulate a human pointer input event**.

A manual desktop pointer click, focus, resize and long-running application
tests are still required for the full interactive MVP acceptance gate.
Unknown APKs are not safe: there is no application sandbox.

## Main Looper during active GUI

The native GTK4 host sends a bounded `PULSE` event every 50 milliseconds.
The Java main thread handles the pulse by draining ready messages from its
`Looper`, including delayed `Handler` callbacks. When the `TextView` label
changes, the host writes a `TEXT` command to repaint GTK4. The `TimerActivity`
fixture verifies an idle window repaints after `postDelayed` without any click,
both on a JVM mock peer and on real host ART + Weston.

This is a **coarse timer polling bridge**, not Android vsync, Choreographer,
precision timers, a full event scheduler, or a guarantee for background tasks.

## Headless Sway compositor pointer input regression (M5)

`tests/wayland-sway-pointer.sh` runs an isolated headless Sway compositor
with a JVM Activity and the **real GTK4 Wayland client**. It reads the bounds
of a realized GTK Button and its compositor window, then uses Sway IPC to
move the seat cursor and press/release button1. It verifies the Java click
callback and GTK label repaint. Unlike `ANX_GUI_TEST_AUTOCLICK=1`, it
does not emit GTK's `clicked` signal directly. GTK geometry diagnostics
are enabled only with `ANX_GUI_TEST_REPORT_BUTTON_GEOMETRY=1`.

This is **compositor-generated pointer input**, not a physical mouse test.
It does not prove a native desktop session's resize/focus behavior, touch,
other widget interactions or long-running app stability. The pinned-ART/Weston
regression remains separate and continues to use a GTK test signal.
