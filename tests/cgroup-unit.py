#!/usr/bin/env python3
"""Mocked cgroup filesystem tests, NOT kernel memory/process enforcement."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from cgroup_v2 import (CgroupError, MEMORY_MAX, PIDS_MAX, delegated_cgroup,
                       join_cgroup)


class DelegatedCgroupTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.parent = self.root / "delegated"
        self.parent.mkdir()
        (self.parent / "cgroup.controllers").write_text("cpu memory pids\n")
        (self.parent / "cgroup.subtree_control").write_text("memory pids\n")
        (self.parent / "cgroup.procs").write_text("")
        self.real_mkdir = os.mkdir
        self.real_rmdir = os.rmdir
        self.real_write_text = Path.write_text

    def fake_mkdir(self, path, mode=0o777):
        self.real_mkdir(path, mode)
        directory = Path(path)
        for file in ("memory.max", "pids.max", "cgroup.procs", "cgroup.kill"):
            self.real_write_text(directory / file, "")
        self.real_write_text(directory / "cgroup.events", "populated 0\n")

    def fake_rmdir(self, path):
        kill = Path(path) / "cgroup.kill"
        if kill.exists():
            self.assertEqual(kill.read_text(), "1",
                             "descendants must be killed before leaf removal")
        for entry in Path(path).iterdir():
            entry.unlink()
        self.real_rmdir(path)

    def simulated_kernel(self):
        return (mock.patch("cgroup_v2.os.mkdir", side_effect=self.fake_mkdir),
                mock.patch("cgroup_v2.os.rmdir", side_effect=self.fake_rmdir))

    def test_prepared_limits_and_process_join_and_cleanup(self):
        m1, m2 = self.simulated_kernel()
        with m1, m2:
            with delegated_cgroup(self.parent, root=self.root) as leaf:
                self.assertEqual((leaf / "memory.max").read_text(), str(MEMORY_MAX))
                self.assertEqual((leaf / "pids.max").read_text(), str(PIDS_MAX))
                self.assertEqual(subprocess.run(
                    [sys.executable, "-c", "print('ready')"],
                    preexec_fn=lambda: join_cgroup(leaf),
                    capture_output=True, text=True, check=True,
                ).stdout.strip(), "ready")
                self.assertEqual((leaf / "cgroup.procs").read_text(), "0")
            self.assertFalse(leaf.exists())
        self.assertEqual(list(self.parent.glob("anx-*")), [])

    def test_rejects_parent_outside_root(self):
        with self.assertRaisesRegex(CgroupError, "delegated subdirectory"):
            with delegated_cgroup(self.root, root=self.root):
                self.fail("root must not be usable as a delegated parent")

    def test_rejects_missing_controller_without_creating_group(self):
        (self.parent / "cgroup.subtree_control").write_text("memory\n")
        with self.assertRaisesRegex(CgroupError, "controllers"):
            with delegated_cgroup(self.parent, root=self.root):
                self.fail("must not launch with missing pids controller")
        self.assertFalse(list(self.parent.glob("anx-*")))

    def test_missing_kill_control_fails_closed_and_cleans_directory(self):
        def no_kill(path, mode=0o777):
            self.fake_mkdir(path, mode)
            (Path(path) / "cgroup.kill").unlink()

        with mock.patch("cgroup_v2.os.mkdir", side_effect=no_kill), \
             mock.patch("cgroup_v2.os.rmdir", side_effect=self.fake_rmdir):
            with self.assertRaisesRegex(CgroupError, "cgroup.kill"):
                with delegated_cgroup(self.parent, root=self.root):
                    self.fail("must not run without reliable descendant cleanup")
        self.assertFalse(list(self.parent.glob("anx-*")))

    def test_write_failure_fails_closed_and_removes_leaf(self):
        normal_write = Path.write_text

        def deny_memory(path, value, *args, **kwargs):
            if Path(path).name == "memory.max":
                raise PermissionError("test-denied controller write")
            return normal_write(path, value, *args, **kwargs)

        m1, m2 = self.simulated_kernel()
        with m1, m2, mock.patch.object(Path, "write_text", new=deny_memory):
            with self.assertRaisesRegex(PermissionError, "test-denied"):
                with delegated_cgroup(self.parent, root=self.root):
                    self.fail("failed limit write must block process execution")
        self.assertFalse(list(self.parent.glob("anx-*")))

    def test_child_join_failure_never_executes(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing" / "cgroup.procs"
            marker = Path(directory) / "executed"
            with self.assertRaises(subprocess.SubprocessError):
                subprocess.run(
                    [sys.executable, "-c",
                     "from pathlib import Path; Path(%r).write_text('bad')" % str(marker)],
                    preexec_fn=lambda: join_cgroup(missing),
                    check=False, timeout=10,
                )
            self.assertFalse(marker.exists())


if __name__ == "__main__":
    unittest.main()
