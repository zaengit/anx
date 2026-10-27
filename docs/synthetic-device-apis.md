# Experimental synthetic Android identity and clipboard APIs

The host `android.os.Build.VERSION.SDK_INT=26` and
`VERSION.RELEASE="ANX-host-compatibility"` values exist exclusively to
satisfy SDK-compiled Android bytecode. They are **not** an Android OS version
or a substitute for runtime capability detection.

`Settings.Secure.getString(ContentResolver, ANDROID_ID)` returns the
literal marker `anx-host-not-an-android-device`. It never reads a real
hardware ID, account identifier, or private host configuration.

The in-memory `android.content.ClipboardManager`, legacy
`android.text.ClipboardManager`, `ClipData` and
`View.OnLongClickListener` APIs support local JVM compatibility only.
GTK4 attaches a long-press controller to the primary TextView and sends
its event into the ART main thread. CI emits a **test-only synthetic GTK
gesture signal**, rather than compositor-injected pointer input. There is
**no shared desktop clipboard**. `Toast.show()` writes a console diagnostic, **not** a native
notification. Unsupported `Context.getSystemService` names return null.
Any app depending on true Android device identity or system services may
fail or behave differently.

Verification: `bash tests/framework-smoke.sh` and the two independently
authored APK cases in `bash scripts/run-art-alpine.sh`.
