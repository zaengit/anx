#!/usr/bin/env python3
"""Optional REAL kernel cgroup v2 probe. Requires an explicitly delegated parent.

Usage: python3 tests/cgroup-kernel.py /sys/fs/cgroup/<delegated-parent>
No sudo/setup fallback is attempted. This test does not execute an APK.
"""
from __future__ import annotations

from pathlib import Path
import os
import re
import signal
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


# The stress tests deliberately LOWER the limits in their *own*, separate
# short-lived leaf groups. No controls outside ANX's private leaves are changed.
PIDS_STRESS_MAX = 8
MEMORY_STRESS_MAX = 64 * 1024 * 1024

PIDS_GUEST = r"""
import os
from pathlib import Path
import sys
import threading

leaf = Path(sys.argv[1])
assert Path("/proc/self/cgroup").read_text().strip().endswith("/" + leaf.name)
gate = threading.Event()
threads = []
blocked = False
try:
    for _ in range(16):
        thread = threading.Thread(target=gate.wait)
        try:
            thread.start()
        except RuntimeError as exc:
            if "can't start new thread" not in str(exc):
                raise
            blocked = True
            break
        threads.append(thread)
finally:
    gate.set()
    for thread in threads:
        thread.join()
assert blocked, "pids.max did not reject excess threads"
print("ANX_PIDS_DENIED", flush=True)
"""

MEMORY_GUEST = r"""
from pathlib import Path
import sys

leaf = Path(sys.argv[1])
assert Path("/proc/self/cgroup").read_text().strip().endswith("/" + leaf.name)
print("ANX_MEMORY_STARTED", flush=True)
# 128 MiB resident demand in a *private leaf capped at 64 MiB*. Failure
# to OOM-kill this process is a failed isolation check, never success.
data = bytearray(128 * 1024 * 1024)
for index in range(0, len(data), 4096):
    data[index] = 1
print("ANX_MEMORY_UNBOUNDED", flush=True)
"""


def _event_count(path: Path, counter: str) -> int:
    for line in path.read_text(encoding="ascii").splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[0] == counter:
            return int(parts[1])
    raise AssertionError(f"missing cgroup event counter {counter} in {path}")


def _run_in_leaf(leaf: Path, script: str, timeout: int = 15) -> subprocess.CompletedProcess:
    def setup() -> None:
        apply_sandbox_resource_limits()
        join_cgroup(leaf)

    return subprocess.run(
        [sys.executable, "-c", script, str(leaf)],
        preexec_fn=setup, capture_output=True, text=True,
        check=False, timeout=timeout,
    )


def verify_pids_enforcement(leaf: Path) -> None:
    limit = leaf / "pids.max"
    limit.write_text(str(PIDS_STRESS_MAX), encoding="ascii")
    if limit.read_text(encoding="ascii").strip() != str(PIDS_STRESS_MAX):
        raise AssertionError("kernel did not accept stress-test pids.max")
    events = leaf / "pids.events"
    before = _event_count(events, "max")
    child = _run_in_leaf(leaf, PIDS_GUEST)
    after = _event_count(events, "max")
    if (child.returncode != 0 or "ANX_PIDS_DENIED" not in child.stdout
            or after <= before):
        raise AssertionError(
            f"kernel pids.max not confirmed (code={child.returncode}, "
            f"events {before}->{after}): {child.stdout} {child.stderr}"
        )


def verify_memory_enforcement(leaf: Path) -> None:
    # A valid host may swap cold, one-time-written pages. Such a host can
    # legitimately finish a 128 MiB allocation under memory.max=64 MiB
    # without OOM. Remove swap only for THIS disposable stress-test leaf,
    # so the test exercises physical memory enforcement deterministically.
    # The actual ANX runtime is intentionally NOT changed by this probe.
    swap = leaf / "memory.swap.max"
    if not swap.is_file():
        raise AssertionError("kernel lacks memory.swap.max; cannot assert a no-swap OOM probe")
    swap.write_text("0", encoding="ascii")
    if swap.read_text(encoding="ascii").strip() != "0":
        raise AssertionError("kernel did not disable swap in private OOM test leaf")

    limit = leaf / "memory.max"
    limit.write_text(str(MEMORY_STRESS_MAX), encoding="ascii")
    if limit.read_text(encoding="ascii").strip() != str(MEMORY_STRESS_MAX):
        raise AssertionError("kernel did not accept stress-test memory.max")
    events = leaf / "memory.events"
    before = _event_count(events, "oom_kill")
    child = _run_in_leaf(leaf, MEMORY_GUEST)
    after = _event_count(events, "oom_kill")
    if (child.returncode != -signal.SIGKILL
            or "ANX_MEMORY_STARTED" not in child.stdout
            or after <= before):
        current = (leaf / "memory.current").read_text(encoding="ascii").strip()
        swap_current = (leaf / "memory.swap.current").read_text(
            encoding="ascii").strip() if (leaf / "memory.swap.current").is_file() else "unknown"
        raise AssertionError(
            f"kernel memory.max OOM kill not confirmed (code={child.returncode}, "
            f"events {before}->{after}, memory.current={current}, "
            f"swap.current={swap_current}): {child.stdout} {child.stderr}"
        )



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
        # Independent real-kernel enforcement checks. Each creates a new
        # limited leaf; failed controller enforcement is a failing probe.
        with delegated_cgroup(parent) as pid_leaf:
            verify_pids_enforcement(pid_leaf)
        print("ANX_PIDS_KERNEL_OK", flush=True)
        with delegated_cgroup(parent) as memory_leaf:
            verify_memory_enforcement(memory_leaf)
        print("ANX_MEMORY_KERNEL_OK", flush=True)
    except (OSError, ValueError, subprocess.SubprocessError, CgroupError,
            AssertionError) as exc:
        print(f"[FAIL] Real cgroup kernel probe: {exc}", file=sys.stderr)
        return 1

    print("[PASS] Real cgroup: membership, detached-child teardown, "
          "kernel-enforced pids.max and memory.max.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
