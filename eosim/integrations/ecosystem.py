# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""EoS Ecosystem Runner — build and test every EoS repo through EoSim.

Discovery is by inspection, not by a hardcoded list: any immediate
subdirectory of the workspace holding a ``.git`` is a repo, and its build
system is detected from the files it actually contains. A new product becomes
testable by being cloned into the workspace, with no change here.

Nothing in this module infers a pass. A repo that could not be tested reports
SKIP with the reason, never PASS -- an unrunnable suite and a green suite are
different facts and the report keeps them apart.
"""

import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field

#: Result statuses. SKIP means "not tested here", which is not a pass.
#: DEPS is a narrower SKIP: the suite exists and would run, but the repo's
#: own declared dependencies are absent from this environment. Keeping it
#: apart from FAIL matters -- a missing fastapi is not a broken test.
PASS, FAIL, SKIP, ERROR, DEPS = "PASS", "FAIL", "SKIP", "ERROR", "DEPS"

#: Directories that live beside the repos but are not products.
_NOT_A_PRODUCT = {".github", ".git"}

_BUILD_TIMEOUT_S = 900
_TEST_TIMEOUT_S = 900


@dataclass
class RepoTestResult:
    repo: str
    kind: str = "unknown"
    status: str = SKIP
    reason: str = ""
    tests_run: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    build_ok: bool = False
    duration_s: float = 0.0
    output: str = ""
    sim_result: dict = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        """True only when a suite actually ran and reported no failures."""
        return self.status == PASS


@dataclass
class EcosystemReport:
    repos_tested: int = 0
    repos_passed: int = 0
    repos_failed: int = 0
    repos_skipped: int = 0
    total_tests: int = 0
    total_passed: int = 0
    total_failed: int = 0
    total_blocked: int = 0
    duration_s: float = 0.0
    results: list = field(default_factory=list)
    simulations: list = field(default_factory=list)

    def summary(self) -> str:
        lines = []
        lines.append("=" * 72)
        lines.append("  EoSim Ecosystem Validation Report")
        lines.append("=" * 72)
        lines.append("")
        lines.append(
            "  Repos:  %d discovered | %d passed | %d failed | %d skipped"
            % (self.repos_tested, self.repos_passed, self.repos_failed, self.repos_skipped)
        )
        counts = "  Tests:  %d run | %d passed | %d failed" % (
            self.total_tests,
            self.total_passed,
            self.total_failed,
        )
        if self.total_blocked:
            # Blocked tests never ran; folding them into "failed" would read
            # as broken code when the cause is an absent dependency.
            counts += " | %d blocked on missing deps" % self.total_blocked
        lines.append(counts)
        lines.append(f"  Time:   {self.duration_s:.1f}s")
        lines.append("")
        for r in sorted(self.results, key=lambda x: (x.status != FAIL, x.repo)):
            detail = ""
            if r.status in (PASS, FAIL, DEPS) and r.tests_run:
                detail = "tests:%d/%d" % (r.tests_passed, r.tests_run)
                if r.reason:
                    detail += "  " + r.reason
            elif r.reason:
                # No count to show — a Makefile-driven suite, or a skip.
                detail = r.reason[:44]
            elif r.reason:
                detail = r.reason[:44]
            lines.append(
                "  [%-5s] %-26s %-9s %-46s (%.1fs)"
                % (r.status, r.repo, r.kind, detail, r.duration_s)
            )
        if self.simulations:
            lines.append("")
            lines.append("  Simulations:")
            for s in self.simulations:
                lines.append(
                    "    [%-5s] %-20s %d cycles  %.1fs"
                    % (
                        PASS if s.get("success") else FAIL,
                        s.get("platform", "?"),
                        s.get("cycles", 0),
                        s.get("duration_s", 0),
                    )
                )
        lines.append("")
        lines.append("=" * 72)
        if self.repos_failed:
            verdict = "FAILURES DETECTED"
        elif self.repos_skipped and not self.repos_passed:
            verdict = "NOTHING WAS TESTED"
        elif self.repos_skipped:
            verdict = "PASSED (%d repo(s) skipped — see above)" % self.repos_skipped
        else:
            verdict = "ALL PASSED"
        lines.append("  VERDICT: %s" % verdict)
        lines.append("=" * 72)
        return "\n".join(lines)


def find_repos(workspace: str = None) -> dict:
    """Every git repo directly under the workspace, keyed by directory name.

    Discovery is by inspection rather than a fixed list, because a hardcoded
    list goes stale and its casing has to match the filesystem exactly -- the
    previous version looked for "eai"/"eni"/"eipc"/"eboot" and found none of
    them on a case-sensitive filesystem.
    """
    workspace = _resolve_workspace(workspace)
    if not workspace:
        return {}

    repos = {}
    try:
        entries = sorted(os.listdir(workspace))
    except OSError:
        return {}

    for name in entries:
        if name in _NOT_A_PRODUCT:
            continue
        path = os.path.join(workspace, name)
        if os.path.isdir(os.path.join(path, ".git")):
            repos[name] = path
    return repos


def _resolve_workspace(workspace: str = None) -> str:
    if workspace:
        return workspace if os.path.isdir(workspace) else ""
    env = os.environ.get("EOS_WORKSPACE", "")
    if env and os.path.isdir(env):
        return env
    for candidate in (os.getcwd(), os.path.join(os.getcwd(), "..")):
        candidate = os.path.abspath(candidate)
        if os.path.isdir(os.path.join(candidate, "eos", ".git")):
            return candidate
    return ""


def detect_kinds(path: str) -> list:
    """Every build system the repo has, most significant first.

    A repo can carry more than one. ebuild is a Python CLI that also ships a
    CMakeLists integrating sibling repos; returning only one of those would
    leave the other untested, which is how a broken CMake build stayed
    invisible while the Python suite was green.
    """

    def has(*names):
        return any(os.path.exists(os.path.join(path, x)) for x in names)

    kinds = []
    if has("CMakeLists.txt"):
        kinds.append("cmake")
    if has("pyproject.toml", "setup.py"):
        kinds.append("python")
    if has("go.mod"):
        kinds.append("go")
    if has("Cargo.toml"):
        kinds.append("cargo")
    if has("package.json"):
        kinds.append("node")
    if not kinds and _has_python_tests(path):
        # A repo can be a perfectly good pytest project with no packaging file.
        # eCAD-Hardware-Products carries tests/test_rtl_models.py and no
        # pyproject.toml, and test_python_repo() only ever needed a tests/
        # directory. Requiring pyproject.toml to notice that was the detector
        # asking for something the runner does not use.
        #
        # Guarded on `not kinds` so a repo whose real build system is already
        # identified does not also get pytest pointed at it: eBoot has both a
        # CMakeLists.txt and a tests/ directory full of C.
        kinds.append("python")
    if not kinds and has("Makefile", "makefile"):
        kinds.append("make")
    if not kinds and has("mkdocs.yml", "_config.yml", "index.html"):
        kinds.append("docs")
    return kinds or ["unknown"]


def _has_python_tests(path: str) -> bool:
    """True when tests/ or test/ holds at least one Python file."""
    for d in ("tests", "test"):
        tdir = os.path.join(path, d)
        if not os.path.isdir(tdir):
            continue
        for _root, _dirs, files in os.walk(tdir):
            if any(f.endswith(".py") for f in files):
                return True
    return False


# Directories that never contain a component of the repo itself. node_modules
# is the one that matters: a vendored package.json would otherwise be reported
# as a build system belonging to the repo.
_NOT_A_COMPONENT_DIR = {
    ".git",
    "node_modules",
    "build",
    "dist",
    "venv",
    ".venv",
    "__pycache__",
    ".tox",
    "target",
    "vendor",
    "third_party",
    ".mypy_cache",
    ".pytest_cache",
}

_NESTED_MAX_DEPTH = 4


def detect_components(path: str) -> list:
    """(kind, directory) for every build system in the repo, root or nested.

    The runners build from the directory they are handed, so a nested component
    has to carry its own location. Returning just the kind would send
    test_c_repo at eos-health's root, which has no CMakeLists.txt, turning a
    silent skip into a spurious failure.

    Root detection runs first and is returned unchanged when it finds anything,
    so every repo that is detected today keeps taking exactly the path it takes
    today. The scan below only ever runs for a repo that would otherwise have
    been reported "unknown" and skipped.
    """
    kinds = detect_kinds(path)
    if kinds != ["unknown"]:
        return [(k, path) for k in kinds]

    found = []
    seen = set()
    base_depth = os.path.abspath(path).count(os.sep)

    for root, dirs, _files in os.walk(path):
        dirs[:] = sorted(d for d in dirs if d not in _NOT_A_COMPONENT_DIR and not d.startswith("."))
        if os.path.abspath(root).count(os.sep) - base_depth >= _NESTED_MAX_DEPTH:
            dirs[:] = []
            continue
        if root == path:
            continue
        for kind in detect_kinds(root):
            if kind in ("unknown", "docs"):
                continue
            key = (kind, root)
            if key not in seen:
                seen.add(key)
                found.append(key)

    return found or [("unknown", path)]


def detect_kind(path: str) -> str:
    """The repo's primary build system. See detect_kinds for the full set."""
    return detect_kinds(path)[0]


