"""Opt-in Linux cgroup v2 resource gate for ANX's experimental console sandbox.

This requires a *pre-delegated* cgroup parent. ANX never enables controllers
on a host hierarchy, never escalates privileges, and never silently falls back
to unrestricted execution. Not a security-certified Android process sandbox.
"""
from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path
import secrets
import time
from typing import Iterator

CGROUP_ROOT = Path("/sys/fs/cgroup")
MEMORY_MAX = 512 * 1024 * 1024
PIDS_MAX = 64


class CgroupError(ValueError):
    """A cgroup budget could not be provisioned or cleaned up safely."""


def join_cgroup(path: Path) -> None:
    """Join the private cgroup in the child before exec (write 0 = self).

    This must run only in ANX's single-threaded preexec child. A write failure
    aborts subprocess startup; no ART or Bubblewrap execution is permitted.
    """
    fd = os.open(path / "cgroup.procs", os.O_WRONLY | os.O_CLOEXEC)
    try:
        if os.write(fd, b"0") != 1:
            raise OSError("short cgroup.procs write")
    finally:
        os.close(fd)


def _populated(path: Path) -> bool:
    events = (path / "cgroup.events").read_text(encoding="ascii").splitlines()
    for line in events:
        if line.startswith("populated "):
            return line.split() == ["populated", "1"]
    raise CgroupError("cgroup.events has no populated status")


def _validate_parent(parent: Path, root: Path) -> Path:
    root = root.resolve(strict=True)
    parent = parent.expanduser().resolve(strict=True)
    if not parent.is_relative_to(root) or parent == root:
        raise CgroupError("parent must be a delegated subdirectory under /sys/fs/cgroup")
    if not (parent / "cgroup.procs").is_file():
        raise CgroupError("not a usable cgroup v2 parent")
    controllers = set((parent / "cgroup.controllers").read_text(encoding="ascii").split())
    enabled = set((parent / "cgroup.subtree_control").read_text(encoding="ascii").split())
    if not {"memory", "pids"}.issubset(controllers & enabled):
        raise CgroupError("cgroup v2 memory and pids controllers must be delegated and enabled")
    return parent


@contextmanager
def delegated_cgroup(parent: Path, *, root: Path = CGROUP_ROOT) -> Iterator[Path]:
    """Provision a fresh leaf; forcibly kill descendants and remove it on exit.

    The parent is intentionally caller-provided, but MUST already be delegated
    with memory and pids enabled. Ownership/permissions are kernel-enforced.
    An unavailable controller or cleanup failure is fatal, not a fallback.
    """
    try:
        parent = _validate_parent(parent, root)
        leaf = parent / ("anx-" + secrets.token_hex(12))
        os.mkdir(leaf, 0o700)
    except (OSError, CgroupError) as exc:
        raise CgroupError(f"cannot allocate delegated cgroup: {exc}") from exc

    try:
        for name, ceiling in (("memory.max", MEMORY_MAX), ("pids.max", PIDS_MAX)):
            control = leaf / name
            control.write_text(str(ceiling), encoding="ascii")
            actual = control.read_text(encoding="ascii").strip()
            if actual != str(ceiling):
                raise CgroupError(f"cgroup did not enforce {name}={ceiling}: {actual!r}")
        if not (leaf / "cgroup.kill").is_file():
            raise CgroupError("cgroup.kill unavailable; cannot reliably reap descendants")
        if not (leaf / "cgroup.procs").is_file() or not (leaf / "cgroup.events").is_file():
            raise CgroupError("cgroup process or status control unavailable")
        yield leaf
    finally:
        # cgroup.kill covers surviving descendants after Bubblewrap/ART exits.
        # Do not use a recursive filesystem delete on cgroup virtual files.
        try:
            if (leaf / "cgroup.kill").is_file():
                (leaf / "cgroup.kill").write_text("1", encoding="ascii")
            if (leaf / "cgroup.events").is_file():
                deadline = time.monotonic() + 4
                while _populated(leaf):
                    if time.monotonic() >= deadline:
                        raise CgroupError("cgroup still populated after cgroup.kill")
                    time.sleep(0.05)
            os.rmdir(leaf)
        except (OSError, CgroupError) as exc:
            raise CgroupError(f"cannot clean up delegated cgroup {leaf}: {exc}") from exc
