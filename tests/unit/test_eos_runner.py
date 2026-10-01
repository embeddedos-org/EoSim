# SPDX-License-Identifier: MIT
"""EoS build/test orchestration: discovery, cmake invocation, result parsing."""

import os
import subprocess
import sys
from unittest.mock import MagicMock

import pytest

from eosim.integrations import eos_runner as er
from eosim.integrations.eos_runner import EosTestResult, EosTestSuite


def completed(rc=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(args=[], returncode=rc, stdout=stdout, stderr=stderr)


class TestSuiteSummary:
    def test_summary_lists_counts_and_results(self):
        suite = EosTestSuite(platform="eos-native", total=2, passed=1, failed=1, duration_s=1.5)
        suite.results = [
            EosTestResult("build", True, duration_s=0.25),
            EosTestResult("test_uart", False, duration_s=1.0),
        ]
        lines = suite.summary().splitlines()
        assert lines[0] == "EoSim Test Suite: eos-native"
        assert lines[1] == "  Total: 2 | Passed: 1 | Failed: 1 | Skipped: 0"
        assert lines[2] == "  Duration: 1.50s"
        assert lines[4].startswith("  [PASS] build") and lines[4].endswith("(0.25s)")
        assert lines[5].startswith("  [FAIL] test_uart") and lines[5].endswith("(1.00s)")


@pytest.fixture
def only_tmp_files(monkeypatch, tmp_path):
    """Hide host paths (e.g. a real ~/EoS checkout) from the discovery helpers."""
    real_isfile, real_exists = os.path.isfile, os.path.exists
    root = str(tmp_path)

    def inside(p):
        return os.path.abspath(p).startswith(root)

    monkeypatch.setattr(er.os.path, "isfile", lambda p: inside(p) and real_isfile(p))
    monkeypatch.setattr(er.os.path, "exists", lambda p: inside(p) and real_exists(p))
    monkeypatch.setenv("HOME", root)
    monkeypatch.delenv("EOS_SOURCE", raising=False)
    monkeypatch.chdir(tmp_path)
    return tmp_path


class TestDiscovery:
    def test_env_var_takes_precedence(self, only_tmp_files, monkeypatch):
        src = only_tmp_files / "custom"
        src.mkdir()
        (src / "CMakeLists.txt").write_text("project(eos)")
        (only_tmp_files / "eos").mkdir()
        (only_tmp_files / "eos" / "CMakeLists.txt").write_text("")
        monkeypatch.setenv("EOS_SOURCE", str(src))
        assert er.find_eos_source() == str(src)

    def test_cwd_checkout_found(self, only_tmp_files):
        (only_tmp_files / "eos").mkdir()
        (only_tmp_files / "eos" / "CMakeLists.txt").write_text("")
        assert er.find_eos_source() == os.path.abspath(str(only_tmp_files / "eos"))

    def test_directory_without_cmakelists_ignored(self, only_tmp_files, monkeypatch):
        (only_tmp_files / "eos").mkdir()
        monkeypatch.setenv("EOS_SOURCE", str(only_tmp_files / "eos"))
        assert er.find_eos_source() is None

    def test_cmake_on_path(self, monkeypatch):
        monkeypatch.setattr(er.shutil, "which", lambda n: "/opt/cmake/bin/cmake")
        assert er.find_cmake() == "/opt/cmake/bin/cmake"

    def test_cmake_fallback_locations(self, monkeypatch):
        monkeypatch.setattr(er.shutil, "which", lambda n: None)
        monkeypatch.setattr(er.os.path, "exists", lambda p: p == "/usr/local/bin/cmake")
        assert er.find_cmake() == "/usr/local/bin/cmake"
        monkeypatch.setattr(er.os.path, "exists", lambda p: False)
        assert er.find_cmake() is None


class TestBuild:
    @pytest.fixture
    def run(self, monkeypatch):
        monkeypatch.setattr(er, "find_cmake", lambda: "cmake")
        run = MagicMock(return_value=completed(0, "ok"))
        monkeypatch.setattr(er.subprocess, "run", run)
        return run

    def test_no_cmake(self, monkeypatch, tmp_path):
        monkeypatch.setattr(er, "find_cmake", lambda: None)
        assert er.build_eos(str(tmp_path)) == (
            False,
            "cmake not found — install CMake to build EoS",
        )

    def test_configure_and_build(self, run, tmp_path):
        src, bld = str(tmp_path / "src"), str(tmp_path / "bld")
        ok, log = er.build_eos(src, bld)
        assert ok is True
        assert [c.args[0] for c in run.call_args_list] == [
            ["cmake", "-B", bld, "-S", src, "-DEOS_BUILD_TESTS=ON"],
            ["cmake", "--build", bld],
        ]
        assert f"$ cmake -B {bld} -S {src} -DEOS_BUILD_TESTS=ON" in log
        assert f"$ cmake --build {bld}" in log
        assert os.path.isdir(bld)

    def test_default_build_dir_and_no_tests(self, run, tmp_path):
        er.build_eos(str(tmp_path), tests=False)
        bld = os.path.join(str(tmp_path), "eosim-build")
        assert run.call_args_list[0].args[0] == ["cmake", "-B", bld, "-S", str(tmp_path)]
        assert os.path.isdir(bld)

    def test_configure_failure_stops_before_build(self, run, tmp_path):
        run.return_value = completed(1, "cfg out", "CMake Error: no compiler")
        ok, log = er.build_eos(str(tmp_path), str(tmp_path / "b"))
        assert ok is False
        assert "CMake Error: no compiler" in log
        assert run.call_count == 1

    def test_build_failure(self, run, tmp_path):
        run.side_effect = [completed(0, "configured"), completed(2, "", "undefined reference")]
        ok, log = er.build_eos(str(tmp_path), str(tmp_path / "b"))
        assert ok is False
        assert log.splitlines()[-1] == "undefined reference"

    def test_configure_timeout(self, run, tmp_path):
        run.side_effect = subprocess.TimeoutExpired(cmd="cmake", timeout=120)
        ok, log = er.build_eos(str(tmp_path), str(tmp_path / "b"))
        assert ok is False and log.startswith("Build configure failed:")

    def test_build_tool_missing(self, run, tmp_path):
        run.side_effect = [completed(0), FileNotFoundError("ninja")]
        ok, log = er.build_eos(str(tmp_path), str(tmp_path / "b"))
        assert (ok, log) == (False, "Build failed: ninja")


def make_exe(path, executable=True):
    path.write_text("#!/bin/sh\n")
    path.chmod(0o755 if executable else 0o644)


@pytest.mark.skipif(os.name == "nt", reason="POSIX executable-bit discovery")
class TestRunEosTests:
    @pytest.fixture
    def build_ok(self, monkeypatch):
        monkeypatch.setattr(er, "build_eos", lambda s, b, tests: (True, "build log"))

    def test_build_failure_is_single_failed_result(self, monkeypatch, tmp_path):
        monkeypatch.setattr(er, "build_eos", lambda s, b, tests: (False, "boom"))
        suite = er.run_eos_tests(str(tmp_path), str(tmp_path / "b"))
        assert (suite.total, suite.passed, suite.failed) == (1, 0, 1)
        assert suite.results[0].name == "build"
        assert suite.results[0].output == "boom"
        assert suite.build_log == "boom"

    def test_runs_executables_in_tests_subdir(self, monkeypatch, tmp_path, build_ok):
        bld = tmp_path / "b"
        (bld / "tests").mkdir(parents=True)
        make_exe(bld / "tests" / "test_a")
        make_exe(bld / "tests" / "test_b")
        make_exe(bld / "tests" / "test_c", executable=False)
        (bld / "tests" / "README").write_text("")
        outcomes = {"test_a": completed(0, "3 passed"), "test_b": completed(3, "", "assert failed")}
        run = MagicMock(side_effect=lambda cmd, **kw: outcomes[os.path.basename(cmd[0])])
        monkeypatch.setattr(er.subprocess, "run", run)

        suite = er.run_eos_tests(str(tmp_path), str(bld))

        assert [c.args[0] for c in run.call_args_list] == [
            [str(bld / "tests" / "test_a")],
            [str(bld / "tests" / "test_b")],
        ]
        assert all(c.kwargs["cwd"] == str(bld) for c in run.call_args_list)
        assert [r.name for r in suite.results] == ["build", "test_a", "test_b"]
        assert (suite.total, suite.passed, suite.failed) == (3, 2, 1)
        assert suite.results[2].output == "assert failed"
        assert suite.results[2].return_code == 3

    def test_timeout_and_permission_errors_fail_tests(self, monkeypatch, tmp_path, build_ok):
        bld = tmp_path / "b"
        bld.mkdir()
        make_exe(bld / "test_hang")
        make_exe(bld / "test_perm")
        errors = {
            "test_hang": subprocess.TimeoutExpired(cmd="t", timeout=30),
            "test_perm": PermissionError("not allowed"),
        }

        def run(cmd, **kw):
            raise errors[os.path.basename(cmd[0])]

        monkeypatch.setattr(er.subprocess, "run", run)
        suite = er.run_eos_tests(str(tmp_path), str(bld))
        hang, perm = suite.results[1:]
        assert (hang.passed, hang.output, hang.return_code) == (False, "Timeout after 30s", -1)
        assert (perm.passed, perm.output, perm.return_code) == (False, "not allowed", -1)
        assert suite.failed == 2

    def test_timeout_after_passing_test_has_no_return_code(self, monkeypatch, tmp_path, build_ok):
        bld = tmp_path / "b"
        bld.mkdir()
        make_exe(bld / "test_1ok")
        make_exe(bld / "test_2hang")

        def run(cmd, **kw):
            if cmd[0].endswith("test_2hang"):
                raise subprocess.TimeoutExpired(cmd="t", timeout=30)
            return completed(0)

        monkeypatch.setattr(er.subprocess, "run", run)
        suite = er.run_eos_tests(str(tmp_path), str(bld))
        assert suite.results[1].return_code == 0
        assert suite.results[2].passed is False
        assert suite.results[2].return_code == -1  # not the previous test's exit code


class TestRunEosuiteTests:
    @pytest.fixture
    def run(self, monkeypatch):
        run = MagicMock()
        monkeypatch.setattr(er.subprocess, "run", run)
        return run

    def test_parses_pytest_summary(self, run, tmp_path):
        run.return_value = completed(1, "....F\n=== 5 passed, 2 failed, 1 skipped in 0.12s ===\n")
        suite = er.run_eosuite_tests(str(tmp_path))
        cmd = [
            sys.executable,
            "-m",
            "pytest",
            os.path.join(str(tmp_path), "tests"),
            "-q",
            "--tb=line",
        ]
        assert run.call_args.args[0] == cmd
        assert run.call_args.kwargs["cwd"] == str(tmp_path)
        assert (suite.passed, suite.failed, suite.skipped, suite.total) == (5, 2, 1, 7)
        (res,) = suite.results
        assert (res.name, res.passed, res.return_code) == ("pytest", False, 1)
        assert suite.platform == "eapps"

    def test_all_passed(self, run, tmp_path):
        run.return_value = completed(0, "", "12 passed in 1.0s\n")
        suite = er.run_eosuite_tests(str(tmp_path))
        assert (suite.passed, suite.failed, suite.total) == (12, 0, 12)
        assert suite.results[0].passed is True

    def test_only_failures_is_a_failure(self, run, tmp_path):
        run.return_value = completed(1, "FF\n=== 2 failed in 0.05s ===\n")
        suite = er.run_eosuite_tests(str(tmp_path))
        assert (suite.passed, suite.failed, suite.total) == (0, 2, 2)
        assert suite.results[0].passed is False

    def test_runner_error(self, run, tmp_path):
        run.side_effect = subprocess.TimeoutExpired(cmd="pytest", timeout=120)
        suite = er.run_eosuite_tests(str(tmp_path))
        assert (suite.total, suite.failed) == (1, 1)
        assert suite.results[0].passed is False
        assert "timed out" in suite.results[0].output
