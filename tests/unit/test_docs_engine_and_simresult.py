# SPDX-License-Identifier: MIT
"""The engine and SimResult docs must describe the code that exists.

docs/getting-started.md listed "dry-run" as an engine, in both the engine
order and the SimResult table, and documented a ``serial_output`` field;
docs/api-reference.md built a SimResult with ``serial_output=``, which raises
TypeError. There is no dry-run engine (``--dry-run`` is a flag of the QEMU
path) and the field is ``stdout``. llms-full.txt carries a copy of each doc,
so every check runs on both copies.
"""

import dataclasses
import re
from pathlib import Path

import pytest

import eosim.engine.backend as backend
from eosim.engine.backend import SimResult

ROOT = Path(__file__).resolve().parents[2]


def _llms_section(doc):
    text = (ROOT / "llms-full.txt").read_text(encoding="utf-8")
    parts = re.split(r"^# === (docs/\S+) ===\n", text, flags=re.M)
    sections = dict(zip(parts[1::2], parts[2::2]))
    return sections[doc]


def _copies(doc):
    return [
        pytest.param((ROOT / doc).read_text(encoding="utf-8"), id=doc),
        pytest.param(_llms_section(doc), id="llms-full.txt:" + doc),
    ]


def _simresult_table(text):
    section = text.split("## Understanding SimResult", 1)[1].split("\n## ", 1)[0]
    rows = {}
    for line in section.splitlines():
        m = re.match(r"\|\s*`(\w+)`\s*\|(.*)\|\s*$", line)
        if m:
            rows[m.group(1)] = m.group(2)
    return rows


def _engine_names():
    return set(
        re.findall(
            r'SimResult\(engine="([\w-]+)"', Path(backend.__file__).read_text(encoding="utf-8")
        )
    )


def test_engine_names_are_found():
    assert {"eosim", "qemu", "renode"} <= _engine_names()


@pytest.mark.parametrize("text", _copies("docs/getting-started.md"))
def test_simresult_table_matches_the_dataclass(text):
    documented = set(_simresult_table(text))
    fields = {f.name for f in dataclasses.fields(SimResult)}
    assert documented == fields, "documented but not a field: %s; field not documented: %s" % (
        sorted(documented - fields),
        sorted(fields - documented),
    )


@pytest.mark.parametrize("text", _copies("docs/getting-started.md"))
def test_documented_engines_exist(text):
    listed = set(re.findall(r"[\w-]+", _simresult_table(text)["engine"].split("(", 1)[1]))
    listed -= {"or", "a", "bridge", "engine"}
    assert listed and listed <= _engine_names(), sorted(listed - _engine_names())


@pytest.mark.parametrize("text", _copies("docs/getting-started.md"))
def test_dry_run_is_not_called_an_engine(text):
    # "--dry-run" (the QEMU flag) is fine; "dry-run" on its own as an engine is not.
    for line in text.splitlines():
        if "engine" in line.lower():
            assert "dry-run" not in line.replace("--dry-run", ""), line


@pytest.mark.parametrize("text", _copies("docs/api-reference.md"))
def test_api_reference_simresult_example_runs(text):
    section = text.split("### SimResult", 1)[1]
    code = re.search(r"```python\n(.*?)```", section, flags=re.S).group(1)
    namespace = {}
    exec(compile(code, "api-reference SimResult example", "exec"), namespace)
    assert namespace["result"].stdout == "Booting EoS...\nReady.\n"
