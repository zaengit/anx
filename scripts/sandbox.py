"""Fail-closed *experimental* Bubblewrap console profile for ANX.

Do not treat this as a complete or audited security sandbox. It restricts
paths/network in a mount/user/pid/net namespace when supported by the host.
"""
from __future__ import annotations

from pathlib import Path
import os
import re
import shutil


class SandboxError(ValueError):
    """The sandbox profile cannot enforce its expected preconditions."""


def wrap_console_art(
    *,
    art_executable: Path,
    framework_dex: Path,
    apk_path: Path,
    launcher: str,
    package: str,
    application: str,
    android_data: Path,
    app_data_root: Path,
    native_directory: Path | None = None,
    secondary_dex_paths: tuple[Path, ...] = (),
    bubblewrap_executable: str | None = None,
) -> list[str]:
    bwrap = (shutil.which("bwrap") if bubblewrap_executable is None
             else bubblewrap_executable)
    if not bwrap:
        raise SandboxError("Bubblewrap (bwrap) is required for --experimental-sandbox")
    art = art_executable.resolve()
    if not (art.is_relative_to("/usr") or art.is_relative_to("/bin")):
        raise SandboxError(
            "experimental sandbox supports host ART installed under /usr or /bin only"
        )
    locations = [framework_dex, apk_path, android_data, app_data_root]
    if native_directory:
        locations.append(native_directory)
    locations.extend(secondary_dex_paths)
    if not all(path.exists() for path in locations):
        raise SandboxError("sandbox input or persistent data directory does not exist")
    if not android_data.is_dir() or not app_data_root.is_dir():
        raise SandboxError("sandbox writable directories must be directories")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+", package):
        raise SandboxError("invalid package identifier for sandbox directory")
    # Never expose ALL other packages' data to a sandboxed application.
    package_dir = app_data_root / package
    if package_dir.is_symlink():
        raise SandboxError("per-package data directory cannot be a symlink")
    package_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    if not package_dir.is_dir() or package_dir.resolve().parent != app_data_root.resolve():
        raise SandboxError("per-package data directory escaped its root")
    # ART's runtime cache is also a per-package writable mount. Sharing a
    # global ANDROID_DATA directory would expose other apps' runtime caches.
    runtime_dir = android_data / package
    if runtime_dir.is_symlink():
        raise SandboxError("per-package ART cache directory cannot be a symlink")
    runtime_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    if not runtime_dir.is_dir() or runtime_dir.resolve().parent != android_data.resolve():
        raise SandboxError("per-package ART cache directory escaped its root")
    if native_directory and not native_directory.is_dir():
        raise SandboxError("sandbox native library directory is missing")
    if len(secondary_dex_paths) > 15:
        raise SandboxError("too many secondary DEX paths")
    for i, secondary in enumerate(secondary_dex_paths, start=2):
        if secondary.name != f"classes{i}.dex" or not secondary.is_file() or secondary.is_symlink():
            raise SandboxError("invalid secondary DEX path for sandbox")
    if not framework_dex.is_file() or not apk_path.is_file():
        raise SandboxError("sandbox APK and framework must be regular files")

    # No bind of /home, ~/.ssh, credentials, /etc, the host /tmp, or host /run.
    # The only write-capable host paths are dedicated ANX data directories.
    args = [
        bwrap,
        "--unshare-all", "--die-with-parent", "--new-session",
        "--clearenv", "--setenv", "PATH", "/usr/bin:/bin",
        "--setenv", "HOME", "/tmp",
        "--setenv", "TMPDIR", "/tmp",
        "--setenv", "ANDROID_DATA", "/anx/data",
        "--setenv", "ANX_APP_DATA_HOME", "/anx/apps",
        "--setenv", "ANX_BACKEND", "console",
        "--setenv", "LANG", "C.UTF-8",
        "--ro-bind", "/usr", "/usr",
        "--ro-bind-try", "/lib", "/lib",
        "--ro-bind-try", "/lib64", "/lib64",
        "--ro-bind-try", "/bin", "/bin",
        "--ro-bind-try", "/sbin", "/sbin",
        "--dir", "/anx", "--dir", "/anx/apps",
        "--dir", "/home", "--dir", "/root",
        "--tmpfs", "/tmp",
        "--proc", "/proc", "--dev", "/dev",
        "--ro-bind", str(framework_dex.resolve()), "/anx/framework.dex",
        "--ro-bind", str(apk_path.resolve()), "/anx/app.apk",
        "--bind", str(runtime_dir.resolve()), "/anx/data",
        "--bind", str(package_dir.resolve()), "/anx/apps/" + package,
    ]
    classpath = "/anx/framework.dex:/anx/app.apk"
    if secondary_dex_paths:
        args += ["--dir", "/anx/dex"]
        for secondary in secondary_dex_paths:
            guest = "/anx/dex/" + secondary.name
            args += ["--ro-bind", str(secondary.resolve()), guest]
            classpath += ":" + guest
    java_args = [str(art), "-cp", classpath, "org.anx.launcher.Main",
                 launcher, package, application, "/anx/app.apk"]
    if native_directory:
        args += ["--ro-bind", str(native_directory.resolve()), "/anx/native"]
        java_args.insert(1, "-Djava.library.path=/anx/native")
    args += ["--chdir", "/anx", "--"] + java_args
    return args
