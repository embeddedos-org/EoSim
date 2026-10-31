# SPDX-License-Identifier: MIT
"""Static checks on the release Docker build.

The v3.0.2 release never reached GitHub Releases or PyPI because the image
build failed: the Dockerfile copied ``platforms/`` from the repository root
after the registry moved to ``eosim/platforms``, and buildx stopped with
``"/platforms": not found``. Docker is not available in the unit test run,
so these tests check the inputs the build depends on.
"""

import re
import shlex
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def _build_context_copy_sources():
    """Sources of every COPY that reads from the build context (not --from)."""
    sources = []
    for line in (ROOT / "Dockerfile").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line.upper().startswith("COPY "):
            continue
        args = shlex.split(line)[1:]
        if any(a.startswith("--from=") for a in args):
            continue
        args = [a for a in args if not a.startswith("--")]
        sources.extend(args[:-1])
    return sources


def _dockerignore_patterns():
    path = ROOT / ".dockerignore"
    if not path.exists():
        return []
    patterns = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            patterns.append(line.rstrip("/"))
    return patterns


def test_dockerfile_copy_sources_exist_in_build_context():
    sources = _build_context_copy_sources()
    assert sources, "no COPY instructions parsed from Dockerfile"
    ignored = _dockerignore_patterns()
    for src in sources:
        assert (ROOT / src).exists(), f"Dockerfile copies {src!r}, which is not in the repository"
        top = src.rstrip("/").split("/")[0]
        assert top not in ignored, f"Dockerfile copies {src!r}, which .dockerignore excludes"


def test_release_smoke_test_overrides_eosim_entrypoint():
    # The image's ENTRYPOINT is ["eosim"], so `docker run IMAGE python -c ...`
    # would run `eosim python -c ...` and fail the release job.
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert re.search(r'^ENTRYPOINT \["eosim"\]', dockerfile, re.M)

    workflow = yaml.safe_load(
        (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    )
    steps = workflow["jobs"]["docker"]["steps"]
    smoke = next(s for s in steps if s.get("name") == "Smoke test pushed image")
    run_lines = " ".join(smoke["run"].replace("\\\n", " ").split())
    docker_runs = [c for c in run_lines.split("docker ") if c.startswith("run ")]
    assert docker_runs
    for cmd in docker_runs:
        if " python" in cmd or "-c " in cmd:
            assert "--entrypoint python" in cmd, cmd
