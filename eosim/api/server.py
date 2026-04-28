# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""FastAPI REST server for EoSim remote control.

Run directly:
    python -m eosim.api.server
    uvicorn eosim.api.server:app --host 0.0.0.0 --port 8080
"""
import os


class EoSimAPIServer:
    """Lightweight REST API server for EoSim simulation control.

    Requires FastAPI and uvicorn (optional dependencies).
    """

    def __init__(self, host='0.0.0.0', port=8080):
        self.host = host
        self.port = port
        self.app = None
        self._simulations = {}

    def create_app(self):
        try:
            from fastapi import FastAPI
            self.app = FastAPI(
                title="EoSim API",
                version="2.0.0",
                description="World-class embedded simulation platform REST API",
            )
            self._register_routes()
        except ImportError:
            self.app = None
        return self.app

    def _register_routes(self):
        from eosim.api.routes import register_routes
        register_routes(self.app, self)

    def run(self):
        if self.app is None:
            self.create_app()
        if self.app is None:
            raise RuntimeError("FastAPI not installed. Install with: pip install fastapi uvicorn")
        import uvicorn
        uvicorn.run(self.app, host=self.host, port=self.port)

    def add_simulation(self, name, sim):
        self._simulations[name] = sim

    def get_simulation(self, name):
        return self._simulations.get(name)

    def list_simulations(self):
        return list(self._simulations.keys())


def create_app():
    """Factory function for creating the FastAPI app (used by uvicorn)."""
    server = EoSimAPIServer()
    server.create_app()
    return server.app


# Module-level app instance for: uvicorn eosim.api.server:app
try:
    app = create_app()
except Exception:
    app = None


if __name__ == "__main__":
    server = EoSimAPIServer(
        host=os.environ.get("EOSIM_HOST", "0.0.0.0"),
        port=int(os.environ.get("EOSIM_PORT", "8080")),
    )
    server.run()