def _skip(result: RepoTestResult, reason: str, start: float) -> RepoTestResult:
    result.status = SKIP
    result.reason = reason
    result.duration_s = time.time() - start
    return result


def _build_dir_for(path: str) -> str:
    """Where to put a repo's CMake tree.

    Deliberately outside the checkout: building into <repo>/eosim-build left
    an untracked directory in every repo the runner touched, which shows up
    as a dirty working tree and, in a repo without a matching .gitignore, as
    something a developer might commit. EOSIM_BUILD_ROOT overrides it.
    """
    root = os.environ.get("EOSIM_BUILD_ROOT")
    if not root:
        base = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
        root = os.path.join(base, "eosim", "ecosystem")
    build_dir = os.path.join(root, os.path.basename(os.path.abspath(path)))
    os.makedirs(build_dir, exist_ok=True)
    return build_dir


def test_c_repo(name: str, path: str) -> RepoTestResult:
    """Configure, build and ctest a CMake repo, reporting ctest's own count."""
    result = RepoTestResult(repo=name, kind="cmake")
    start = time.time()

    cmake = shutil.which("cmake")
    if not cmake:
        return _skip(result, "cmake not installed", start)

    build_dir = _build_dir_for(path)
    cfg = [
        cmake,
        "-S",
        path,
        "-B",
        build_dir,
        "-DEOS_BUILD_TESTS=ON",
        "-DEBLDR_BUILD_TESTS=ON",
        "-DEAI_BUILD_TESTS=ON",
        "-DENI_BUILD_TESTS=ON",
    ]
    try:
        r = subprocess.run(cfg, capture_output=True, text=True, timeout=_BUILD_TIMEOUT_S)
    except (subprocess.TimeoutExpired, OSError) as e:
        result.status, result.reason = ERROR, "configure: %s" % e
        result.duration_s = time.time() - start
        return result
    if r.returncode != 0:
        output = (r.stderr or "") + (r.stdout or "")
        unmet = _unmet_toolchain(output)
        if unmet:
            # An absent vendor SDK is not a broken build. Reporting it as FAIL
            # puts it in the same column as a CMakeLists that references
            # sources which do not exist, and the two need opposite responses:
            # one is "install something", the other is "fix the repo".
            result.status, result.reason = DEPS, "needs %s" % unmet
        else:
            result.status, result.reason = FAIL, "cmake configure failed"
        result.output = output[-2000:]
        result.duration_s = time.time() - start
        return result

    try:
        r = subprocess.run(
            [cmake, "--build", build_dir, "-j", str(os.cpu_count() or 1)],
            capture_output=True,
            text=True,
            timeout=_BUILD_TIMEOUT_S,
        )
    except (subprocess.TimeoutExpired, OSError) as e:
        result.status, result.reason = ERROR, "build: %s" % e
        result.duration_s = time.time() - start
        return result
    if r.returncode != 0:
        result.status, result.reason = FAIL, "build failed"
        result.output = (r.stderr or r.stdout)[-2000:]
        result.duration_s = time.time() - start
        return result
    result.build_ok = True

    ctest = shutil.which("ctest")
    if not ctest:
        return _skip(result, "built OK; ctest not installed", start)

    try:
        r = subprocess.run(
            [ctest, "--output-on-failure", "-j", str(os.cpu_count() or 1)],
            capture_output=True,
            text=True,
            timeout=_TEST_TIMEOUT_S,
            cwd=build_dir,
        )
    except (subprocess.TimeoutExpired, OSError) as e:
        result.status, result.reason = ERROR, "ctest: %s" % e
        result.duration_s = time.time() - start
        return result

    result.output = r.stdout[-4000:]
    counted = _parse_ctest(r.stdout)
    if counted is None:
        # No summary line means ctest found no tests registered. That is not
        # a pass; the repo built but nothing was verified.
        return _skip(result, "built OK; no tests registered", start)

    result.tests_passed, result.tests_failed, result.tests_run = counted
    result.status = PASS if (r.returncode == 0 and result.tests_failed == 0) else FAIL
    result.duration_s = time.time() - start
    return result


