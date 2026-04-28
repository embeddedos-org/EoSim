# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""API route definitions for EoSim REST server."""


def register_routes(app, server):
    """Register all API routes on the FastAPI app."""

    @app.get("/api/v1/platforms")
    def list_platforms():
        from eosim.core.registry import PlatformRegistry
        reg = PlatformRegistry()
        reg.discover()
        return {"platforms": [p.name for p in reg.all()]}

    @app.get("/api/v1/domains")
    def list_domains():
        from eosim.core.domains import list_domains
        return {"domains": list_domains()}

    @app.get("/api/v1/simulators")
    def list_simulators():
        from eosim.engine.native.simulators import SimulatorFactory
        return {"simulators": SimulatorFactory.list_simulators()}

    @app.get("/api/v1/templates")
    def list_templates():
        from eosim.gui.product_templates import list_templates
        return {"templates": list_templates()}

    @app.get("/api/v1/simulations")
    def list_simulations():
        return {"simulations": server.list_simulations()}

    @app.get("/api/v1/simulations/{name}/state")
    def get_simulation_state(name: str):
        sim = server.get_simulation(name)
        if sim is None:
            return {"error": "Simulation not found"}
        return {"name": name, "state": sim.get_state()}

    @app.post("/api/v1/simulations/{name}/tick")
    def tick_simulation(name: str):
        sim = server.get_simulation(name)
        if sim is None:
            return {"error": "Simulation not found"}
        sim.tick()
        return {"name": name, "tick": sim.tick_count}

    @app.post("/api/v1/simulations/{name}/reset")
    def reset_simulation(name: str):
        sim = server.get_simulation(name)
        if sim is None:
            return {"error": "Simulation not found"}
        sim.reset()
        return {"name": name, "status": "reset"}
