# SPDX-License-Identifier: MIT
"""REST routes exercised through FastAPI's TestClient.

Regression: /api/v1/platforms and /api/v1/metrics called
``PlatformRegistry().discover()``, a method the registry does not have, so both
endpoints always returned 500.

fastapi and httpx come from the optional ``[api]`` extra; without them these
tests are skipped.
"""

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from eosim.api.server import EoSimAPIServer  # noqa: E402
from eosim.cli import main as cli_main  # noqa: E402
from eosim.core.registry import PlatformRegistry  # noqa: E402


@pytest.fixture
def client():
    server = EoSimAPIServer()
    server.add_simulation("sim-a", object())
    return TestClient(server.create_app())


def test_platforms_lists_packaged_registry(client):
    expected = sorted(p.name for p in PlatformRegistry(str(cli_main.PLATFORMS_DIR)).all())
    assert expected, "packaged platform registry is empty"

    res = client.get("/api/v1/platforms")

    assert res.status_code == 200
    body = res.json()
    assert sorted(body["platforms"]) == expected
    assert body["count"] == len(expected)
    assert "esp32" in body["platforms"]


def test_metrics_counts_platforms_and_simulations(client):
    expected = PlatformRegistry(str(cli_main.PLATFORMS_DIR)).count()

    res = client.get("/api/v1/metrics")

    assert res.status_code == 200
    body = res.json()
    assert body["platform_count"] == expected
    assert body["simulation_count"] == 1