def _parse_ctest(out: str):
    """(passed, failed, total) from ctest's summary line, or None."""
    m = re.search(r"(\d+)% tests passed,\s+(\d+) tests? failed out of (\d+)", out)
    if not m:
        return None
    failed, total = int(m.group(2)), int(m.group(3))
    return total - failed, failed, total


def test_python_repo(name: str, path: str) -> RepoTestResult:
    """Run pytest and report the counts pytest itself printed."""
    result = RepoTestResult(repo=name, kind="python")
    start = time.time()

    if not any(os.path.isdir(os.path.join(path, d)) for d in ("tests", "test")):
        return _skip(result, "no tests/ directory", start)

    # -q is deliberately not passed. A repo whose own addopts already sets it
    # would end up at -q -q, which suppresses the summary line entirely and
    # made a fully green EoStudio run look like "no summary produced".
    #
    # PYTHONPATH carries the repo root so `import <pkg>` resolves against the
    # checkout under test rather than requiring it to be pip-installed first.
    # A src/ layout puts the package under src/, not at the repo root, so
    # both are offered; whichever is not a package directory is simply inert.
    roots = [path]
    src = os.path.join(path, "src")
    if os.path.isdir(src):
        roots.insert(0, src)
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        roots + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else [])
    )
    try:
        r = subprocess.run(
            [sys.executable, "-m", "pytest", "--tb=line"],
            capture_output=True,
            text=True,
            timeout=_TEST_TIMEOUT_S,
            cwd=path,
            env=env,
        )
    except (subprocess.TimeoutExpired, OSError) as e:
        result.status, result.reason = ERROR, "pytest: %s" % e
        result.duration_s = time.time() - start
        return result

    result.build_ok = True
    result.output = (r.stdout + r.stderr)[-4000:]
    counted = _parse_pytest(result.output)

    if counted is None:
        # Exit 5 is pytest's "no tests collected"; anything else with no
        # summary line is a collection error, which must not read as a pass.
        reason = (
            "no tests collected"
            if r.returncode == 5
            else "pytest produced no summary (exit %d)" % r.returncode
        )
        if r.returncode in (0, 5):
            return _skip(result, reason, start)

        # A collection error caused by absent third-party modules is the same
        # condition DEPS already covers further down, reached earlier: pytest
        # aborts before printing any summary, so the counts never get parsed.
        # Calling it FAIL puts "pip install click" in the same column as a
        # suite that genuinely fails.
        external = _external_missing_modules(result.output, path)
        if external:
            result.status = DEPS
            result.reason = "needs %s" % ", ".join(external)
        else:
            result.status, result.reason = FAIL, reason
        result.duration_s = time.time() - start
        return result

    passed, failed, errors = counted
    result.tests_passed = passed
    result.tests_failed = failed + errors
    result.tests_run = passed + failed + errors

    missing = _missing_modules(result.output)
    if r.returncode == 0 and result.tests_failed == 0:
        result.status = PASS
    elif failed == 0 and errors and missing:
        # Nothing asserted wrongly; the suite could not be imported because
        # the repo's own dependencies are absent from this environment.
        result.status = DEPS
        result.reason = "needs %s" % ", ".join(missing)
    else:
        result.status = FAIL
        if missing:
            result.reason = "also missing %s" % ", ".join(missing)
    result.duration_s = time.time() - start
    return result


