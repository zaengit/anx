#!/usr/bin/env python3
"""Optional REAL kernel cgroup v2 probe. Requires an explicitly delegated parent.

Usage: python3 tests/cgroup-kernel.py /sys/fs/cgroup/<delegated-parent>
No sudo/setup fallback is attempted. This test does not execute an APK.
"""
from __future__ import annotations

from pathlib import Path
import os
import re
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from cgroup_v2 import (CgroupError, MEMORY_MAX, PIDS_MAX, delegated_cgroup,
                       join_cgroup)
from sandbox import apply_sandbox_resource_limits


GUEST = """
from pathlib import Path
import os
import sys
leaf = Path(sys.argv[1])
assert Path('/proc/self/cgroup').read_text().strip().endswith('/' + leaf.name), (
    'child did not join expected kernel cgroup'
)
assert (leaf / 'memory.max').read_text().strip() == str(512 * 1024 * 1024)
assert (leaf / 'pids.max').read_text().strip() == '64'
print('ANX_CGROUP_KERNEL_OK', flush=True)
# A detached descendant must be terminated when the ANX leaf is cleaned up.
pid = os.fork()
if pid == 0:
    os.setsid()
    # Avoid holding the probe's captured stdout/stderr pipes open.
    os.close(1)
    os.close(2)
    import time
    time.sleep(60)
    os._exit(0)
print('DESCENDANT=' + str(pid), flush=True)
"""


def main() -> int:
    if len(sys.argv) != 2:
        print("[UNSUPPORTED] Specify a pre-delegated writable cgroup v2 parent; "
              "no automatic privileged setup is performed.", file=sys.stderr)
        return 77

    parent = Path(sys.argv[1])
    try:
        with delegated_cgroup(parent) as leaf:
            def setup():
                apply_sandbox_resource_limits()
                join_cgroup(leaf)

            probe = subprocess.run(
                [sys.executable, "-c", GUEST, str(leaf)],
                preexec_fn=setup, capture_output=True, text=True,
                check=False, timeout=20,
            )
            if probe.returncode != 0 or "ANX_CGROUP_KERNEL_OK" not in probe.stdout:
                raise AssertionError(
                    "kernel child failed to verify cgroup membership/limits: "
                    + probe.stdout + " " + probe.stderr
                )
            match = re.search(r"^DESCENDANT=([0-9]+)$", probe.stdout, re.MULTILINE)
            if match is None:
                raise AssertionError("detached descendant process was not created")
            descendant_pid = int(match.group(1))
            descendant_proc = Path(f"/proc/{descendant_pid}")
            member = (descendant_proc / "cgroup").read_text(encoding="ascii")
            if not any(line.endswith("/" + leaf.name) for line in member.splitlines()):
                raise AssertionError("detached descendant escaped the target cgroup")
            state = (descendant_proc / "status").read_text(encoding="ascii")
            if any(line.startswith("State:") and "Z (zombie)" in line
                   for line in state.splitlines()):
                raise AssertionError("detached descendant exited before cleanup")
            print(probe.stdout.strip())
        if leaf.exists():
            raise AssertionError("private cgroup persisted after cleanup")
        descendant_status = Path(f"/proc/{descendant_pid}/status")
        if descendant_status.exists():
            state = descendant_status.read_text(encoding="ascii")
            if not any(line.startswith("State:") and line.split()[1] == "Z"
                       for line in state.splitlines()):
                raise AssertionError("detached descendant still running after cgroup.kill")
    except (OSError, subprocess.SubprocessError, CgroupError, AssertionError) as exc:
        print(f"[FAIL] Real cgroup kernel probe: {exc}", file=sys.stderr)
        return 1

    print("[PASS] Real cgroup: child membership, limit files, descendant "
          "reaping and private leaf removal.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
