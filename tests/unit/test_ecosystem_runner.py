# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""The ecosystem runner must find every product and never invent a pass.

Two defects motivate this file:

1. find_repos held a hardcoded list of seven lowercase names
   ("eai", "eni", "eipc", "eboot", "ebuild-tool"). None of those match the
   real directory names on a case-sensitive filesystem, so it discovered
   2 of the 19 repos in the workspace and run_ecosystem_tests silently
   `continue`d past anything not on the list.

2. test_c_repo ended with

       tests_passed = max(tests_passed, tests_run if build_ok else 0)
       tests_failed = max(0, tests_run - tests_passed)
       passed = build_ok and tests_failed == 0

   where tests_run was a count of executables on disk. Any repo that
   compiled reported every test passing and a verdict of PASS, whether or
   not a single test had run.
"""

import os

import pytest

from eosim.integrations import ecosystem as eco
from eosim.integrations.ecosystem import (
    DEPS, ERROR, FAIL, PASS, SKIP,
    EcosystemReport, RepoTestResult,
    _parse_ctest, _parse_pytest,
    _external_missing_modules,
    _missing_modules,
    _unmet_toolchain,
    detect_components, detect_kind, detect_kinds, find_repos,
    test_repo as run_one_repo,
)


def _repo(tmp_path, name, *files):
    d = tmp_path / name
    (d / ".git").mkdir(parents=True)
    for f in files:
        (d / f).write_text("", encoding="utf-8")
    return d


class TestDiscovery:
    def test_finds_every_git_directory(self, tmp_path):
        for n in ("eos", "eAI", "eNI", "eIPC", "eBoot", "ebuild", "EoStudio"):
            _repo(tmp_path, n)
        assert set(find_repos(str(tmp_path))) == {
            "eos", "eAI", "eNI", "eIPC", "eBoot", "ebuild", "EoStudio"}

    def test_casing_is_not_assumed(self, tmp_path):
        """The old list looked for 'eai'; the directory is 'eAI'."""
        _repo(tmp_path, "eAI")
        assert "eAI" in find_repos(str(tmp_path))

    def test_non_repo_directories_are_ignored(self, tmp_path):
        _repo(tmp_path, "eos")
        (tmp_path / "scratch").mkdir()
        (tmp_path / "docs").mkdir()
        assert set(find_repos(str(tmp_path))) == {"eos"}

    def test_dot_github_is_not_a_product(self, tmp_path):
        _repo(tmp_path, ".github")
        _repo(tmp_path, "eos")
        assert set(find_repos(str(tmp_path))) == {"eos"}

    def test_missing_workspace_is_empty_not_an_error(self):
        assert find_repos("/nonexistent/path") == {}


class TestKindDetection:
    @pytest.mark.parametrize("marker,kind", [
        ("CMakeLists.txt", "cmake"),
        ("pyproject.toml", "python"),
        ("setup.py", "python"),
        ("go.mod", "go"),
        ("Cargo.toml", "cargo"),
        ("package.json", "node"),
        ("Makefile", "make"),
    ])
    def test_detects_from_files_present(self, tmp_path, marker, kind):
        d = _repo(tmp_path, "r", marker)
        assert detect_kind(str(d)) == kind

    def test_cmake_wins_over_a_wrapper_makefile(self, tmp_path):
        """A CMake project often ships a convenience Makefile; ctest is the
        runner that knows about its tests."""
        d = _repo(tmp_path, "r", "CMakeLists.txt", "Makefile")
        assert detect_kind(str(d)) == "cmake"

    def test_unknown_when_nothing_is_recognised(self, tmp_path):
        assert detect_kind(str(_repo(tmp_path, "r"))) == "unknown"


class TestNoFabricatedPasses:
    """Nothing may report PASS unless a suite ran and reported no failures."""

    def test_unknown_project_is_skipped_not_passed(self, tmp_path):
        d = _repo(tmp_path, "mystery")
        r = run_one_repo("mystery", str(d))
        assert r.status == SKIP
        assert r.passed is False

    def test_python_repo_without_tests_is_skipped_not_passed(self, tmp_path):
        d = _repo(tmp_path, "p", "pyproject.toml")
        r = run_one_repo("p", str(d))
        assert r.status == SKIP
        assert r.passed is False
        assert "no tests" in r.reason

    def test_missing_toolchain_is_skipped_not_passed(self, tmp_path, monkeypatch):
        monkeypatch.setattr(eco.shutil, "which", lambda _n: None)
        d = _repo(tmp_path, "g", "go.mod")
        r = run_one_repo("g", str(d))
        assert r.status == SKIP
        assert r.passed is False

    def test_passed_is_derived_from_status_only(self):
        """The old code could set build_ok and a pass count independently of
        whether anything ran; `passed` now has one source of truth."""
        r = RepoTestResult(repo="x", build_ok=True, tests_run=99, tests_passed=99)
        assert r.passed is False          # status is still the default SKIP
        r.status = PASS
        assert r.passed is True


class TestResultParsing:
    def test_ctest_summary_is_read_not_guessed(self):
        out = "100% tests passed, 0 tests failed out of 24"
        assert _parse_ctest(out) == (24, 0, 24)

    def test_ctest_failures_are_counted(self):
        out = "91% tests passed, 2 tests failed out of 23"
        assert _parse_ctest(out) == (21, 2, 23)

    def test_ctest_without_a_summary_is_not_a_pass(self):
        assert _parse_ctest("ninja: no work to do") is None

    def test_pytest_counts_are_read(self):
        assert _parse_pytest("288 passed in 2.21s") == (288, 0, 0)

    def test_failures_and_errors_are_kept_apart(self):
        """A broken assertion and an uninstalled dependency are different
        problems, and only one of them is the repo's fault."""
        assert _parse_pytest("3 failed, 256 passed, 1 error in 2.3s") == (256, 3, 1)

    def test_pytest_collection_error_is_counted(self):
        """An uncollectable suite must never read as zero problems."""
        assert _parse_pytest(
            "!!! Interrupted: 1 error during collection !!!") == (0, 0, 1)

    def test_pytest_silence_yields_no_counts(self):
        """A crash with no summary at all is handled by the caller, which
        turns it into SKIP or FAIL based on the exit code -- never a pass."""
        assert _parse_pytest("Segmentation fault") is None


