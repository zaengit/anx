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
./anx run build/demo.apk --art /path/to/dalvikvm64
```

`build/demo.apk` contains a binary `AndroidManifest.xml` and a DEX compiled
from `src/demo/java`, separate from `build/framework/classes.dex`. ART receives
the framework DEX and APK on its classpath, and the launcher class is selected
from the manifest.

The loader currently requires exactly one launcher Activity, one top-level
DEX (`classes.dex`), and no native `.so` files. It instantiates the manifest `Application` class when provided, passes the APK
path to a read-only `AssetManager` for `assets/` streams, and supports main-thread
lifecycle and immediate Handler callbacks. It does not parse `resources.arsc`,
load multidex or JNI, or create a graphical window.
Malformed archives and unsupported inputs fail with a targeted error.
