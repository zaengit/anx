# Third-party runtime provenance

ANX does not vendor ART or libcore. The initial host-runtime reference is
the AOSP-derived `android_translation_layer/art_standalone` repository at:

- Repository: <https://gitlab.com/android_translation_layer/art_standalone>
- Pinned commit: `a1edfc40e8cea3644d80e4e776d3fa7fc397a1c2`
- Pin date: 2026-10-18
- Source history note: the upstream README says the tree was assembled from
  the `android-6.0.1_r46` dalvik branch, with ART and libcore updated
  separately.
- Upstream license notices: `art/MODULE_LICENSE_APACHE2`,
  `libcore/LICENSE`, and the per-component `NOTICE`/license files in the
  checkout.
- Local compatibility patch: `patches/art_standalone-jni-onunload.patch`
  avoids a shutdown abort in the pinned libcore's `JNI_OnUnload` callback. The
  patch changes only the shutdown cleanup call; retain it with the pinned
  runtime until an upstream revision includes the fix.

The runtime build also uses external native dependencies, including
`bionic_translation` and WolfSSL configured with JNI. Their versions and
licenses depend on the selected host package/build and must be recorded by a
runtime distributor. ANX does not currently redistribute those binaries.
Keep all upstream license and copyright notices when packaging a runtime; do
not assume the ART source license covers every dependency.

The app repository's own license has not yet been selected. That decision is
separate from the ART/libcore source provenance and is a release prerequisite.
