# Building and running host ART

ANX executes DEX bytecode with ART. A JDK smoke test does not validate this
path. The commands below build the demo DEX and run both a standalone DEX entry
point and the ANX lifecycle launcher through `dalvikvm64`.

## Reference runtime

The initial reference is the Linux host runtime from
[`android_translation_layer/art_standalone`](https://gitlab.com/android_translation_layer/art_standalone),
pinned at commit `a1edfc40e8cea3644d80e4e776d3fa7fc397a1c2` (2026-10-18).
This is an AOSP-derived ART/libcore fork, not an unmodified current AOSP ART
checkout. Its README describes ART and most of the tree as based on the
`android-6.0.1_r46` dalvik branch, with ART and libcore updated separately.
Review [`../third_party/README.md`](../third_party/README.md) before changing
the pin or distributing runtime binaries.

The project DEX target is API 26 (`d8 --min-api 26`). The reference host is
Linux x86_64. ART must be built for the host architecture and installed with
its runtime libraries and data; a `dalvikvm64` executable copied by itself is
not a complete runtime.

## Build ANX DEX

Install JDK 17 or newer and Android SDK Build-Tools. `scripts/build.sh` searches
`PATH`, `ANDROID_SDK_ROOT`, `ANDROID_HOME`, and `~/Android/Sdk` for D8.

```sh
bash scripts/build.sh
```

To select an exact D8 binary:

```sh
D8="$ANDROID_SDK_ROOT/build-tools/37.0.0/d8" bash scripts/build.sh
```

If D8 is not installed, an R8 JAR can provide the D8 entry point:

```sh
R8_JAR=/path/to/r8.jar bash scripts/build.sh
```

The build writes `build/dex/classes.dex` and records its SHA-256 when the ART
smoke script runs.

## Build art_standalone from source

Clone and checkout the pinned revision:

```sh
git clone https://gitlab.com/android_translation_layer/art_standalone.git
cd art_standalone
git checkout a1edfc40e8cea3644d80e4e776d3fa7fc397a1c2
```

The upstream README lists the build dependencies for Debian-family systems:
JDK, Python 3, Meson, EGL development files, pkg-config, libbsd, libunwind,
libelf, Valgrind, ICU, OpenSSL, expat, zip, lz4, xz/lzma, and libcap development
files. It also requires a WolfSSL build with JNI enabled and a separately
installed `bionic_translation` dependency. Build and install with the upstream
Makefile, then verify `dalvikvm64 --help` and run a DEX before using it with
ANX. Dependency package names and versions vary by distribution; record
them with the runtime build.

## Run the ART smoke test

```sh
ART_CMD=/path/to/dalvikvm64 bash tests/art-smoke.sh
```

The script prints the resolved ART executable, host architecture, DEX hash,
and ART version (queried separately because this runtime exits after
`-showversion`), then runs `org.demo.HelloDex` and the ANX launcher. It
stores full runtime output under `build/art-smoke/`. If `ART_CMD` is omitted,
the script looks for `dalvikvm64` on `PATH`.

The smoke test fails with a targeted message when D8/DEX or ART is missing. A
successful run proves that this DEX and this framework subset work with the
selected ART build; it does not establish compatibility with Android APKs in
general.

## Current reference result

On 2026-10-26, D8 37.0.0 generated the DEX on Fedora 45 x86_64. The unmodified
Alpine `art_standalone` package `0_git20261018-r0` reported
`ART version 2.1.0 x86_64`, ran the demo, then aborted with exit status 134
during runtime shutdown. Its libcore `JNI_OnUnload` path called
`JavaVM::GetEnv()` after ART had unregistered the thread.

`third_party/patches/art_standalone-jni-onunload.patch` backports the AOSP
cleanup change by avoiding JNI calls from that callback and unregistering ICU
without an environment. `scripts/run-art-alpine.sh` builds the pinned source
with this patch, replaces `libjavacore.so` in the disposable runtime image,
then runs the ART, manifest-inspection, and separately packaged demo APK
smokes. The patched run passes; its full logs are under `build/art-smoke/`.

## Local reference-container run

On an x86_64 Linux machine with Podman, the optional wrapper builds a pinned,
patched Alpine `art_standalone` image without installing ART on the host:

```sh
bash scripts/run-art-alpine.sh
```

It builds DEX on the host, then builds and runs ART in an Alpine Linux
container. The container recipe pins the base image digest, ART source commit,
source archive hash, and package version. Alpine edge build dependencies remain
external inputs. This is a runtime smoke reference, not ANX's deployment
architecture, and does not validate a Fedora/glibc ART installation.