# What a CMakeLists says when an external SDK or toolchain it needs is absent.
# Deliberately narrow: it must not swallow "Cannot find source file", which
# means the repository is referencing code it does not contain.
_UNMET_TOOLCHAIN_PATTERNS = (
    re.compile(
        r"(?P<name>[A-Z][A-Z0-9_]*_(?:SDK|TOOLCHAIN|ROOT|DIR|PATH|HOME)"
        r"[A-Z0-9_]*)\s+not set"
    ),
    re.compile(r"Could NOT find (?P<name>[A-Za-z0-9_+-]+)"),
    re.compile(r"(?P<name>[A-Za-z0-9_+-]+) is required but was not found"),
)


def _unmet_toolchain(output: str):
    """The name of an absent external dependency, or None.

    Returns None when the failure is anything the repository itself owns. A
    missing source file in particular must stay a FAIL: it means the build
    description and the tree disagree, which no amount of installing fixes.
    """
    if "Cannot find source file" in output or "No SOURCES given" in output:
        return None
    for pattern in _UNMET_TOOLCHAIN_PATTERNS:
        match = pattern.search(output)
        if match:
            return match.group("name")
    return None


def _missing_modules(out: str) -> list:
    """Module names that could not be imported, deduplicated and ordered.

    Both spellings are matched. ModuleNotFoundError quotes the name, but
    `python -m pytest` on an interpreter without pytest prints the bare form
    "No module named pytest" — the case where the test runner itself is what is
    absent, which is exactly when nothing else in the output explains the
    failure.
    """
    seen = []
    for quoted, bare in re.findall(r"No module named (?:'([^']+)'|([A-Za-z_][\w.]*))", out):
        top = (quoted or bare).split(".")[0]
        if top not in seen:
            seen.append(top)
    return seen


