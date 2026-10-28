#!/usr/bin/env python3
"""Real kernel cgroup v2 probe inside a disposable systemd delegated service.

CI-only privileged setup: the caller MUST be launched via systemd-run with
Delegate=yes under an anx-cgroup-probe-*.service transient unit. This helper
must never edit the host's root, user, or pre-existing service cgroups.
A lack of delegation exits 77 (NOT TESTED); failed enforcement exits nonzero.
"""
from __future__ import annotations

import os
from pathlib import Path
import re
import subprocess
import sys

CGROUP_ROOT = Path("/sys/fs/cgroup")
PROBE = Path(__file__).resolve().with_name("cgroup-kernel.py")
UNSUPPORTED = 77


def unsupported(reason: str) -> int:
    print(f"[UNSUPPORTED] Real delegated cgroup kernel probe NOT TESTED: {reason}",
          file=sys.stderr)
    return UNSUPPORTED


def main() -> int:
    if os.geteuid() != 0:
        return unsupported("systemd transient probe requires privileged CI setup")
    try:
        if not (CGROUP_ROOT / "cgroup.controllers").is_file():
            return unsupported("unified cgroup v2 hierarchy unavailable")
        memberships = Path("/proc/self/cgroup").read_text(encoding="ascii").splitlines()
        if len(memberships) != 1 or not memberships[0].startswith("0::/"):
            return unsupported("no single unified cgroup v2 membership")
        relative = Path(memberships[0][4:])
        if (not re.fullmatch(r"anx-cgroup-probe-[A-Za-z0-9-]+\.service", relative.name)
                or ".." in relative.parts):
            return unsupported("refusing to alter cgroup outside a fresh ANX systemd unit")
        service = (CGROUP_ROOT / relative).resolve(strict=True)
        if service == CGROUP_ROOT.resolve() or not service.is_relative_to(CGROUP_ROOT):
            return unsupported("service cgroup escaped unified hierarchy")
        # A systemd transient service should contain only the test driver.
        # Enabling domain controllers is prohibited while it contains processes.
        members = (service / "cgroup.procs").read_text(encoding="ascii").split()
        if members != [str(os.getpid())]:
            return unsupported("transient service unexpectedly contains other processes")
        controllers = set((service / "cgroup.controllers").read_text(encoding="ascii").split())
        if not {"memory", "pids"}.issubset(controllers):
            return unsupported("systemd did not delegate both memory and pids controllers")

        # Move only ourselves to our own sibling-manager leaf so we can enable
        # domain controllers on the now-empty transient service's subtree.
        manager = service / "anx-ci-manager"
        manager.mkdir(mode=0o700)
        (manager / "cgroup.procs").write_text("0", encoding="ascii")
        (service / "cgroup.subtree_control").write_text("+memory +pids", encoding="ascii")
        enabled = set((service / "cgroup.subtree_control").read_text(
            encoding="ascii").split())
        if not {"memory", "pids"}.issubset(enabled):
            return unsupported("transient service did not enable memory and pids subtree")

        print("[REAL KERNEL] Testing delegated memory.max, pids.max, "
              "and detached descendants inside disposable systemd unit",
              flush=True)
        result = subprocess.run(
            [sys.executable, str(PROBE), str(service)], check=False, timeout=120,
        )
        if result.returncode == 77:
            return unsupported("inner kernel probe reported unsupported delegation")
        return result.returncode
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        print(f"[FAIL] Transient cgroup setup/kernel probe failed: {exc}",
              file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
