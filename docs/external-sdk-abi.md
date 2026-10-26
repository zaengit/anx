# Independently compiled Android SDK API fixture

`tests/fixtures/external-app/` contains a small real Android
`Application` and `Activity` example. `scripts/build-external-apk.sh`
compiles Java against **Android SDK `android.jar` only**, runs D8, and packages
a binary manifest through `aapt`. No ANX `android.*` classes are on the
compiler classpath. This catches binary descriptor mismatches hidden when
ANX's own demo builds against its replacement framework.

Verification:

```sh
bash scripts/build-external-apk.sh
./anx inspect build/external.apk
bash scripts/run-art-alpine.sh
```

The ART reference invokes the APK's declared Application and launcher,
validates the SharedPreferences ABI (`android.content.SharedPreferences`),
current-package PackageManager and Android Log. The Weston headless CI then
opens a native GTK4 Wayland window and checks the Java Button listener
updates the GTK label using an automated GTK signal.

The test is deliberately limited to one DEX, no native `.so`, and simple
views. It is a local API/ABI fixture, not a redistributable sample of the
wider F-Droid ecosystem or general Android APK compatibility. Unknown
APKs remain unsafe to run; see SECURITY.md.
