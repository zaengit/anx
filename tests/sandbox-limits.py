#!/usr/bin/env python3
"""Linux rlimit regressions for the experimental sandbox launcher.

These check kernel rlimits inherited by a subprocess, not APK isolation.
"""
from __future__ import annotations

import json
from pathlib import Path
import resource
import subprocess
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from sandbox import SANDBOX_RESOURCE_LIMITS, apply_sandbox_resource_limits


class SandboxLimitsTest(unittest.TestCase):
    def test_child_has_bounded_hard_and_soft_limits(self):
        host_limits = {kind: resource.getrlimit(kind)
                       for kind, _ in SANDBOX_RESOURCE_LIMITS}
        script = """import json, resource
limits = {
    str(kind): resource.getrlimit(kind)
    for kind in (
        resource.RLIMIT_CORE, resource.RLIMIT_NOFILE,
        resource.RLIMIT_FSIZE, resource.RLIMIT_CPU
    )
}
print(json.dumps(limits))
"""
        child = subprocess.run(
            [sys.executable, "-c", script],
            preexec_fn=apply_sandbox_resource_limits,
            capture_output=True, text=True, check=True, timeout=10,
        )
        actual = json.loads(child.stdout)
        for kind, ceiling in SANDBOX_RESOURCE_LIMITS:
            soft, hard = actual[str(kind)]
            self.assertGreaterEqual(hard, soft)
            self.assertLessEqual(soft, ceiling)
            self.assertLessEqual(hard, ceiling)
            host_soft, host_hard = host_limits[kind]
            if host_soft != resource.RLIM_INFINITY:
                self.assertLessEqual(soft, host_soft)
            if host_hard != resource.RLIM_INFINITY:
                self.assertLessEqual(hard, host_hard)
            self.assertEqual(resource.getrlimit(kind), host_limits[kind],
                             "ANX parent resource limits were modified")

    def test_stricter_inherited_limit_is_preserved(self):
        # Make NOFILE stricter in the child before applying the profile.
        def restrict_then_apply():
            current_soft, current_hard = resource.getrlimit(resource.RLIMIT_NOFILE)
            ceiling = 32
            soft = min(ceiling, current_soft) if current_soft != resource.RLIM_INFINITY else ceiling
            hard = min(ceiling, current_hard) if current_hard != resource.RLIM_INFINITY else ceiling
            resource.setrlimit(resource.RLIMIT_NOFILE, (soft, hard))
            apply_sandbox_resource_limits()

        child = subprocess.run(
            [sys.executable, "-c",
             "import resource; print(resource.getrlimit(resource.RLIMIT_NOFILE))"],
            preexec_fn=restrict_then_apply,
            capture_output=True, text=True, check=True, timeout=10,
        )
        host_soft, host_hard = resource.getrlimit(resource.RLIMIT_NOFILE)
        expected = tuple(
            min(32, x) if x != resource.RLIM_INFINITY else 32
            for x in (host_soft, host_hard)
        )
        self.assertEqual(child.stdout.strip(), str(expected))

    def test_failed_limit_setup_does_not_execute_child(self):
        with mock.patch("sandbox.resource.setrlimit",
                        side_effect=OSError("test-forced-limit-failure")):
            with self.assertRaises(subprocess.SubprocessError):
                subprocess.run(
                    [sys.executable, "-c", "print('should-not-run')"],
                    preexec_fn=apply_sandbox_resource_limits,
                    capture_output=True, text=True, timeout=10,
                    check=False,
                )


if __name__ == "__main__":
    unittest.main()
