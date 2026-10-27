#!/usr/bin/env python3
"""Secondary DEX extraction guard tests, no Android SDK required."""
from pathlib import Path
import stat
import sys
from tempfile import TemporaryDirectory
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from apk_inspector import ApkMetadata
from apk_manifest import ManifestInfo
from secondary_dex import SecondaryDexError, extract_secondary_dex


class SecondaryDexTest(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.apk = self.root / "fixture.apk"
        self.dest = self.root / "dest"
        self.dest.mkdir()

    def metadata(self, count=2):
        names = ("classes.dex",) + tuple(f"classes{i}.dex" for i in range(2, count + 1))
        return ApkMetadata(self.apk, ManifestInfo("org.anx.test", None, (), ()),
                           names, (), 1, 16)

    def pack(self, payload=b"dex\n035\x00" + b"fixture-payload",
             filename="classes2.dex", symlink=False):
        with zipfile.ZipFile(self.apk, "w", compression=zipfile.ZIP_DEFLATED) as output:
            if symlink:
                entry = zipfile.ZipInfo(filename)
                entry.create_system = 3
                entry.external_attr = (stat.S_IFLNK | 0o777) << 16
                output.writestr(entry, payload)
            else:
                output.writestr(filename, payload)

    def test_valid_secondary_dex_and_readonly_mode(self):
        self.pack()
        paths = extract_secondary_dex(self.metadata(), self.dest)
        self.assertEqual((self.dest / "classes2.dex",), paths)
        self.assertEqual(b"dex\n035\x00", paths[0].read_bytes()[:8])
        self.assertEqual(0o400, paths[0].stat().st_mode & 0o777)

    def test_malformed_header_rejected(self):
        self.pack(b"wrong dex header")
        with self.assertRaisesRegex(SecondaryDexError, "header"):
            extract_secondary_dex(self.metadata(), self.dest)
        self.assertEqual([], list(self.dest.iterdir()))

    def test_secondary_zip_symlink_rejected(self):
        self.pack(symlink=True)
        with self.assertRaisesRegex(SecondaryDexError, "regular file"):
            extract_secondary_dex(self.metadata(), self.dest)

    def test_limit_on_dex_count(self):
        self.pack()
        with self.assertRaisesRegex(SecondaryDexError, "too many"):
            extract_secondary_dex(self.metadata(count=17), self.dest)

    def test_existing_destination_is_rejected(self):
        self.pack()
        (self.dest / "classes2.dex").write_bytes(b"old")
        with self.assertRaisesRegex(SecondaryDexError, "empty"):
            extract_secondary_dex(self.metadata(), self.dest)


if __name__ == "__main__":
    unittest.main()