def _external_missing_modules(out: str, repo_path: str) -> list:
    """Absent modules that the repository does not itself provide.

    A repo failing to import its own package is a real defect — the runner
    already puts the checkout on PYTHONPATH, so that import should resolve —
    and must stay a FAIL. Only third-party absences are an environment
    problem.
    """
    external = []
    for name in _missing_modules(out):
        provided = (
            os.path.isdir(os.path.join(repo_path, name))
            or os.path.isfile(os.path.join(repo_path, name + ".py"))
            or os.path.isdir(os.path.join(repo_path, "src", name))
        )
        if not provided:
            external.append(name)
    return external


def _parse_pytest(out: str):
    """(passed, failed, errors) from pytest's summary line, or None.

    failed and errors are kept apart: a failed test is a broken assertion,
    while an error is usually a collection problem -- most often an import
    of a dependency that is declared but not installed here.
    """
    if not re.search(r"\d+ (passed|failed|error)", out):
        return None

    def n(word):
        m = re.search(r"(\d+) %s" % word, out)
        return int(m.group(1)) if m else 0

    return n("passed"), n("failed"), n("error")


def test_go_repo(name: str, path: str) -> RepoTestResult:
    result = RepoTestResult(repo=name, kind="go")
    start = time.time()

    go = shutil.which("go")
    if not go:
        return _skip(result, "go not installed", start)

    try:
        r = subprocess.run(
            [go, "test", "-v", "-count=1", "./..."],
            capture_output=True,
            text=True,
            timeout=_TEST_TIMEOUT_S,
            cwd=path,
        )
    except (subprocess.TimeoutExpired, OSError) as e:
        result.status, result.reason = ERROR, "go test: %s" % e
        result.duration_s = time.time() - start
        return result

    result.build_ok = True
    result.output = r.stdout[-4000:]
    result.tests_passed = r.stdout.count("--- PASS")
    result.tests_failed = r.stdout.count("--- FAIL")
    result.tests_run = result.tests_passed + result.tests_failed
    if result.tests_run == 0:
        return _skip(result, "no Go tests found", start)
    result.status = PASS if (r.returncode == 0 and result.tests_failed == 0) else FAIL
    result.duration_s = time.time() - start
    return result


def test_node_repo(name: str, path: str) -> RepoTestResult:
    result = RepoTestResult(repo=name, kind="node")
    start = time.time()

    npm = shutil.which("npm")
    if not npm:
        return _skip(result, "npm not installed", start)
    if not os.path.isdir(os.path.join(path, "node_modules")):
        return _skip(result, "dependencies not installed (npm ci)", start)

    try:
        r = subprocess.run(
            [npm, "test", "--silent"],
            capture_output=True,
            text=True,
            timeout=_TEST_TIMEOUT_S,
            cwd=path,
        )
    except (subprocess.TimeoutExpired, OSError) as e:
        result.status, result.reason = ERROR, "npm test: %s" % e
        result.duration_s = time.time() - start
        return result

    result.build_ok = True
    result.output = (r.stdout + r.stderr)[-4000:]
    result.status = PASS if r.returncode == 0 else FAIL
    result.duration_s = time.time() - start
    return result


