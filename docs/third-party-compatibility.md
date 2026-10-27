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
| Nested vertical LinearLayout, TextView, Button IDs | Supported in a separate SDK fixture; **not yet independently authored APK** |
| Other third-party APKs | Not verified; needs independent matrix expansion |

The binary XML inflater now accepts a root TextView or a **vertical LinearLayout**
with nested vertical layouts, TextView and Button nodes, each with optional
`android:id`, literal or R.string-backed `android:text`, and XML
`Button android:onClick="methodName"` bound only to a public `void` Activity
method taking one View argument. Missing/mismatched method signatures fail at
inflation, preserving the existing Activity content. The SDK-only
`tests/fixtures/nested-app` exercises `findViewById`, nested IDs and a click
callback under ART + GTK/Weston. It is **not a second independent third-party
APK**. The inflater caps layouts at 1 MiB, at most 16 nodes, 4 nesting levels,
8192 strings and 256 attributes per node. It rejects unsupported view types.
Styles, geometry, themes, density/locale selection and full Android rendering
remain absent.

The GTK integration verification uses a test-only timed auto-close and
checks the realized GTK label. It does not simulate physical pointer input.
ANX is still not safe for running untrusted Android apps.