class TestMultipleBuildSystems:
    """A repo with two build systems must have both exercised: ebuild is a
    Python CLI whose CMakeLists integrates sibling repos, and a broken CMake
    build there stayed invisible behind a green Python suite."""

    def test_both_are_detected(self, tmp_path):
        d = _repo(tmp_path, "ebuild", "CMakeLists.txt", "pyproject.toml")
        assert detect_kinds(str(d)) == ["cmake", "python"]

    def test_primary_kind_is_the_first(self, tmp_path):
        d = _repo(tmp_path, "ebuild", "CMakeLists.txt", "pyproject.toml")
        assert detect_kind(str(d)) == "cmake"

    def test_a_make_wrapper_is_not_a_second_system(self, tmp_path):
        """Makefile is only a fallback; a CMake project's Makefile is a
        convenience wrapper, not a separate suite to run."""
        d = _repo(tmp_path, "r", "CMakeLists.txt", "Makefile")
        assert detect_kinds(str(d)) == ["cmake"]


class TestDependencyGapsAreNotFailures:
    def test_missing_modules_are_extracted(self, tmp_path):
        from eosim.integrations.ecosystem import _missing_modules
        out = ("ModuleNotFoundError: No module named 'fastapi'\n"
               "ModuleNotFoundError: No module named 'fastapi.routing'\n"
               "ModuleNotFoundError: No module named 'httpx'\n")
        assert _missing_modules(out) == ["fastapi", "httpx"]

    def test_deps_is_not_a_pass(self):
        r = RepoTestResult(repo="eDB", status=DEPS, tests_passed=23)
        assert r.passed is False

    def test_deps_repos_are_not_counted_as_passed(self):
        rep = EcosystemReport(repos_tested=1, repos_skipped=1)
        assert "NOTHING WAS TESTED" in rep.summary()


class TestReportVerdict:
    def test_all_skipped_does_not_read_as_success(self):
        rep = EcosystemReport(repos_tested=3, repos_skipped=3)
        assert "NOTHING WAS TESTED" in rep.summary()

    def test_skips_are_surfaced_alongside_passes(self):
        rep = EcosystemReport(repos_tested=3, repos_passed=2, repos_skipped=1)
        assert "1 repo(s) skipped" in rep.summary()

    def test_any_failure_dominates(self):
        rep = EcosystemReport(repos_tested=3, repos_passed=2, repos_failed=1)
        assert "FAILURES DETECTED" in rep.summary()

    def test_clean_run_says_so(self):
        rep = EcosystemReport(repos_tested=2, repos_passed=2)
        assert "ALL PASSED" in rep.summary()

    def test_failures_are_listed_first(self):
        rep = EcosystemReport(results=[
            RepoTestResult(repo="aaa", status=PASS),
            RepoTestResult(repo="zzz", status=FAIL),
        ])
        body = rep.summary()
        assert body.index("zzz") < body.index("aaa")


