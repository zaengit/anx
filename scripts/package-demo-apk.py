#!/usr/bin/env python3
"""Combine aapt's binary manifest package with a separately compiled DEX."""
import argparse
from pathlib import Path
import sys
import zipfile


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("metadata_apk", type=Path)
    parser.add_argument("dex", type=Path)
    parser.add_argument("output_apk", type=Path)
    args = parser.parse_args()
    try:
        args.output_apk.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(args.metadata_apk) as source, zipfile.ZipFile(
            args.output_apk, "w", compression=zipfile.ZIP_DEFLATED
        ) as output:
            for entry in source.infolist():
                if entry.filename != "classes.dex":
                    output.writestr(entry, source.read(entry))
            output.write(args.dex, "classes.dex")
    except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
        print(f"Could not package demo APK: {exc}", file=sys.stderr)
        return 1
    print(f"[OK] Demo APK: {args.output_apk}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
