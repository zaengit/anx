#!/usr/bin/env python3
"""ANX command line for APK inspection and the current ART demo subset."""
import argparse
import contextlib
import tempfile
import os
from pathlib import Path
import shutil
import subprocess
import sys

from apk_inspector import ApkError, format_metadata, inspect_apk
from native_libraries import NativeLibraryError, extract_native_libraries


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_FRAMEWORK_DEX = ROOT / "build" / "framework" / "classes.dex"


def _run(apk: Path, art: str, framework_dex: Path, android_data: Path | None,
         backend: str, wayland_binary: str | None, unsafe_host_execution: bool) -> int:
    try:
        metadata = inspect_apk(apk)
    except ApkError as exc:
        print(f"anx run: {exc}", file=sys.stderr)
        return 1

    if not unsafe_host_execution:
        print(
            "anx run: refusing to execute APK code without process isolation. "
            "There is no sandbox; APK code can access host files and network. "
            "Pass --unsafe-host-execution only for APKs you trust.",
            file=sys.stderr,
        )
        return 2

    manifest = metadata.manifest
    if not metadata.dex_files:
        print("anx run: APK contains no classes.dex", file=sys.stderr)
        return 1
    if len(metadata.dex_files) > 1:
        print("anx run: multidex APKs are detected but not loadable yet", file=sys.stderr)
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

    native = wayland_binary or os.environ.get("ANX_WAYLAND_BINARY") or str(
        ROOT / "build" / "native" / "anx-wayland"
    )
    resolved_native = shutil.which(native)
    if resolved_native is None:
        native_path = Path(native).expanduser()
        if native_path.is_file() and os.access(native_path, os.X_OK):
            resolved_native = str(native_path.resolve())
    selected_backend = backend
    if selected_backend == "auto":
        selected_backend = ("wayland" if os.environ.get("WAYLAND_DISPLAY")
                            and resolved_native else "console")
        if selected_backend == "console":
            print("[anx] no compiled Wayland backend/session; using console backend", flush=True)
    if selected_backend == "wayland" and not resolved_native:
        print("anx run: Wayland executable missing. Run: bash scripts/build-wayland.sh",
              file=sys.stderr)
        return 1
    class_path = os.pathsep.join((str(framework_dex.resolve()), str(metadata.path)))
    command = [executable, "-cp", class_path,
               "org.anx.launcher.Main", manifest.launcher_activity or "",
               manifest.package_name, manifest.application_name or "-",
               str(metadata.path)]
    environment = os.environ.copy()
    environment["ANDROID_DATA"] = str(data_dir.resolve())
    app_data_root = Path(os.environ.get(
        "ANX_APP_DATA_HOME", str(Path.home() / ".local" / "share" / "anx" / "apps")
    )).expanduser()
    try:
        app_data_root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print(f"anx run: cannot create app data directory: {exc}", file=sys.stderr)
        return 1
    environment["ANX_APP_DATA_HOME"] = str(app_data_root.resolve())
    environment["ANX_BACKEND"] = selected_backend
    if selected_backend == "wayland":
        environment["ANX_WAYLAND_BINARY"] = resolved_native
    print(f"[anx] ART: {executable}", flush=True)
    print(f"[anx] package: {manifest.package_name}", flush=True)
    print(f"[anx] launcher: {manifest.launcher_activity}", flush=True)
    try:
        # Keep the checked, isolated extraction directory alive while ART runs.
        # This is not an OS sandbox; the user already opted into host execution.
        directory = (tempfile.TemporaryDirectory(prefix="anx-native-")
                     if metadata.native_abis else contextlib.nullcontext(None))
        with directory as extracted:
            if extracted is not None:
                abi, names = extract_native_libraries(metadata, Path(extracted))
                command.insert(1, "-Djava.library.path=" + extracted)
                environment["ANX_NATIVE_LIBRARY_DIR"] = extracted
                print(f"[anx] native ABI: {abi} ({len(names)} libraries)", flush=True)
            return subprocess.run(command, env=environment, check=False).returncode
    except (OSError, NativeLibraryError) as exc:
        print(f"anx run: failed to load host-native libraries: {exc}", file=sys.stderr)
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
    run_parser.add_argument("--backend", choices=("auto", "console", "wayland"),
                            default="auto")
    run_parser.add_argument(
        "--unsafe-host-execution",
        action="store_true",
        help="explicitly accept unrestricted host access by trusted APK code",
    )
    run_parser.add_argument("--wayland-binary",
                            help="path to compiled GTK4 Wayland host executable")
    argv = sys.argv[1:]
    if argv and not argv[0].startswith("-") and argv[0] not in ("inspect", "run"):
        argv.insert(0, "run")
    args = parser.parse_args(argv)
    if args.command == "inspect":
        try:
            print(format_metadata(inspect_apk(args.apk)))
            return 0
        except ApkError as exc:
            print(f"anx inspect: {exc}", file=sys.stderr)
            return 1
    return _run(args.apk, args.art, args.framework_dex, args.android_data,
                args.backend, args.wayland_binary, args.unsafe_host_execution)


if __name__ == "__main__":
    raise SystemExit(main())
