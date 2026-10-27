#!/usr/bin/env python3
"""Negative native loader cases need no Android SDK or host ART."""
from pathlib import Path
import stat
import struct
import sys
from tempfile import TemporaryDirectory
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from native_libraries import NativeLibraryError, extract_native_libraries
from apk_inspector import ApkMetadata
from apk_manifest import ManifestInfo


def elf(arch=62):
    data = bytearray(64)
    data[:6] = b"\x7fELF\x02\x01"
    struct.pack_into("<H", data, 18, arch)
    return bytes(data)


class NativeLibraryTest(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.apk = self.root / "fixture.apk"

    def write(self, filename="lib/x86_64/libok.so", data=None, symlink=False):
        with zipfile.ZipFile(self.apk, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            if symlink:
                info = zipfile.ZipInfo(filename)
                info.create_system = 3
                info.external_attr = (stat.S_IFLNK | 0o777) << 16
                archive.writestr(info, "target")
            else:
                archive.writestr(filename, elf() if data is None else data)

    def meta(self, abi="x86_64"):
        return ApkMetadata(self.apk, ManifestInfo("org.example", None, (), ()),
                           ("classes.dex",), ((abi, 1),), 1, 64)

    def extract(self, abi="x86_64"):
        folder = self.root / "output"
        folder.mkdir(exist_ok=True)
        return extract_native_libraries(self.meta(abi), folder)

    def test_valid_elf(self):
        self.write()
        self.assertEqual(("x86_64", ("libok.so",)), self.extract())
        self.assertEqual(elf(), (self.root / "output/libok.so").read_bytes())

    def test_arm_host_abi_rejected(self):
        self.write("lib/arm64-v8a/libok.so")
        with self.assertRaisesRegex(NativeLibraryError, "no matching"):
            self.extract("arm64-v8a")

    def test_symlink_not_followed(self):
        self.write(symlink=True)
        with self.assertRaisesRegex(NativeLibraryError, "regular file"):
            self.extract()

    def test_malformed_name(self):
        self.write("lib/x86_64/foo.so")
        with self.assertRaisesRegex(NativeLibraryError, "invalid native"):
            self.extract()

    def test_wrong_machine(self):
        self.write(data=elf(183))
        with self.assertRaisesRegex(NativeLibraryError, "architecture"):
            self.extract()
        self.assertFalse((self.root / "output/libok.so").exists())

    def test_not_elf(self):
        self.write(data=b"not-elf" * 10)
        with self.assertRaisesRegex(NativeLibraryError, "not ELF"):
            self.extract()

    def test_preexisting_destination_rejected(self):
        self.write()
        folder = self.root / "output"
        folder.mkdir()
        (folder / "libok.so").write_bytes(b"already there")
        with self.assertRaisesRegex(NativeLibraryError, "empty directory"):
            extract_native_libraries(self.meta(), folder)


if __name__ == "__main__":
    unittest.main()
