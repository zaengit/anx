# ANX — experimental Android compatibility layer for Linux

A proof of concept for Java-based Android application compatibility in a Linux process **without** Waydroid, a VM, a container, or LineageOS. The design uses AOSP host ART (or an AOSP-based `art_standalone` fork). It **cannot yet** run Android APKs in general, and an experimental native GTK4/GDK Wayland backend is available for the narrow TextView + Button demo (console fallback remains available).

See [STATUS.md](STATUS.md) for tested milestone status and remaining release blockers.

## What is implemented

- A small framework implementing `Application`, `Activity`, `Instrumentation`, `Intent`, typed `Bundle`, `Looper`, `MessageQueue`, `Handler`, `View`, `TextView`, and click-capable `Button`. The console backend does not yet support real graphical interaction.
- Lifecycle dispatch on the prepared main thread: `Application.onCreate`, then `Activity.onCreate` → `onStart` → `onResume` → `onPause` → `onStop` → `onDestroy` with host-only `Application.onTerminate` during teardown.
- An abstract `WindowBackend`, recursive console view output, and an experimental GTK4/GDK Wayland process with a text/click IPC bridge.
- A script to compile Java to DEX with **D8**; a script to run DEX through **ART `dalvikvm64`**.
- A standalone `HelloDex` entry point and an ART smoke script that checks both DEX execution and the ANX lifecycle launcher.
- An APK ZIP/size validator, Android binary manifest parser, launcher-Activity resolver, DEX/ABI inspector, and `anx inspect` / `anx run` commands.
- A separately packaged hello APK with its own DEX; the host framework and APK classes are passed to ART as separate classpath entries.

## Prerequisites

- Linux x86_64 (initial development); JDK 17+; Bash shell; Python 3.10+.
- To compile DEX: Android SDK Build-Tools containing `d8`, or an R8 JAR that provides `com.android.tools.r8.D8`.
- To execute with ART: host ART `dalvikvm64`, along with compatible libraries, bootclasspath, and build data files. One relatively practical example is https://gitlab.com/android_translation_layer/art_standalone (an AOSP-derived modified ART). This build has many dependencies; see its repository README. The ART version and PoC framework must be compatible at the bytecode/API level.

## Quick tests (JDK smoke tests, not ART)

```sh
bash tests/smoke.sh
bash tests/framework-smoke.sh
```

The JDK validates the Java compatibility logic. Separate host-ART evidence is provided by the [ART integration workflow](.github/workflows/art-integration.yml), which runs the standalone APK and a mock click/repaint subprocess through the patched reference ART.

## Convert to DEX

```sh
bash scripts/build.sh
# D8 is discovered from PATH, ANDROID_SDK_ROOT, ANDROID_HOME, or ~/Android/Sdk.
# To select a specific D8 binary:
D8="$ANDROID_SDK_ROOT/build-tools/37.0.0/d8" bash scripts/build.sh
# Or use an R8 JAR that provides D8:
R8_JAR=/opt/android/r8.jar bash scripts/build.sh
```

## Run with AOSP-based ART

Set up and run host ART according to the instructions for the AOSP project/build you chose. For `art_standalone`, the upstream README documents `dalvikvm64 -cp file.dex class.Name`.

```sh
ART_CMD=/path/to/dalvikvm64 bash scripts/run-art.sh
# Conceptually equivalent to:
# ANDROID_DATA=/tmp/art-data dalvikvm64 -cp build/dex/classes.dex org.anx.launcher.Main org.demo.HelloActivity
```

The ART smoke test verifies both a standalone DEX class and the framework demo:

```sh
ART_CMD=/path/to/dalvikvm64 bash tests/art-smoke.sh
```

On an x86_64 Linux host with Podman, the optional Alpine reference runtime can
be built with the libcore shutdown fix and exercised without installing ART on
the host:

```sh
bash scripts/run-art-alpine.sh
```

See [docs/build-art-host.md](docs/build-art-host.md) for the pinned runtime
revision, build prerequisites, and limitations of the container reference.

Having `dalvikvm64` available is not sufficient: host ART requires the correct libraries, libcore, bootclasspath, and runtime paths. If ART cannot start yet, fix the host runtime installation before debugging the framework.

## Experiment with a user APK

```sh
./anx inspect /path/to/application.apk
./anx run /path/to/application.apk --art /path/to/dalvikvm64
```

Build the standalone demo APK and inspect/run it through the reference ART setup:

```sh
bash scripts/build-demo-apk.sh
./anx inspect build/demo.apk
./anx run build/demo.apk --art /path/to/dalvikvm64
```

The loader passes the manifest package/Application name and APK path to the Java
host, so application callbacks and read-only `assets/` lookup can work in the
supported subset. It drains ready main-thread callbacks once before displaying the console view.
The experimental GUI backend waits for native click/close events, but it does
not yet offer Android-compatible continuous Looper timing or background tasks.
The current loader handles one DEX file and APKs without native libraries. It
does not yet load Android resources, multidex, JNI, Binder services, or Google
Play Services. ART must be installed with its runtime libraries, bootclasspath,
and data files.

## Experimental native Wayland GUI

```sh
# Fedora: sudo dnf install gtk4-devel pkgconf-pkg-config gcc
# Ubuntu: sudo apt install libgtk-4-dev pkg-config build-essential
bash scripts/build-wayland.sh
bash scripts/build-demo-apk.sh
./anx build/demo.apk --art /path/to/dalvikvm64 --backend wayland
bash tests/gui-protocol-smoke.sh
```

`--backend auto` chooses Wayland when `WAYLAND_DISPLAY` and the built
executable are present; otherwise it falls back to console. This experimental
GTK4 Wayland bridge is **not** a full Android GUI implementation.

See [docs/wayland-backend.md](docs/wayland-backend.md) for limitations and tests.

## Next milestones and safety

M3's lifecycle subset is validated on pinned ART. M4's native GTK4 Wayland
client and the host bridge pass compositor-headless and ART/mock-protocol
tests respectively. The fully integrated **ART + GTK4 visual click** remains
unverified, so **M5/v0.1 MVP is not complete**.

Track the remaining development in [STATUS.md](STATUS.md) and [M4–M8 issues](https://github.com/zaengit/anx/issues).
There is **no sandbox**: only run APKs you trust. APK metadata validation
does not isolate executable code from the Linux host.

## Architecture decisions

We use **ART as the DEX runtime**, rather than reimplementing the VM. The framework is not the entire AOSP framework: `android.*` classes are implemented only as needed and translated to host APIs. This requires ABI/API consistency and substantial development before nontrivial applications become compatible.

## Upstream references

- https://source.android.com/docs/core/ota/modular-system/art
- https://android.googlesource.com/platform/art/
- https://gitlab.com/android_translation_layer/art_standalone
- https://gitlab.com/android_translation_layer/android_translation_layer
