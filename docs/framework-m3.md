# M3 framework scope (v0.0.4 development)

ANX now constructs the `Application` declared in the binary manifest, prepares a
main `Looper`, binds the `Activity` to that application and its launcher `Intent`,
and dispatches its lifecycle via `Instrumentation`. The CLI passes the
manifest package, application class, and APK path to the ART entry point.

## Implemented API subset

- `Application.onCreate` and host-only `Application.onTerminate`.
- `Activity` lifecycle: create, start, resume, pause, stop, destroy.
- `Context.getApplicationContext`, `getPackageName`, `getAssets`, `getResources` (placeholder).
- Explicit `Intent` class/action/categories and primitive extras.
- `Bundle` for strings, ints, booleans, nested Bundles and copies.
- `Looper`, `MessageQueue`, `Handler.post`, `postDelayed`,
  `sendMessage`, `removeCallbacks`, `removeMessages`.
- `AssetManager.open` for read-only `assets/*` ZIP entries, with path validation. Compiled resource-ID lookups fail with `Resources.NotFoundException`.
- `View.OnClickListener` and `Button.performClick` as API building blocks.

## Execution model and remaining gaps

The console MVP calls `Looper.drainForHost()` **once** after `onResume`.
Only callbacks that are already due execute; future delayed callbacks do not
keep the process alive. Full `Looper.loop()` is available, but a persistent
window/event bridge is required before using it for normal APK GUI execution.

There is no `resources.arsc` resolver, `Resources.getString`, Android framework
service stack, Binder, nested activity navigation, background service or
window manager. `Application.onTerminate` is a host cleanup callback, not
a guaranteed Android lifecycle event. There is no renderer or real desktop
click input, so **M4/M5 acceptance criteria are not met**.

## Verification

```sh
bash tests/smoke.sh
bash tests/framework-smoke.sh
bash tests/apk-inspect-smoke.sh
# Host ART integration requires installed or containerized patched ART:
bash scripts/run-art-alpine.sh
```

The first two are JVM tests, not proof of ART. The third needs Android SDK
build tools (D8/aapt). The last needs Podman, Android SDK, and the pinned
ART runtime; pass/fail must be checked on the target host.

**Security:** ANX does not sandbox APK code; only launch trusted test APKs.
ZIP bounds checking is not process isolation.
