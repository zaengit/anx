# Experimental Linux-host JNI pilot (M7)

**Scope:** The ANX loader accepts **host-compatible x86_64 ELF64** libraries from
an APK's `lib/x86_64/lib*.so` entries. ZIP entries are inspected before any
execution; selected library names and ELF headers are checked, files streamed
through CRC verification to a private temporary directory, and the directory
is removed after ART exits. Counts and total uncompressed sizes are bounded.

The launcher passes the native directory as `-Djava.library.path` to ART.
A purpose-built APK, compiled against the official Android SDK, calls
`System.loadLibrary("anxfixture")` and invokes an x86_64 JNI function.
Its shared object is compiled **on the Alpine/musl host** in the pinned ART
container, not built against Android's Bionic libc.

## Verify

```sh
python3 tests/native-libraries-unit.py
bash scripts/build-jni-fixture.sh
bash scripts/run-art-alpine.sh
```

This feature does **not** provide an Android NDK linker, Bionic symbol
compatibility, ARM emulation, Bionic/native dependency closure, relocation
namespaces, general JNI lifecycle, EGL or graphics acceleration.
A regular Android NDK .so can still fail to load on Linux.
A malicious `.so` is unrestricted host-native code: use
`--unsafe-host-execution` for **trusted fixtures only**.
