#!/usr/bin/env python3
"""End-to-end wall-clock timeout regression via the actual ANX CLI/fake bwrap.

Mocked helper only. Does NOT prove that orphaned grandchildren or a hostile
APK are terminated without a delegated cgroup v2 controller.
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from anx import DEFAULT_SANDBOX_TIMEOUT_SECONDS, MAX_SANDBOX_TIMEOUT_SECONDS


class SandboxTimeoutTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="anx-timeout-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.helper = self.bin / "bwrap"
        self.counter = self.bin / "invocations"
        self.pid = self.bin / "pid"
        self.apk = ROOT / "build" / "demo.apk"
        self.framework = ROOT / "build" / "framework" / "classes.dex"
        self.assertTrue(self.apk.is_file(), "build demo APK before this test")
        self.assertTrue(self.framework.is_file(), "build framework before this test")
        self.environment = os.environ.copy()
        self.environment.update({
            "PATH": str(self.bin) + os.pathsep + self.environment.get("PATH", ""),
            "ANDROID_DATA": str(self.root / "art-cache"),
            "ANX_APP_DATA_HOME": str(self.root / "apps"),
        })
        self.base = [
            sys.executable, str(ROOT / "scripts" / "anx.py"),
            "run", str(self.apk), "--art", "/usr/bin/true",
            "--framework-dex", str(self.framework),
            "--backend", "console", "--unsafe-host-execution",
        ]

    def helper_script(self, *, sleep: bool):
        self.helper.write_text(
            "#!/usr/bin/python3\n"
            "import os\n"
            "from pathlib import Path\n"
            "import time\n"
            "p = Path(__file__)\n"
            "with p.with_name('invocations').open('a') as output:\n"
            "    output.write('launched\\n')\n"
            "p.with_name('pid').write_text(str(os.getpid()))\n"
            + ("time.sleep(60)\n" if sleep else "raise SystemExit(42)\n"),
            encoding="utf-8",
        )
        self.helper.chmod(0o700)

    def invoke(self, *flags: str):
        return subprocess.run(
            self.base + list(flags), env=self.environment, check=False,
            capture_output=True, text=True, timeout=15,
        )

    def test_one_second_timeout_kills_helper_and_never_retries(self):
        self.helper_script(sleep=True)
        result = self.invoke("--experimental-sandbox",
                             "--sandbox-timeout-seconds", "1")
        self.assertEqual(result.returncode, 124, result.stdout + result.stderr)
        self.assertIn("exceeded wall-clock timeout of 1s", result.stderr)
        self.assertEqual(self.counter.read_text().splitlines(), ["launched"])
        self.assertTrue(self.pid.exists(), "fake helper did not execute")
        pid = int(self.pid.read_text())
        with self.assertRaises(ProcessLookupError):
            os.kill(pid, 0)

    def test_fast_helper_exit_preserved(self):
        self.helper_script(sleep=False)
        result = self.invoke("--experimental-sandbox",
                             "--sandbox-timeout-seconds", "2")
        self.assertEqual(result.returncode, 42, result.stderr)
        self.assertEqual(self.counter.read_text().splitlines(), ["launched"])

    def test_timeout_argument_requires_sandbox(self):
        self.helper_script(sleep=True)
        result = self.invoke("--sandbox-timeout-seconds", "1")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("requires --experimental-sandbox", result.stderr)
        self.assertFalse(self.counter.exists(), "helper ran after option rejection")

    def test_rejects_zero_and_out_of_range_values(self):
        self.helper_script(sleep=True)
        for value in ("0", "-1", str(MAX_SANDBOX_TIMEOUT_SECONDS + 1)):
            with self.subTest(value=value):
                result = self.invoke("--experimental-sandbox",
                                     "--sandbox-timeout-seconds", value)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn("must be between 1 and", result.stderr)
        self.assertFalse(self.counter.exists(), "helper ran with invalid timeout")

    def test_default_budget_is_five_minutes(self):
        self.assertEqual(DEFAULT_SANDBOX_TIMEOUT_SECONDS, 300)
        self.assertEqual(MAX_SANDBOX_TIMEOUT_SECONDS, 3600)


if __name__ == "__main__":
    unittest.main()
