# SPDX-License-Identifier: MIT
"""Regression tests for EoSim#38.

The qemu engine must never report PASSED without executing qemu:
- qemu not installed -> exit 2, "QEMU NOT INSTALLED" (not a pass).
- --dry-run -> exit 0, explicit opt-in only.
- qemu installed -> the constructed command is executed; qemu's exit code
  propagates (0 -> PASSED, non-zero -> FAILED).
"""
from unittest.mock import patch, MagicMock

from click.testing import CliRunner


def _invoke(*args):
    from eosim.cli.main import cli
    return CliRunner().invoke(cli, ["run", *args])


class TestQemuEngineHonesty:
    def test_missing_qemu_is_not_a_pass(self, tmp_path):
        with patch("shutil.which", return_value=None):
            result = _invoke(
                "x86_64-linux", "--timeout", "5", "--log-dir", str(tmp_path))
        assert result.exit_code == 2
        assert "QEMU NOT INSTALLED" in result.output
        assert "PASSED" not in result.output

    def test_dry_run_is_explicit_opt_in(self, tmp_path):
        with patch("shutil.which", return_value=None):
            result = _invoke(
                "x86_64-linux", "--dry-run", "--log-dir", str(tmp_path))
        assert result.exit_code == 0
        assert "DRY RUN" in result.output

    def test_qemu_executed_and_pass_propagated(self, tmp_path):
        fake = MagicMock()
        fake.returncode = 0
        fake.stdout = "SeaBIOS ok"
        fake.stderr = ""
        with patch("shutil.which",
                   return_value="/usr/bin/qemu-system-x86_64"), \
             patch("subprocess.run", return_value=fake) as run:
            result = _invoke(
                "x86_64-linux", "--timeout", "5", "--log-dir", str(tmp_path))
        assert result.exit_code == 0
        assert "PASSED" in result.output
        assert "PASSED (dry run)" not in result.output
        cmd = run.call_args[0][0]
        assert cmd[0] == "/usr/bin/qemu-system-x86_64"
        assert "-nographic" in cmd

    def test_qemu_failure_propagates(self, tmp_path):
        fake = MagicMock()
        fake.returncode = 3
        fake.stdout = ""
        fake.stderr = "boom"
        with patch("shutil.which",
                   return_value="/usr/bin/qemu-system-x86_64"), \
             patch("subprocess.run", return_value=fake):
            result = _invoke(
                "x86_64-linux", "--timeout", "5", "--log-dir", str(tmp_path))
        assert result.exit_code == 1
        assert "FAILED (qemu exit 3)" in result.output
