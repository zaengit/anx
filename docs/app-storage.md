# M6 app-local storage subset

The runtime supports `Context.getFilesDir`, `getCacheDir`,
`openFileInput`, `openFileOutput`, `deleteFile` and typed
`SharedPreferences` using Java properties as a private ANX disk format
(**not** Android XML preferences). Paths use the `ANX_APP_DATA_HOME`
environment variable or `~/.local/share/anx/apps`.

These paths are namespaced by validated Android package names. Simple file
names only are accepted; traversal and slash-containing names are rejected.
`SharedPreferences.Editor.commit` writes a temporary file, fsyncs it,
and atomically renames it on Linux. In-process commits are serialized;
cross-process locking, listeners, StringSet, encryption and migrations
are not implemented. `apply` commits synchronously and can throw on
failure (unlike Android's asynchronous semantics).

## Verification

```sh
bash tests/framework-smoke.sh
bash scripts/run-art-alpine.sh
```

The separate demo APK exercises preferences during `Application.onCreate`.
The Java storage smoke validates primitive types, a second context reading
persisted data, append, deletion, namespace separation, and path rejection.
The ART container test also exercises the same demo application.

**Important:** This does **not** restrict what a malicious APK can access.
ANX has no OS-level process sandbox yet; these are convenience app directories,
not a security boundary. Run only trusted APKs.
