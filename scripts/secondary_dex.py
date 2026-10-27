"""Bounded extraction of secondary APK DEX files for pinned host ART.

This is an APK execution facility, not a safe bytecode verifier or sandbox.
Metadata must have been validated by inspect_apk before calling this module.
"""
from __future__ import annotations

import os
from pathlib import Path
import stat
import zipfile

from apk_inspector import ApkMetadata

MAX_DEX_FILES = 16
MAX_SECONDARY_DEX_BYTES = 64 * 1024 * 1024
MAX_SECONDARY_TOTAL_BYTES = 128 * 1024 * 1024


class SecondaryDexError(ValueError):
    """Invalid or unsupported secondary DEX for host execution."""


def extract_secondary_dex(metadata: ApkMetadata, destination: Path) -> tuple[Path, ...]:
    secondary = metadata.dex_files[1:]
    if not secondary:
        return ()
    if len(metadata.dex_files) > MAX_DEX_FILES:
        raise SecondaryDexError("APK contains too many DEX files (max 16)")
    if not destination.is_dir() or destination.is_symlink() or any(destination.iterdir()):
        raise SecondaryDexError("secondary DEX destination must be a private empty directory")
    paths: list[Path] = []
    try:
        with zipfile.ZipFile(metadata.path, "r") as archive:
            infos = [archive.getinfo(name) for name in secondary]
            total = 0
            for index, info in enumerate(infos, start=2):
                if info.filename != f"classes{index}.dex":
                    raise SecondaryDexError("secondary DEX sequence is not contiguous")
                mode = (info.external_attr >> 16) & 0xFFFF
                if stat.S_IFMT(mode) not in (0, stat.S_IFREG):
                    raise SecondaryDexError(f"secondary DEX is not a regular file: {info.filename}")
                if info.file_size < 8 or info.file_size > MAX_SECONDARY_DEX_BYTES:
                    raise SecondaryDexError(f"secondary DEX size exceeds safety bounds: {info.filename}")
                total += info.file_size
                if total > MAX_SECONDARY_TOTAL_BYTES:
                    raise SecondaryDexError("secondary DEX entries exceed combined size limit")
            for info in infos:
                name = info.filename  # trusted canonical classesN.dex, not a ZIP-supplied path
                target = destination / name
                flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
                descriptor = os.open(target, flags, 0o600)
                try:
                    with os.fdopen(descriptor, "wb") as output, archive.open(info) as source:
                        prefix = source.read(8)
                        if (len(prefix) != 8 or prefix[:4] != b"dex\n"
                                or prefix[4:7] not in
                                (b"035", b"037", b"038", b"039", b"040", b"041", b"042")
                                or prefix[7] != 0):
                            raise SecondaryDexError(f"secondary DEX header is invalid: {name}")
                        output.write(prefix)
                        count = 8
                        while True:
                            data = source.read(1024 * 1024)
                            if not data:
                                break
                            count += len(data)
                            if count > MAX_SECONDARY_DEX_BYTES:
                                raise SecondaryDexError(f"secondary DEX decompressed beyond limit: {name}")
                            output.write(data)
                        if count != info.file_size:
                            raise SecondaryDexError(f"secondary DEX length mismatch: {name}")
                    os.chmod(target, 0o400)
                    paths.append(target)
                except BaseException:
                    target.unlink(missing_ok=True)
                    raise
        return tuple(paths)
    except SecondaryDexError:
        raise
    except (OSError, ValueError, RuntimeError, zipfile.BadZipFile, EOFError, KeyError) as exc:
        raise SecondaryDexError(f"secondary DEX extraction failed: {exc}") from exc
