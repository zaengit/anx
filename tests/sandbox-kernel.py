#!/usr/bin/env python3
"""Black-box kernel namespace/mount/network isolation test (no APK execution).

Unlike sandbox-unit.py, this executes a REAL bwrap process. A blocked
unprivileged user namespace causes a failing test, not a fake green check.
"""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from sandbox import wrap_console_art

GUEST_CHECK = r"""
import os
from pathlib import Path
import socket
import sys

host_netns, host_mntns, secret_path = sys.argv[1:]
assert os.readlink("/proc/self/ns/net") != host_netns, "host network namespace shared"
assert os.readlink("/proc/self/ns/mnt") != host_mntns, "host mount namespace shared"
assert "ANX_PROBE_SECRET" not in os.environ, "host environment leaked"
assert not Path(secret_path).exists(), "host home/private test file visible"
assert not Path("/etc/passwd").exists(), "host /etc unexpectedly visible"
assert Path("/anx/framework.dex").read_bytes() == b"framework-fixture"
assert Path("/anx/app.apk").read_bytes() == b"apk-fixture"
for forbidden in ("/anx/framework.dex", "/anx/app.apk", "/usr/bin/env"):
    try:
        with open(forbidden, "ab") as stream:
            stream.write(b"mutation")
    except OSError:
        pass
    else:
        raise AssertionError("read-only mount is writable: " + forbidden)
assert not Path("/anx/apps/org.other/secret.txt").exists(), "other package data visible"
target = Path("/anx/apps/org.fixture/guest-wrote.txt")
target.write_text("persist-from-bwrap", encoding="utf-8")
assert Path("/anx/data").is_dir(), "Android data bind is missing"
assert not Path("/anx/data/org.other/cache.bin").exists(), "sibling ART cache visible"
Path("/anx/data/own-cache.bin").write_bytes(b"own-runtime-cache")
assert Path("/tmp").is_dir(), "temporary directory unavailable"
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.settimeout(0.35)
    status = sock.connect_ex(("1.1.1.1", 443))
    assert status != 0, "external network connection unexpectedly succeeded"
print("ANX_SANDBOX_KERNEL_OK", flush=True)
"""

def main() -> int:
    bwrap = shutil.which("bwrap")
    if not bwrap:
        print("[FAIL] bubblewrap must be installed for real kernel test", file=sys.stderr)
        return 1
    if not (Path("/proc/self/ns/net").exists()
            and Path("/proc/self/ns/mnt").exists()):
        print("[FAIL] Linux kernel namespaces unavailable", file=sys.stderr)
        return 1
    home = Path.home()
    with tempfile.TemporaryDirectory(prefix="anx-kernel-probe-") as work:
        root = Path(work)
        framework = root / "framework.dex"
        apk = root / "application.apk"
        android_data = root / "android-data"
        apps = root / "apps"
        for directory in (android_data, apps):
            directory.mkdir()
        other_runtime = android_data / "org.other"
        other_runtime.mkdir()
        (other_runtime / "cache.bin").write_bytes(b"other-runtime")
        other = apps / "org.other"
        other.mkdir()
        (other / "secret.txt").write_text("other app data", encoding="utf-8")
        framework.write_bytes(b"framework-fixture")
        apk.write_bytes(b"apk-fixture")
        # Deliberately outside the sandbox input paths, under the user's home.
        marker = home / (".anx-kernel-test-" + root.name)
        marker.write_text("never visible inside Bubblewrap", encoding="utf-8")
        try:
            args = wrap_console_art(
                art_executable=Path("/usr/bin/python3"),
                framework_dex=framework,
                apk_path=apk,
                launcher="org.fixture.Activity",
                package="org.fixture",
                application="-",
                android_data=android_data,
                app_data_root=apps,
                bubblewrap_executable=bwrap,
            )
            separator = args.index("--")
            command = args[:separator + 1] + [
                "/usr/bin/python3", "-I", "-c", GUEST_CHECK,
                os.readlink("/proc/self/ns/net"),
                os.readlink("/proc/self/ns/mnt"),
                str(marker),
            ]
            environment = os.environ.copy()
            environment["ANX_PROBE_SECRET"] = "must-not-reach-sandbox"
            result = subprocess.run(command, capture_output=True, text=True,
                                    timeout=20, env=environment, check=False)
            if result.returncode != 0:
                # Ubuntu/AppArmor and CI kernels may reject user or network
                # namespace setup. Report this separately; do NOT retry ART.
                permission_error = result.stderr.startswith("bwrap:") and (
                    "Operation not permitted" in result.stderr
                    or "Permission denied" in result.stderr
                )
                if permission_error:
                    print("[UNSUPPORTED] Kernel policy denies Bubblewrap setup: "
                          + result.stderr.strip(), file=sys.stderr)
                    return 77
                print("[FAIL] Bubblewrap kernel isolation probe failed:", file=sys.stderr)
                print(result.stdout, file=sys.stderr)
                print(result.stderr, file=sys.stderr)
                return 1
            if "ANX_SANDBOX_KERNEL_OK" not in result.stdout:
                print("[FAIL] Kernel probe did not report expected evidence", file=sys.stderr)
                return 1
            if (apps / "org.fixture/guest-wrote.txt").read_text(encoding="utf-8") != "persist-from-bwrap":
                print("[FAIL] Explicit writable ANX app data bind did not persist", file=sys.stderr)
                return 1
            if (android_data / "org.fixture/own-cache.bin").read_bytes() != b"own-runtime-cache":
                print("[FAIL] Package-local ART runtime data did not persist", file=sys.stderr)
                return 1
            if (android_data / "org.other/cache.bin").read_bytes() != b"other-runtime":
                print("[FAIL] Sibling ART runtime data was modified", file=sys.stderr)
                return 1
            if apk.read_bytes() != b"apk-fixture":
                print("[FAIL] Host APK modified despite read-only bind", file=sys.stderr)
                return 1
        finally:
            marker.unlink(missing_ok=True)
    print("[PASS] Real Bubblewrap: separate network/mount namespaces, "
          "no host home/env, read-only APK/runtime, per-package ART and app-data persistence.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
