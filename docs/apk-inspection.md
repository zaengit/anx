# APK inspection and loading subset

ANX's Python inspector reads APK ZIP metadata without extracting entries.
It validates archive size, entry count, declared uncompressed sizes, compression
ratios, duplicate names, the binary manifest CRC, and DEX CRCs. It applies
limits of 2 GiB per archive, 512 MiB per entry, 1 GiB total uncompressed data,
20,000 ZIP entries, and a 2,000:1 compression ratio.

The binary XML reader reports the package, optional Application class,
activities, aliases, and a unique `MAIN`/`LAUNCHER` target. `anx inspect`
also lists DEX files and native ABIs. It does not extract APK contents.

## Build and run the reference demo

```sh
bash scripts/build-demo-apk.sh
./anx inspect build/demo.apk
./anx run build/demo.apk --art /path/to/dalvikvm64 --unsafe-host-execution
```

`build/demo.apk` contains a binary `AndroidManifest.xml` and a DEX compiled
from `src/demo/java`, separate from `build/framework/classes.dex`. ART receives
the framework DEX and APK on its classpath, and the launcher class is selected
from the manifest.

The loader requires exactly one launcher Activity and a contiguous series of
DEX entries (`classes.dex`, `classes2.dex`, etc.). On the experimental ART
execution path, ANX extracts at most **15 secondary DEX files** into a private
temporary directory, rejects malformed headers, ZIP symlinks and excessive
decompressed sizes (64 MiB each, 128 MiB combined), and adds them to ART's
classpath. The directory is deleted after ART exits. APK metadata inspection
does not extract entries. The independent SDK test fixture places a method
used by `ExternalActivity` **only** in `classes2.dex`; ART calls it in CI.
`classes.dex` is left inside the APK. The experimental Bubblewrap console
profile binds secondary DEX files read-only.

A single matching x86_64 **Linux-host-built** JNI library subset, compiled
string/color/dimension/bool/integer resources and the GTK4 Wayland MVP also
exist. These do not imply Bionic compatibility, Android system services,
full `resources.arsc` configuration handling or general third-party APK support.
Malformed archives and unsupported inputs fail with a targeted error.

The binary XML string-pool reader rejects truncated lengths, missing UTF-8
and UTF-16 terminators, and string data overlapping its offset array.
The manifest parser also rejects unclosed element stacks. These malformed
inputs raise controlled `ManifestError`/`ApkError` exceptions; the
standalone `tests/manifest-safety.py` regression runs in CI. This validation
improves inspection robustness but is not an APK sandbox.