class TestBuildDirIsOutsideTheCheckout:
    """Building into the repo leaves an untracked directory behind in every
    repo the runner touches."""

    def test_build_dir_is_not_inside_the_repo(self, tmp_path, monkeypatch):
        from eosim.integrations.ecosystem import _build_dir_for
        monkeypatch.setenv("EOSIM_BUILD_ROOT", str(tmp_path / "cache"))
        repo = tmp_path / "eos"
        repo.mkdir()
        build = _build_dir_for(str(repo))
        assert not build.startswith(str(repo))

    def test_each_repo_gets_its_own_tree(self, tmp_path, monkeypatch):
        from eosim.integrations.ecosystem import _build_dir_for
        monkeypatch.setenv("EOSIM_BUILD_ROOT", str(tmp_path / "cache"))
        (tmp_path / "eos").mkdir()
        (tmp_path / "eBoot").mkdir()
        a = _build_dir_for(str(tmp_path / "eos"))
        b = _build_dir_for(str(tmp_path / "eBoot"))
        assert a != b


class TestBlockedTestsAreNotFailures:
    def test_blocked_count_is_reported_separately(self):
        rep = EcosystemReport(repos_tested=1, total_tests=39,
                              total_passed=23, total_blocked=16)
        body = rep.summary()
        assert "16 blocked on missing deps" in body
        assert "16 failed" not in body

    def test_blocked_is_omitted_when_zero(self):
        rep = EcosystemReport(total_tests=10, total_passed=10)
        assert "blocked" not in rep.summary()


class TestMakeRunner:
    """eosllm is driven by a Makefile. Before this it reported
    "no runner for a 'make' project" and contributed nothing."""

    def test_make_is_wired_to_a_runner(self, tmp_path):
        d = _repo(tmp_path, "m", "Makefile")
        (d / "Makefile").write_text("test:\n\t@true\n", encoding="utf-8")
        r = run_one_repo("m", str(d))
        assert r.kind == "make"
        assert r.status == PASS

    def test_a_makefile_without_a_test_target_is_skipped(self, tmp_path):
        """`make test` against a Makefile with no such rule fails with
        "No rule to make target", which would read as a broken repo rather
        than one that keeps its tests elsewhere."""
        d = _repo(tmp_path, "m", "Makefile")
        (d / "Makefile").write_text("all:\n\t@true\n", encoding="utf-8")
        r = run_one_repo("m", str(d))
        assert r.status == SKIP
        assert "test" in r.reason

    def test_a_failing_make_test_is_a_failure(self, tmp_path):
        d = _repo(tmp_path, "m", "Makefile")
        (d / "Makefile").write_text("test:\n\t@exit 3\n", encoding="utf-8")
        r = run_one_repo("m", str(d))
        assert r.status == FAIL

    def test_make_reports_its_exit_code_not_an_invented_count(self, tmp_path):
        """There is no count to parse from a Makefile, and inventing one is
        the fabrication this module exists to prevent."""
        d = _repo(tmp_path, "m", "Makefile")
        (d / "Makefile").write_text("test:\n\t@true\n", encoding="utf-8")
        r = run_one_repo("m", str(d))
        assert r.tests_run == 0
        assert "exit 0" in r.reason


