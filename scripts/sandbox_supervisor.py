"""Conservative process supervision for ANX's experimental console sandbox.

The launcher only owns the direct Bubblewrap helper. A delegated cgroup is
required to reliably reap unrelated or detached descendant processes.
"""
from __future__ import annotations

from contextlib import contextmanager
import signal
import subprocess
from typing import Callable, Iterator


class SandboxSignals:
    """Turn SIGTERM into unwinding so cgroup and temporary-file cleanup runs.

    SIGINT already raises KeyboardInterrupt in the ordinary Python CLI.
    Must only be installed in the main thread; this CLI is single-threaded.
    """

    def __init__(self) -> None:
        self.terminated = False

    @contextmanager
    def install(self) -> Iterator[None]:
        previous = signal.getsignal(signal.SIGTERM)

        def interrupted(signum: int, _frame: object) -> None:
            self.terminated = True
            # Ignore repeated SIGTERM while ExitStack kills cgroup descendants.
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
            raise KeyboardInterrupt

        signal.signal(signal.SIGTERM, interrupted)
        try:
            yield
        finally:
            signal.signal(signal.SIGTERM, previous)

    @property
    def exit_code(self) -> int:
        return 143 if self.terminated else 130


def run_sandbox_helper(
    command: list[str],
    *,
    environment: dict[str, str],
    timeout_seconds: int,
    child_setup: Callable[[], None],
) -> tuple[int, bool]:
    """Reap the direct helper on timeout/SIGINT/SIGTERM, with no fallback.

    Return (process exit status, timed_out). The caller's ExitStack (which
    may manage a delegated cgroup) must remain active throughout this call.
    """
    with subprocess.Popen(
        command, env=environment, close_fds=True,
        stdin=subprocess.DEVNULL, preexec_fn=child_setup,
    ) as child:
        try:
            return child.wait(timeout=timeout_seconds), False
        except (subprocess.TimeoutExpired, KeyboardInterrupt) as exc:
            try:
                child.kill()
            except ProcessLookupError:
                pass  # A simultaneous normal exit is not a security failure.
            child.wait()
            if isinstance(exc, subprocess.TimeoutExpired):
                return 124, True
            raise
