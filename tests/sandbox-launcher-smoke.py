#!/usr/bin/env python3
"""End-to-end ANX launcher regression using a fake bwrap (not kernel isolation).

Verify that a host process's sensitive environment, open file descriptors, and
stdin do not reach the Bubblewrap helper launched by the actual ANX CLI.
"""
from __future__ import annotations

import fcntl
import os
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    apk = ROOT / "build" / "demo.apk"
    framework = ROOT / "build" / "framework" / "classes.dex"
    if not apk.is_file() or not framework.is_file():
        print("[FAIL] build/demo.apk and framework DEX are required", file=sys.stderr)
        return 1

    with tempfile.TemporaryDirectory(prefix="anx-fd-probe-") as temporary:
        root = Path(temporary)
        bin_dir = root / "bin"
        bin_dir.mkdir()
        marker = root / "sensitive-host-file"
        marker.write_text("must-not-reach-guest", encoding="utf-8")
        source_fd = os.open(marker, os.O_RDONLY)
        try:
            inherited_fd = fcntl.fcntl(source_fd, fcntl.F_DUPFD, 55)
        finally:
            os.close(source_fd)
        os.set_inheritable(inherited_fd, True)
        try:
            helper = bin_dir / "bwrap"
            helper.write_text(
                "#!/bin/sh\n"
                "if [ -n \"$HOST_ANX_SECRET\" ]; then exit 91; fi\n"
                "if [ -n \"$ANX_APP_DATA_HOME\" ]; then exit 94; fi\n"
                "if [ -n \"$ANDROID_DATA\" ]; then exit 95; fi\n"
                f"if [ -e /proc/self/fd/{inherited_fd} ]; then exit 92; fi\n"
                "if [ \"$(readlink /proc/self/fd/0)\" != /dev/null ]; then exit 93; fi\n"
                "exit 42\n",
                encoding="utf-8",
            )
            helper.chmod(0o700)
            environment = os.environ.copy()
            environment.update({
                "PATH": str(bin_dir) + os.pathsep + environment.get("PATH", ""),
                "HOST_ANX_SECRET": "not-for-bwrap",
                "ANX_APP_DATA_HOME": str(root / "apps"),
                "ANDROID_DATA": str(root / "android-data"),
            })
            with marker.open("rb") as host_stdin:
                child = subprocess.run(
                    [sys.executable, str(ROOT / "scripts" / "anx.py"),
                     "run", str(apk), "--art", "/usr/bin/true",
                     "--framework-dex", str(framework),
                     "--backend", "console", "--unsafe-host-execution",
                     "--experimental-sandbox"],
                    env=environment,
                    stdin=host_stdin,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=25,
                    pass_fds=(inherited_fd,),
                    check=False,
                )
        finally:
            os.close(inherited_fd)

        if child.returncode != 42:
            print(f"[FAIL] sandbox helper returned {child.returncode} (expected 42)",
                  file=sys.stderr)
            print(child.stdout, file=sys.stderr)
            print(child.stderr, file=sys.stderr)
            return 1
        if "experimental console isolation via Bubblewrap" not in child.stdout:
            print("[FAIL] CLI did not launch the experimental helper", file=sys.stderr)
            return 1
    print("[PASS] Helper gets minimal environment, /dev/null stdin, "
          "and no inherited secret file descriptor.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
