# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""Version consistency guard (embeddedos-org/EoSim#36).

The v3.0.1 tag shipped ``pyproject.toml`` version 3.0.1 while
``eosim.__version__`` still said 2.0.0, so ``eosim --version``
disagreed with the installed package version and broke eBoot's
EoSim Sanity gate. The declared version must be a single source
of truth per release.
"""
from __future__ import annotations

import importlib.metadata
from pathlib import Path

import pytest

import eosim


def _pyproject_version() -> str:
    root = Path(__file__).resolve().parent.parent.parent
    text = (root / "pyproject.toml").read_text(encoding="utf-8")
    try:
        import tomllib

        return tomllib.loads(text)["project"]["version"]
    except ImportError:  # Python < 3.11 has no tomllib
        import re

        m = re.search(r'^version\s*=\s*"([^"]+)"', text, re.M)
        assert m, "version not found in pyproject.toml"
        return m.group(1)


def test_version_matches_pyproject():
    declared = _pyproject_version()
    assert eosim.__version__ == declared, (
        f"eosim.__version__ ({eosim.__version__}) != "
        f"pyproject version ({declared}); keep them in sync (EoSim#36)"
    )


def test_version_matches_installed_distribution():
    try:
        dist_version = importlib.metadata.version("embeddedos-eosim")
    except importlib.metadata.PackageNotFoundError:
        pytest.skip("embeddedos-eosim is not installed; nothing to compare")
    assert eosim.__version__ == dist_version, (
        f"eosim.__version__ ({eosim.__version__}) != "
        f"installed distribution version ({dist_version})"
    )
