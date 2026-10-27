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
        self.assertIn("/anx/apps", argv)
        self.assertIn("/anx/data", argv)
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
