#!/usr/bin/env python3
"""Fake-kernel negatives for the optional ACTIVE cgroup v2 enforcement probe.

Do not confuse these mocked event-file tests with a genuine kernel result.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
import signal
import subprocess
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location(
    "anx_cgroup_kernel_probe", ROOT / "tests" / "cgroup-kernel.py"
)
assert spec is not None and spec.loader is not None
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class ProbeValidationTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.leaf = Path(self.temp.name)
        for name in ("pids.max", "memory.max", "memory.swap.max",
                     "memory.current", "memory.swap.current"):
            (self.leaf / name).write_text("0", encoding="ascii")
        (self.leaf / "pids.events").write_text("max 0\n", encoding="ascii")
        (self.leaf / "memory.events").write_text(
            "low 0\nhigh 0\nmax 0\noom 0\noom_kill 0\n", encoding="ascii"
        )

    def test_rejects_missing_event_counter(self):
        with self.assertRaisesRegex(AssertionError, "missing cgroup event counter"):
            probe._event_count(self.leaf / "pids.events", "oom_kill")

    def test_pids_enforced_requires_kernel_event_and_guest_proof(self):
        def guest(_leaf, _script):
            (self.leaf / "pids.events").write_text("max 1\n", encoding="ascii")
            return subprocess.CompletedProcess([], 0, "ANX_PIDS_DENIED\n", "")
        with mock.patch.object(probe, "_run_in_leaf", side_effect=guest):
            probe.verify_pids_enforcement(self.leaf)
        self.assertEqual((self.leaf / "pids.max").read_text(), "8")

    def test_pids_false_positive_rejected_without_event(self):
        fake = subprocess.CompletedProcess([], 0, "ANX_PIDS_DENIED\n", "")
        with mock.patch.object(probe, "_run_in_leaf", return_value=fake):
            with self.assertRaisesRegex(AssertionError, "kernel pids.max not confirmed"):
                probe.verify_pids_enforcement(self.leaf)

    def test_pids_false_positive_rejected_without_guest_marker(self):
        def guest(_leaf, _script):
            (self.leaf / "pids.events").write_text("max 1\n", encoding="ascii")
            return subprocess.CompletedProcess([], 0, "not blocked", "")
        with mock.patch.object(probe, "_run_in_leaf", side_effect=guest):
            with self.assertRaisesRegex(AssertionError, "kernel pids.max not confirmed"):
                probe.verify_pids_enforcement(self.leaf)

    def test_memory_enforced_requires_sigkill_and_kernel_oom_event(self):
        def guest(_leaf, _script):
            (self.leaf / "memory.events").write_text("oom_kill 1\n", encoding="ascii")
            return subprocess.CompletedProcess(
                [], -signal.SIGKILL, "ANX_MEMORY_STARTED\n", ""
            )
        with mock.patch.object(probe, "_run_in_leaf", side_effect=guest):
            probe.verify_memory_enforcement(self.leaf)
        self.assertEqual(
            (self.leaf / "memory.max").read_text(), str(64 * 1024 * 1024)
        )
        self.assertEqual((self.leaf / "memory.swap.max").read_text(), "0",
                         "OOM probe must disallow swap only in its test leaf")

    def test_memory_probe_rejects_missing_swap_controller(self):
        (self.leaf / "memory.swap.max").unlink()
        with self.assertRaisesRegex(AssertionError, "lacks memory.swap.max"):
            probe.verify_memory_enforcement(self.leaf)

    def test_memory_false_positive_rejected_without_oom_event(self):
        fake = subprocess.CompletedProcess(
            [], -signal.SIGKILL, "ANX_MEMORY_STARTED\n", ""
        )
        with mock.patch.object(probe, "_run_in_leaf", return_value=fake):
            with self.assertRaisesRegex(AssertionError, "OOM kill not confirmed"):
                probe.verify_memory_enforcement(self.leaf)

    def test_memory_false_positive_rejected_without_sigkill(self):
        def guest(_leaf, _script):
            (self.leaf / "memory.events").write_text("oom_kill 1\n", encoding="ascii")
            return subprocess.CompletedProcess([], 0, "ANX_MEMORY_STARTED\n", "")
        with mock.patch.object(probe, "_run_in_leaf", side_effect=guest):
            with self.assertRaisesRegex(AssertionError, "OOM kill not confirmed"):
                probe.verify_memory_enforcement(self.leaf)


if __name__ == "__main__":
    unittest.main()
