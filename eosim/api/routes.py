# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""Production API route definitions for EoSim REST server.

All routes return proper HTTP status codes and structured JSON responses.
"""
from __future__ import annotations

import time


def register_routes(app, server) -> None:
    """Register all production API routes on the FastAPI app."""

    # ── Health & Status ───────────────────────────────────────────────────────

    @app.get("/health", tags=["Health"], summary="Quick health probe")
    @app.get("/api/v1/health", tags=["Health"], summary="Detailed health check")
    def health():
        """Kubernetes liveness/readiness probe endpoint.
        Returns 200 OK when the service is healthy.
        """
        from eosim import __version__
        return {
            "status": "ok",
            "version": __version__,
            "platform": "eosim",
            "uptime": round(server.uptime() if hasattr(server, "uptime") else 0, 2),
            "timestamp": time.time(),
            "api": "https://api.eosim.io",
        }

    @app.get("/api/v1/version", tags=["Health"], summary="Version info")
    def version():
        from eosim import __version__, __url__, __api_url__, __docs_url__
        return {
            "version": __version__,
            "url": __url__,
            "api": __api_url__,
            "docs": __docs_url__,
        }

    # ── Platforms ─────────────────────────────────────────────────────────────

    @app.get("/api/v1/platforms", tags=["Platforms"], summary="List all simulation platforms")
    def list_platforms():
        from eosim.core.registry import PlatformRegistry
        reg = PlatformRegistry()
        reg.discover()
        platforms = [p.name for p in reg.all()]
        return {"platforms": platforms, "count": len(platforms)}

    # ── Domains ───────────────────────────────────────────────────────────────

    @app.get("/api/v1/domains", tags=["Domains"], summary="List simulation domains")
    def list_domains():
        from eosim.core.domains import list_domains as _list
        domains = _list()
        return {"domains": domains, "count": len(domains)}

    # ── Simulators ────────────────────────────────────────────────────────────

    @app.get("/api/v1/simulators", tags=["Simulators"], summary="List available simulators")
    def list_simulators():
        from eosim.engine.native.simulators import SimulatorFactory
        sims = SimulatorFactory.list_simulators()
        return {"simulators": sims, "count": len(sims)}

    # ── Templates ─────────────────────────────────────────────────────────────

    @app.get("/api/v1/templates", tags=["Templates"], summary="List simulation templates")
    def list_templates():
        from eosim.gui.product_templates import list_templates as _list
        templates = _list()
        return {"templates": templates, "count": len(templates)}

    # ── Simulations ───────────────────────────────────────────────────────────

    @app.get("/api/v1/simulations", tags=["Simulations"], summary="List active simulations")
    def list_simulations():
        sims = server.list_simulations()
        return {"simulations": sims, "count": len(sims)}

    @app.get(
        "/api/v1/simulations/{name}/state",
        tags=["Simulations"],
        summary="Get simulation state",
    )
    def get_simulation_state(name: str):
        try:
            from fastapi import HTTPException
        except ImportError:
            HTTPException = None

        sim = server.get_simulation(name)
        if sim is None:
            if HTTPException:
                raise HTTPException(
                    status_code=404,
                    detail={"error": "not_found", "message": f"Simulation '{name}' not found"},
                )
            return {"error": "Simulation not found"}
        return {"name": name, "state": sim.get_state()}

    @app.post(
        "/api/v1/simulations/{name}/tick",
        tags=["Simulations"],
        summary="Advance simulation by one tick",
    )
    def tick_simulation(name: str):
        try:
            from fastapi import HTTPException
        except ImportError:
            HTTPException = None

        sim = server.get_simulation(name)
        if sim is None:
            if HTTPException:
                raise HTTPException(
                    status_code=404,
                    detail={"error": "not_found", "message": f"Simulation '{name}' not found"},
                )
            return {"error": "Simulation not found"}
        sim.tick()
        return {"name": name, "tick": sim.tick_count, "status": "ok"}

    @app.post(
        "/api/v1/simulations/{name}/reset",
        tags=["Simulations"],
        summary="Reset simulation to initial state",
    )
    def reset_simulation(name: str):
        try:
            from fastapi import HTTPException
        except ImportError:
            HTTPException = None

        sim = server.get_simulation(name)
        if sim is None:
            if HTTPException:
                raise HTTPException(
                    status_code=404,
                    detail={"error": "not_found", "message": f"Simulation '{name}' not found"},
                )
            return {"error": "Simulation not found"}
        sim.reset()
        return {"name": name, "status": "reset", "tick": 0}

    # ── Metrics ───────────────────────────────────────────────────────────────

    @app.get("/api/v1/metrics", tags=["Metrics"], summary="Platform metrics")
    def get_metrics():
        from eosim.core.registry import PlatformRegistry
        reg = PlatformRegistry()
        reg.discover()
        return {
            "platform_count": len(reg.all()),
            "simulation_count": len(server.list_simulations()),
            "uptime": round(server.uptime() if hasattr(server, "uptime") else 0, 2),
            "api": "https://api.eosim.io",
        }
