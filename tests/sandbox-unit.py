#!/usr/bin/env python3
"""Structural sandbox assertions; does NOT certify kernel namespace isolation."""
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))
from sandbox import SandboxError, wrap_console_art


class SandboxCommandTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = pathlib.Path(self.temp.name)
        self.framework = root / "framework.dex"
        self.apk = root / "app.apk"
        self.framework.write_bytes(b"dex")
        self.apk.write_bytes(b"zip")
        self.data = root / "android-data"
        self.apps = root / "apps"
        self.native = root / "native"
        self.data.mkdir()
        self.apps.mkdir()
        self.native.mkdir()

    def command(self, **kwargs):
        return wrap_console_art(
            art_executable=kwargs.pop("art", pathlib.Path("/usr/bin/java")),
            framework_dex=self.framework,
            apk_path=self.apk,
            launcher="org.anx.fixture.Activity",
            package="org.anx.fixture",
            application="-",
            android_data=self.data,
            app_data_root=self.apps,
            bubblewrap_executable=kwargs.pop("bwrap", "/usr/bin/bwrap"),
            **kwargs,
        )

    def test_restricted_binds_and_network(self):
        argv = self.command()
        self.assertIn("--unshare-all", argv)
        self.assertNotIn("--share-net", argv)
        self.assertIn("--clearenv", argv)
        self.assertEqual(argv.count("--bind"), 2)
        self.assertIn("/anx/apps/org.anx.fixture", argv)
        self.assertIn("/anx/data", argv)
        self.assertIn(str((self.data / "org.anx.fixture").resolve()), argv)
        self.assertNotIn(str(self.data.resolve()), argv)
        self.assertEqual(argv[-5:], ["org.anx.launcher.Main",
                                     "org.anx.fixture.Activity",
                                     "org.anx.fixture", "-", "/anx/app.apk"])
        self.assertNotIn(str(pathlib.Path.home()), argv)

    def test_native_read_only(self):
        argv = self.command(native_directory=self.native)
        self.assertIn("-Djava.library.path=/anx/native", argv)
        self.assertIn(str(self.native), argv)
        pos = argv.index(str(self.native))
        self.assertEqual("--ro-bind", argv[pos - 1])

    def test_cannot_read_other_package_mount(self):
        sibling = self.apps / "org.example.other"
        sibling.mkdir()
        (sibling / "secret.txt").write_text("private", encoding="utf-8")
        argv = self.command()
        self.assertNotIn(str(sibling.resolve()), argv)
        self.assertIn(str((self.apps / "org.anx.fixture").resolve()), argv)

    def test_does_not_mount_sibling_art_caches(self):
        sibling = self.data / "org.other"
        sibling.mkdir()
        (sibling / "cache.bin").write_bytes(b"secret")
        argv = self.command()
        self.assertIn(str((self.data / "org.anx.fixture").resolve()), argv)
        self.assertNotIn(str(sibling.resolve()), argv)

    def test_art_cache_symlink_rejected(self):
        (self.data / "org.anx.fixture").symlink_to(self.native, target_is_directory=True)
        with self.assertRaisesRegex(SandboxError, "ART cache directory cannot be a symlink"):
            self.command()

    def test_invalid_package_rejected(self):
        with self.assertRaisesRegex(SandboxError, "invalid package identifier"):
            wrap_console_art(
                art_executable=pathlib.Path("/usr/bin/java"),
                framework_dex=self.framework, apk_path=self.apk,
                launcher="org.demo.Activity", package="../escape",
                application="-", android_data=self.data, app_data_root=self.apps,
                bubblewrap_executable="/usr/bin/bwrap",
            )

    def test_missing_bwrap_rejected(self):
        with self.assertRaisesRegex(SandboxError, "required"):
            self.command(bwrap="")

    def test_untrusted_art_path_rejected(self):
        with self.assertRaisesRegex(SandboxError, "under /usr or /bin"):
            self.command(art=self.framework)

    def test_missing_framework_rejected(self):
        self.framework.unlink()
        with self.assertRaisesRegex(SandboxError, "does not exist"):
            self.command()


if __name__ == "__main__":
    unittest.main()