def test_make_repo(name: str, path: str) -> RepoTestResult:
    """Run a Makefile's own `test` target.

    Only when the Makefile actually declares one. Running `make test` against
    a Makefile without that rule fails with "No rule to make target", which
    would read as a broken repo rather than a repo that keeps its tests
    somewhere else.
    """
    result = RepoTestResult(repo=name, kind="make")
    start = time.time()

    make = shutil.which("make")
    if not make:
        return _skip(result, "make not installed", start)

    makefile = next(
        (
            os.path.join(path, n)
            for n in ("Makefile", "makefile", "GNUmakefile")
            if os.path.isfile(os.path.join(path, n))
        ),
        None,
    )
    if makefile is None:
        return _skip(result, "no Makefile", start)
    try:
        with open(makefile, encoding="utf-8", errors="replace") as fh:
            body = fh.read()
    except OSError as exc:
        return _skip(result, "cannot read the Makefile: %s" % exc, start)
    if not re.search(r"^test\s*:", body, re.MULTILINE):
        return _skip(result, "Makefile declares no 'test' target", start)

    try:
        r = subprocess.run(
            [make, "-C", path, "test"], capture_output=True, text=True, timeout=_TEST_TIMEOUT_S
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        result.status, result.reason = ERROR, "make test: %s" % exc
        result.duration_s = time.time() - start
        return result

    result.build_ok = True
    result.output = (r.stdout + r.stderr)[-4000:]
    result.status = PASS if r.returncode == 0 else FAIL
    # A Makefile reports through its exit code; there is no count to parse and
    # inventing one would be the fabrication this module exists to avoid.
    result.reason = "`make test` exit %d" % r.returncode
    result.duration_s = time.time() - start
    return result


#: Detected kind -> the runner that knows how to test it.
_RUNNERS = {
    "cmake": test_c_repo,
    "python": test_python_repo,
    "go": test_go_repo,
    "node": test_node_repo,
    "make": test_make_repo,
}


def test_repo(name: str, path: str) -> RepoTestResult:
    """Test one repo with the runner for its primary build system."""
    return test_repo_all(name, path)[0]


def test_repo_all(name: str, path: str) -> list:
    """One result per build system the repo has.

    Every detected system is exercised, so a repo cannot hide a broken native
    build behind a green Python suite.
    """
    results = []
    for kind, comp_path in detect_components(path):
        # Label a nested component by its path within the repo, so one repo
        # yielding several rows stays readable and a failure names the
        # directory that produced it.
        rel = os.path.relpath(comp_path, path)
        label = name if rel == "." else "%s/%s" % (name, rel.replace(os.sep, "/"))
        runner = _RUNNERS.get(kind)
        if runner is None:
            r = RepoTestResult(repo=label, kind=kind)
            results.append(_skip(r, "no runner for a '%s' project" % kind, time.time()))
        else:
            results.append(runner(label, comp_path))
    return results


def run_simulations(platforms: list = None) -> list:
    if not platforms:
        platforms = ["stm32f4", "raspi4", "arm64-linux", "riscv64-linux", "x86_64-linux"]
    results = []
    from eosim.engine.native import VirtualMachine

    for plat in platforms:
        try:
            vm = VirtualMachine(plat, "arm64", ram_mb=32)
            sim = vm.run(max_cycles=200, timeout_s=5)
            results.append(
                {
                    "platform": plat,
                    "success": sim["success"],
                    "cycles": sim["cycles"],
                    "duration_s": sim["duration_s"],
                }
            )
        except Exception as e:
            results.append(
                {
                    "platform": plat,
                    "success": False,
                    "cycles": 0,
                    "duration_s": 0.0,
                    "error": str(e),
                }
            )
    return results


def run_ecosystem_tests(
    workspace: str = None, simulate: bool = True, only: list = None
) -> EcosystemReport:
    """Build and test every repo in the workspace."""
    report = EcosystemReport()
    start = time.time()

    for name, path in find_repos(workspace).items():
        if only and name not in only:
            continue
        per_kind = test_repo_all(name, path)
        report.results.extend(per_kind)
        report.repos_tested += 1

        # A repo counts as failed if any of its build systems failed, and as
        # passed only if at least one actually ran and none failed.
        statuses = {r.status for r in per_kind}
        if statuses & {FAIL, ERROR}:
            report.repos_failed += 1
        elif PASS in statuses:
            report.repos_passed += 1
        else:
            report.repos_skipped += 1  # SKIP and DEPS are both "not tested"

        for r in per_kind:
            report.total_tests += r.tests_run
            report.total_passed += r.tests_passed
            if r.status == DEPS:
                report.total_blocked += r.tests_failed
            else:
                report.total_failed += r.tests_failed

    if simulate:
        report.simulations = run_simulations()

    report.duration_s = time.time() - start
    return report
