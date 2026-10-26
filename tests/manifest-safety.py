#!/usr/bin/env python3
"""Regression for truncated Android binary XML string-pool entries."""
from pathlib import Path
import struct
import sys
import tempfile
import unittest
import zipfile
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from apk_manifest import ManifestError, _length8, parse_binary_manifest
from apk_inspector import ApkError, inspect_apk

class BinaryManifestSafetyTest(unittest.TestCase):
    def test_truncated_utf8_lengths(self):
        for data, offset in ((b"", 0), (b"\x80", 0), (b"\x00", 1)):
            with self.subTest(data=data, offset=offset):
                with self.assertRaises(ManifestError):
                    _length8(data, offset)
    def test_truncated_string_pool(self):
        chunk = struct.pack("<HHIIIIII", 1, 28, 33, 1, 0, 0x100, 32, 0)
        chunk += struct.pack("<I", 0) + b"\x01"
        xml = struct.pack("<HHI", 3, 8, 8 + len(chunk)) + chunk
        with self.assertRaises(ManifestError):
            parse_binary_manifest(xml)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "truncated.apk"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("AndroidManifest.xml", xml)
            with self.assertRaises(ApkError):
                inspect_apk(path)
if __name__ == "__main__":
    unittest.main()
