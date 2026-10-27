"""Constrained *host-ABI* JNI library extraction for trusted APK fixtures only.

This does not implement Bionic, Android linker namespaces or ARM translation.
Only the x86_64 host target is currently supported. Inspection must precede it.
"""
from __future__ import annotations

import os
from pathlib import Path
import platform
import re
import stat
import struct
import zipfile

from apk_inspector import ApkMetadata

MAX_LIBRARIES = 32
MAX_NATIVE_BYTES = 64 * 1024 * 1024
MAX_SINGLE_LIBRARY = 32 * 1024 * 1024
HOST_ABI = "x86_64"
LIBRARY_NAME = re.compile(r"lib[A-Za-z0-9_+.-]+\.so\Z")


class NativeLibraryError(ValueError):
    """Unsupported native ABI, ELF format, ZIP entry or library layout."""


def _validate_elf_header(header: bytes, filename: str) -> None:
    if len(header) < 20 or header[:4] != b"\x7fELF":
        raise NativeLibraryError(f"native file is not ELF: {filename}")
    if header[4] != 2 or header[5] != 1:  # ELFCLASS64, little endian
        raise NativeLibraryError(f"native file is not a little-endian ELF64: {filename}")
    if struct.unpack_from("<H", header, 18)[0] != 62:  # EM_X86_64
        raise NativeLibraryError(f"ELF architecture is not x86_64: {filename}")


def extract_native_libraries(metadata: ApkMetadata, destination: Path) -> tuple[str, tuple[str, ...]]:
    """Stream verified x86_64 libs into an empty, private temp directory.

    Paths are never taken directly from ZIP names. zipfile validates CRC at EOF.
    This function does not make an unsafe APK safe to execute.
    """
    machine = platform.machine().lower()
    if machine not in ("x86_64", "amd64"):
        raise NativeLibraryError(f"unsupported Linux host CPU: {machine}")
    available = dict(metadata.native_abis)
    if HOST_ABI not in available:
        raise NativeLibraryError(
            f"APK has no matching {HOST_ABI} native libraries: {', '.join(sorted(available))}"
        )
    if not destination.is_dir() or any(destination.iterdir()):
        raise NativeLibraryError("native destination must be an empty directory")
    if destination.is_symlink():
        raise NativeLibraryError("native destination may not be a symlink")

    selected: list[zipfile.ZipInfo] = []
    try:
        with zipfile.ZipFile(metadata.path, "r") as archive:
            for entry in archive.infolist():
                parts = entry.filename.split("/")
                if len(parts) != 3 or parts[0] != "lib" or parts[1] != HOST_ABI:
                    continue
                if not parts[2].endswith(".so"):
                    continue
                if not LIBRARY_NAME.fullmatch(parts[2]):
                    raise NativeLibraryError(f"invalid native library name: {entry.filename}")
                mode = (entry.external_attr >> 16) & 0xFFFF
                if stat.S_IFMT(mode) not in (0, stat.S_IFREG):
                    raise NativeLibraryError(f"native library is not a regular file: {entry.filename}")
                if entry.file_size < 20 or entry.file_size > MAX_SINGLE_LIBRARY:
                    raise NativeLibraryError(f"native file outside size limit: {entry.filename}")
                selected.append(entry)
            if len(selected) != available[HOST_ABI] or len(selected) > MAX_LIBRARIES:
                raise NativeLibraryError("too many or malformed native library entries")
            if sum(entry.file_size for entry in selected) > MAX_NATIVE_BYTES:
                raise NativeLibraryError("native libraries exceed total size limit")
            names: list[str] = []
            for entry in selected:
                basename = entry.filename.rsplit("/", 1)[1]
                flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
                flags |= getattr(os, "O_NOFOLLOW", 0)
                output = destination / basename
                fd = os.open(output, flags, 0o600)
                try:
                    with os.fdopen(fd, "wb") as sink, archive.open(entry, "r") as stream:
                        header = stream.read(20)
                        _validate_elf_header(header, basename)
                        sink.write(header)
                        size = len(header)
                        while True:
                            data = stream.read(1024 * 1024)
                            if not data:
                                break
                            size += len(data)
                            if size > MAX_SINGLE_LIBRARY:
                                raise NativeLibraryError(f"native file exceeded size limit: {basename}")
                            sink.write(data)
                        if size != entry.file_size:
                            raise NativeLibraryError(f"native ZIP file size changed: {basename}")
                    names.append(basename)
                except BaseException:
                    output.unlink(missing_ok=True)
                    raise
            return HOST_ABI, tuple(names)
    except NativeLibraryError:
        raise
    except (OSError, ValueError, RuntimeError, zipfile.BadZipFile, EOFError) as exc:
        raise NativeLibraryError(f"native library extraction failed: {exc}") from exc