class TestNestedComponents:
    """A build system below the repo root must still be found.

    detect_kinds looked only at the root, so eos-health (CMake firmware under
    firmware/build-system, a web app under apps/web), eos-aero (a web app four
    levels down) and eCAD-Hardware-Products (pytest tests, no packaging file)
    all reported "unknown". The runner found no runner for that, skipped them,
    and the summary counted the skip alongside the passes. Three of nineteen
    repos were never tested by the tool whose job is to test them.
    """

    def test_root_detection_is_returned_unchanged(self, tmp_path):
        # The guarantee that makes this change safe: a repo detected at the
        # root must keep taking exactly the path it takes today, so the scan
        # cannot regress the repos that already work.
        d = _repo(tmp_path, "eos", "CMakeLists.txt")
        assert detect_components(str(d)) == [("cmake", str(d))]

    def test_root_detection_wins_over_anything_nested(self, tmp_path):
        d = _repo(tmp_path, "ebuild", "CMakeLists.txt", "pyproject.toml")
        (d / "vendored").mkdir()
        (d / "vendored" / "package.json").write_text("{}", encoding="utf-8")
        kinds = [k for k, _ in detect_components(str(d))]
        assert kinds == ["cmake", "python"]
        assert "node" not in kinds

    def test_nested_component_carries_its_own_directory(self, tmp_path):
        # The runners build from the directory handed to them. Reporting
        # "cmake" without the location would send cmake -S at the repo root,
        # which has no CMakeLists.txt — a spurious failure in place of a
        # silent skip is not an improvement.
        d = _repo(tmp_path, "eos-health")
        nested = d / "firmware" / "build-system"
        nested.mkdir(parents=True)
        (nested / "CMakeLists.txt").write_text("", encoding="utf-8")
        assert detect_components(str(d)) == [("cmake", str(nested))]

    def test_several_nested_components_are_all_reported(self, tmp_path):
        d = _repo(tmp_path, "eos-health")
        for sub, marker in (("firmware/build-system", "CMakeLists.txt"),
                            ("apps/web", "package.json")):
            p = d / sub
            p.mkdir(parents=True)
            (p / marker).write_text("", encoding="utf-8")
        assert sorted(k for k, _ in detect_components(str(d))) == ["cmake", "node"]

    def test_vendored_directories_are_not_components(self, tmp_path):
        # A package.json under node_modules belongs to a dependency, not to
        # the repo. Reporting it would have the runner test someone else's code.
        d = _repo(tmp_path, "eOffice")
        vendored = d / "node_modules" / "left-pad"
        vendored.mkdir(parents=True)
        (vendored / "package.json").write_text("{}", encoding="utf-8")
        assert detect_components(str(d)) == [("unknown", str(d))]

    def test_scan_depth_is_bounded(self, tmp_path):
        d = _repo(tmp_path, "deep")
        buried = d / "a" / "b" / "c" / "d" / "e"
        buried.mkdir(parents=True)
        (buried / "package.json").write_text("{}", encoding="utf-8")
        assert detect_components(str(d)) == [("unknown", str(d))]

    def test_a_repo_with_nothing_still_reports_unknown(self, tmp_path):
        d = _repo(tmp_path, "docs-only", "README.md")
        assert detect_components(str(d)) == [("unknown", str(d))]


class TestPythonTestsWithoutPackaging:
    """pytest projects with no pyproject.toml are still pytest projects."""

    def test_tests_directory_alone_identifies_python(self, tmp_path):
        # test_python_repo only ever required a tests/ directory. Demanding
        # pyproject.toml to reach it was the detector asking for something the
        # runner does not use.
        d = _repo(tmp_path, "eCAD-Hardware-Products")
        (d / "tests").mkdir()
        (d / "tests" / "test_rtl_models.py").write_text("", encoding="utf-8")
        assert detect_kinds(str(d)) == ["python"]

    def test_a_tests_directory_without_python_does_not_count(self, tmp_path):
        d = _repo(tmp_path, "thing")
        (d / "tests").mkdir()
        (d / "tests" / "test_main.c").write_text("", encoding="utf-8")
        assert detect_kinds(str(d)) == ["unknown"]

    def test_c_repo_with_c_tests_does_not_also_become_python(self, tmp_path):
        # eBoot has a CMakeLists.txt and a tests/ directory full of C. Pointing
        # pytest at it would report a failure that means nothing.
        d = _repo(tmp_path, "eBoot", "CMakeLists.txt")
        (d / "tests").mkdir()
        (d / "tests" / "helper.py").write_text("", encoding="utf-8")
        assert detect_kinds(str(d)) == ["cmake"]


