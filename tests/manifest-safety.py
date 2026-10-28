#!/usr/bin/env python3
"""Regression for truncated Android binary XML string-pool entries."""
from pathlib import Path
import struct
import sys
import tempfile
import unittest
import zipfile
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from apk_manifest import ManifestError, _length8, _parse_string_pool, parse_binary_manifest
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
    @staticmethod
    def pool(encoded: bytes, *, utf8: bool = True, strings_start: int = 32) -> bytes:
        """One-string Android string pool with a 28-byte header and one offset."""
        return (struct.pack("<HHIIIIII", 1, 28, 32 + len(encoded), 1, 0,
                            0x100 if utf8 else 0, strings_start, 0)
                + struct.pack("<I", 0) + encoded)

    def test_terminated_strings_still_parse(self):
        self.assertEqual(_parse_string_pool(self.pool(b"\x01\x01A\x00"),
                                             0, 36, 28), ["A"])
        utf16 = self.pool(b"\x01\x00A\x00\x00\x00", utf8=False)
        self.assertEqual(_parse_string_pool(utf16, 0, len(utf16), 28), ["A"])

    def test_string_pool_rejects_missing_terminators(self):
        for encoded, utf8 in (
            (b"\x01\x01A\x7f", True),
            (b"\x01\x00A\x00\x7f\x00", False),
        ):
            with self.subTest(utf8=utf8):
                pool = self.pool(encoded, utf8=utf8)
                with self.assertRaisesRegex(ManifestError, "unterminated"):
                    _parse_string_pool(pool, 0, len(pool), 28)

    def test_string_pool_rejects_offset_array_overlap(self):
        pool = self.pool(b"\x01\x01A\x00", strings_start=28)
        with self.assertRaisesRegex(ManifestError, "overlaps"):
            _parse_string_pool(pool, 0, len(pool), 28)

    def test_unclosed_manifest_element_fails_closed(self):
        # A valid string pool followed by a start tag with no matching end tag.
        pool = self.pool(b"\x08\x08manifest\x00")
        start = (struct.pack("<HHI", 0x0102, 16, 36)
                 + struct.pack("<II", 0, 0)
                 + struct.pack("<IIHHHHHH", 0xffffffff, 0, 20, 20, 0, 0, 0, 0))
        body = pool + start
        xml = struct.pack("<HHI", 3, 8, 8 + len(body)) + body
        with self.assertRaisesRegex(ManifestError, "unclosed XML"):
            parse_binary_manifest(xml)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "unclosed.apk"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("AndroidManifest.xml", xml)
            with self.assertRaisesRegex(ApkError, "unclosed XML"):
                inspect_apk(path)

if __name__ == "__main__":
    unittest.main()
