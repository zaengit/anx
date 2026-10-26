#!/usr/bin/env python3
"""Inspect APK metadata without extracting or executing its contents."""
import argparse
from pathlib import Path
import sys

from apk_inspector import ApkError, format_metadata, inspect_apk


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("apk", type=Path)
    args = parser.parse_args()
    try:
        print(format_metadata(inspect_apk(args.apk)))
        return 0
    except ApkError as exc:
        print(f"anx inspect: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