class TestUnmetToolchainIsNotABrokenBuild:
    """An absent vendor SDK and a missing source file need opposite responses.

    eos-health produced both at once. firmware/build-system stops on
    "NRF5_SDK_PATH not set", which means install something; two other trees stop
    on "Cannot find source file", which means the CMakeLists and the tree
    disagree and no installation will help. Reporting both as FAIL puts them in
    the same column.
    """

    def test_an_unset_sdk_path_is_named(self):
        assert _unmet_toolchain(
            "NRF5_SDK_PATH not set.  Download nRF5 SDK 17.1.0"
        ) == "NRF5_SDK_PATH"

    def test_an_unset_toolchain_root_is_named(self):
        assert _unmet_toolchain("ARM_TOOLCHAIN_ROOT not set") == "ARM_TOOLCHAIN_ROOT"

    def test_a_find_package_failure_is_named(self):
        assert _unmet_toolchain("Could NOT find OpenSSL") == "OpenSSL"

    def test_a_missing_source_file_stays_a_failure(self):
        # The repository is referencing code it does not contain. Classifying
        # that as a dependency problem would hide a real defect behind a status
        # that reads as "not our fault".
        assert _unmet_toolchain(
            "CMake Error at CMakeLists.txt:65 (add_executable):\n"
            "  Cannot find source file:\n    src/main.c") is None

    def test_a_target_with_no_sources_stays_a_failure(self):
        assert _unmet_toolchain(
            "No SOURCES given to target: health_band_neuro.elf") is None

    def test_a_repo_defect_wins_when_both_appear(self):
        # eos-health emits both in one configure run. The repo defect is the
        # one that must survive the classification.
        assert _unmet_toolchain(
            "NRF5_SDK_PATH not set\nCannot find source file: a.c") is None

    def test_an_unrecognised_failure_stays_a_failure(self):
        assert _unmet_toolchain("CMake Error: something else entirely") is None


class TestAbsentThirdPartyModulesAreNotFailures:
    """pytest aborting on an uninstalled dependency is a DEPS, not a FAIL.

    When collection fails, pytest prints no summary at all, so the counts are
    never parsed and the DEPS branch further down is never reached. Five repos
    in a full ecosystem run were reported FAIL for "No module named 'click'".
    """

    def test_a_third_party_module_is_reported(self, tmp_path):
        out = "E   ModuleNotFoundError: No module named 'click'"
        assert _external_missing_modules(out, str(tmp_path)) == ["click"]

    def test_the_repos_own_package_is_not(self, tmp_path):
        # The runner puts the checkout on PYTHONPATH, so a repo failing to
        # import its own package is a real defect and must stay a FAIL.
        (tmp_path / "eostudio").mkdir()
        out = "E   ModuleNotFoundError: No module named 'eostudio'"
        assert _external_missing_modules(out, str(tmp_path)) == []

    def test_a_src_layout_package_is_recognised_as_the_repos_own(self, tmp_path):
        (tmp_path / "src" / "mypkg").mkdir(parents=True)
        out = "No module named 'mypkg'"
        assert _external_missing_modules(out, str(tmp_path)) == []

    def test_a_single_module_file_counts_as_the_repos_own(self, tmp_path):
        (tmp_path / "helper.py").write_text("", encoding="utf-8")
        out = "No module named 'helper'"
        assert _external_missing_modules(out, str(tmp_path)) == []

    def test_the_repos_own_absence_does_not_mask_a_third_party_one(self, tmp_path):
        (tmp_path / "eostudio").mkdir()
        out = ("No module named 'eostudio'\n"
               "No module named 'click'")
        assert _external_missing_modules(out, str(tmp_path)) == ["click"]

    def test_nothing_missing_yields_nothing(self, tmp_path):
        assert _external_missing_modules("all fine", str(tmp_path)) == []


class TestMissingModuleSpellings:
    """Both forms of Python's message, including the one that matters most."""

    def test_the_quoted_form(self):
        assert _missing_modules("No module named 'click'") == ["click"]

    def test_the_bare_form(self):
        # `python -m pytest` on an interpreter without pytest prints no quotes.
        # This is the case where the test runner itself is absent — exactly
        # when nothing else in the output explains the failure — and missing it
        # reported five repos as FAIL for an environment problem.
        assert _missing_modules("No module named pytest") == ["pytest"]

    def test_a_dotted_name_reduces_to_its_top_level(self):
        assert _missing_modules("No module named 'a.b.c'") == ["a"]

    def test_both_forms_together_and_deduplicated(self):
        out = "No module named pytest\nNo module named 'click'\nNo module named 'click'"
        assert _missing_modules(out) == ["pytest", "click"]
