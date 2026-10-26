#!/usr/bin/env python3
"""ANX command line for APK inspection and the current ART demo subset."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys

from apk_inspector import ApkError, format_metadata, inspect_apk


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_FRAMEWORK_DEX = ROOT / "build" / "framework" / "classes.dex"


def _run(apk: Path, art: str, framework_dex: Path, android_data: Path | None) -> int:
    try:
        metadata = inspect_apk(apk)
    except ApkError as exc:
        print(f"anx run: {exc}", file=sys.stderr)
        return 1

    manifest = metadata.manifest
    if not metadata.dex_files:
        print("anx run: APK contains no classes.dex", file=sys.stderr)
        return 1
    if len(metadata.dex_files) > 1:
        print("anx run: multidex APKs are detected but not loadable yet", file=sys.stderr)
        return 1
    if metadata.native_abis:
        print("anx run: APK contains native libraries; JNI loading is not implemented", file=sys.stderr)
        return 1
    if len(manifest.launchers) != 1:
        print("anx run: expected exactly one MAIN/LAUNCHER Activity", file=sys.stderr)
        print(format_metadata(metadata), file=sys.stderr)
        return 1
    if not framework_dex.is_file():
        print(f"anx run: framework DEX not found: {framework_dex}", file=sys.stderr)
        print("Build the reference runtime with: bash scripts/build-demo-apk.sh", file=sys.stderr)
        return 1

    executable = shutil.which(art)
    if executable is None:
        candidate = Path(art).expanduser()
        if candidate.is_file() and os.access(candidate, os.X_OK):
            executable = str(candidate.resolve())
    if executable is None:
        print(f"anx run: ART executable not found: {art}", file=sys.stderr)
        return 1

    data_dir = android_data or Path(os.environ.get(
        "ANDROID_DATA", str(Path.home() / ".local" / "share" / "anx" / "android-data")
    ))
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print(f"anx run: cannot create ANDROID_DATA {data_dir}: {exc}", file=sys.stderr)
        return 1

    class_path = os.pathsep.join((str(framework_dex.resolve()), str(metadata.path)))
    command = [executable, "-cp", class_path,
               "org.anx.launcher.Main", manifest.launcher_activity or ""]
    environment = os.environ.copy()
    environment["ANDROID_DATA"] = str(data_dir.resolve())
    print(f"[anx] ART: {executable}", flush=True)
    print(f"[anx] package: {manifest.package_name}", flush=True)
    print(f"[anx] launcher: {manifest.launcher_activity}", flush=True)
    try:
        return subprocess.run(command, env=environment, check=False).returncode
    except OSError as exc:
        print(f"anx run: failed to start ART: {exc}", file=sys.stderr)
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(prog="anx")
    commands = parser.add_subparsers(dest="command", required=True)
    inspect_parser = commands.add_parser("inspect", help="show APK metadata")
    inspect_parser.add_argument("apk", type=Path)
    run_parser = commands.add_parser("run", help="run an APK's launcher Activity with ART")
    run_parser.add_argument("apk", type=Path)
    run_parser.add_argument("--art", default=os.environ.get("ART_CMD", "dalvikvm64"))
    run_parser.add_argument("--framework-dex", type=Path, default=DEFAULT_FRAMEWORK_DEX)
    run_parser.add_argument("--android-data", type=Path)
    args = parser.parse_args()
    if args.command == "inspect":
        try:
            print(format_metadata(inspect_apk(args.apk)))
            return 0
        except ApkError as exc:
            print(f"anx inspect: {exc}", file=sys.stderr)
            return 1
    return _run(args.apk, args.art, args.framework_dex, args.android_data)


if __name__ == "__main__":
    raise SystemExit(main())
