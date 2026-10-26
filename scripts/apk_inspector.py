"""Safe, metadata-only APK inspection (no APK entries are extracted)."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import re
import struct
import zipfile
import zlib

from apk_manifest import ManifestError, ManifestInfo, parse_binary_manifest


MAX_APK_SIZE = 2 * 1024 * 1024 * 1024
MAX_ENTRY_SIZE = 512 * 1024 * 1024
MAX_TOTAL_UNCOMPRESSED = 1024 * 1024 * 1024
MAX_ENTRIES = 20_000
MAX_COMPRESSION_RATIO = 2_000
MAX_MANIFEST_SIZE = 4 * 1024 * 1024
DEX_NAME = re.compile(r"^classes(?:(?P<index>[2-9][0-9]*))?\.dex$")


class ApkError(ValueError):
    """The APK is invalid, unsafe to inspect, or lacks required metadata."""


@dataclass(frozen=True)
class ApkMetadata:
    path: Path
    manifest: ManifestInfo
    dex_files: tuple[str, ...]
    native_abis: tuple[tuple[str, int], ...]
    entry_count: int
    uncompressed_size: int


def inspect_apk(path: Path) -> ApkMetadata:
    path = path.expanduser().resolve()
    try:
        archive_size = path.stat().st_size
        if archive_size > MAX_APK_SIZE:
            raise ApkError(f"APK size exceeds the {MAX_APK_SIZE}-byte limit")
        with zipfile.ZipFile(path, "r") as archive:
            entries = archive.infolist()
            if len(entries) > MAX_ENTRIES:
                raise ApkError(f"APK has more than {MAX_ENTRIES} ZIP entries")
            names = [entry.filename for entry in entries]
            duplicate_names = sorted(name for name, count in Counter(names).items() if count > 1)
            if duplicate_names:
                raise ApkError(f"APK contains duplicate ZIP entry names: {', '.join(duplicate_names[:3])}")

            total_uncompressed = 0
            for entry in entries:
                if entry.file_size < 0 or entry.compress_size < 0:
                    raise ApkError(f"invalid ZIP size for entry {entry.filename!r}")
                if entry.file_size > MAX_ENTRY_SIZE:
                    raise ApkError(f"ZIP entry exceeds the {MAX_ENTRY_SIZE}-byte limit: {entry.filename}")
                total_uncompressed += entry.file_size
                if total_uncompressed > MAX_TOTAL_UNCOMPRESSED:
                    raise ApkError("APK uncompressed contents exceed the 1 GiB limit")
                if entry.file_size and not entry.compress_size:
                    raise ApkError(f"invalid zero compressed size for {entry.filename!r}")
                if entry.compress_size and entry.file_size > entry.compress_size * MAX_COMPRESSION_RATIO:
                    raise ApkError(f"suspicious compression ratio for {entry.filename!r}")

            manifest_name = "AndroidManifest.xml"
            if manifest_name not in names:
                raise ApkError("APK does not contain AndroidManifest.xml")
            manifest_entry = archive.getinfo(manifest_name)
            if manifest_entry.file_size > MAX_MANIFEST_SIZE:
                raise ApkError("AndroidManifest.xml exceeds the 4 MiB limit")
            manifest_data = archive.read(manifest_entry)  # also verifies the manifest CRC
            try:
                manifest = parse_binary_manifest(manifest_data)
            except ManifestError as exc:
                raise ApkError(f"cannot parse AndroidManifest.xml: {exc}") from exc

            dex_indices: list[tuple[int, str]] = []
            native_abis: Counter[str] = Counter()
            for name in names:
                match = DEX_NAME.fullmatch(name)
                if match:
                    index = int(match.group("index") or "1")
                    dex_indices.append((index, name))
                parts = name.split("/")
                if len(parts) == 3 and parts[0] == "lib" and parts[2].endswith(".so"):
                    native_abis[parts[1]] += 1

            dex_indices.sort()
            indices = [index for index, _ in dex_indices]
            if len(set(indices)) != len(indices):
                raise ApkError("APK contains duplicate DEX indices")
            if indices and indices[0] != 1:
                raise ApkError("multidex sequence is missing classes.dex")
            if indices and indices != list(range(1, indices[-1] + 1)):
                raise ApkError("multidex sequence contains a missing DEX file")

            # Read DEX entries in bounded chunks so CRC errors are caught without extraction.
            for _, name in dex_indices:
                actual_size = 0
                with archive.open(name, "r") as stream:
                    while True:
                        chunk = stream.read(1024 * 1024)
                        if not chunk:
                            break
                        actual_size += len(chunk)
                        if actual_size > MAX_ENTRY_SIZE:
                            raise ApkError(f"DEX entry expands beyond the size limit: {name}")

            return ApkMetadata(
                path=path,
                manifest=manifest,
                dex_files=tuple(name for _, name in dex_indices),
                native_abis=tuple(sorted(native_abis.items())),
                entry_count=len(entries),
                uncompressed_size=total_uncompressed,
            )
    except ApkError:
        raise
    except (OSError, zipfile.BadZipFile, EOFError, RuntimeError, ValueError,
            NotImplementedError, struct.error, zlib.error) as exc:
        raise ApkError(f"cannot read APK: {exc}") from exc


def format_metadata(metadata: ApkMetadata) -> str:
    manifest = metadata.manifest
    if len(manifest.launchers) == 1:
        launcher = manifest.launcher_activity
    elif manifest.launchers:
        launcher = "ambiguous: " + ", ".join(item.component_name for item in manifest.launchers)
    else:
        launcher = "not found"
    app_name = manifest.application_name or "(default Application)"
    dex = ", ".join(metadata.dex_files) or "none"
    abis = ", ".join(f"{abi} ({count})" for abi, count in metadata.native_abis) or "none"
    return "\n".join((
        f"APK: {metadata.path}",
        f"Package: {manifest.package_name}",
        f"Application: {app_name}",
        f"Launcher activity: {launcher}",
        f"Activities: {', '.join(item.name for item in manifest.activities) or 'none'}",
        f"DEX: {dex}",
        f"Native ABIs: {abis}",
        f"ZIP entries: {metadata.entry_count}",
        f"Uncompressed size: {metadata.uncompressed_size} bytes",
    ))
