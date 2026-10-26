# M6 additional API compatibility subset

ANX implements the following deliberately limited APIs:

- `android.util.Log`: v/d/i/w/e/wtf, Throwable variants, printing and stack
  traces through the Linux process streams. No Android logd, logcat buffers,
  per-tag filtering or persistent system log retention.
- `Context.getPackageManager()`, `PackageManager.getPackageInfo()` and
  `getApplicationInfo()` for **the current ANX package only**, plus
  `getInstalledPackages()` returning only that package.
- `hasSystemFeature()` always returns false rather than misrepresenting
  real phone hardware.
- `PackageInfo.versionCode=0` and `versionName=null`: unknown; ANX does
  not fabricate manifest version metadata or signatures.

These API methods do **not** emulate Binder, installed Android packages,
permissions, signing certificates, Android system services or resources. Apps
requiring those capabilities remain unsupported.

`tests/framework-smoke.sh` verifies these Java APIs and the ART container
runs the standalone `HelloApplication` with Log and PackageManager calls.

See [app-storage.md](app-storage.md) for the existing persistent preferences
and private app file API subset.
