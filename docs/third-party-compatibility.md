# First independent third-party Android APK (M6)

**Source:** https://github.com/chiuki/android-hello-world
**Pinned upstream commit:** `1347d20b9e2ba0ec76b531a20eb862b9c0bb75ce`
**License:** Apache-2.0, preserved unchanged at `tests/fixtures/third-party/chiuki/LICENSE`.

The original Activity, manifest, XML layout and string resources are copied
**unchanged** from this independent upstream Android application. They
are compiled against the official Android `android.jar` using aapt, javac
and D8, rather than ANX stubs. This is built from source; not a prebuilt
upstream APK or a claim of Android Store interoperability.

## Reproduce

```sh
bash scripts/build-chiuki-apk.sh
python3 scripts/anx.py inspect build/chiuki-third-party.apk
bash scripts/run-art-alpine.sh
```

| Feature | Verified / limitation |
| --- | --- |
| Original unmodified Java `MainActivity` | `setContentView(R.layout.activity_main)` |
| Android-compiled XML layout | One root TextView, `android:text=@string/hello_world` |
| Host ART console | `TextView: Hello world!`, Activity lifecycle cleanup |
| Host ART GTK4 Wayland | Real headless Weston window, GTK label verified, clean close |
| Nested LinearLayout and view attributes | Not supported by XML inflater |
| Other third-party APKs | Not verified; needs independent matrix expansion |

The binary XML inflater accepts only a **single root TextView** with literal
or `R.string`-backed `android:text`. It caps layout reads at 1 MiB, string
count at 8192, and XML attributes at 256. It deliberately rejects unknown
view trees instead of silently showing incorrect UIs; no `findViewById`,
style/theme, layout sizing, translations or density variants are implemented.

The GTK integration verification uses a test-only timed auto-close and
checks the realized GTK label. It does not simulate physical pointer input.
ANX is still not safe for running untrusted Android apps.
