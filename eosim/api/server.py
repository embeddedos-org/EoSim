# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""Production FastAPI REST server for EoSim.

Run directly:
    python -m eosim.api.server
    uvicorn eosim.api.server:app --host 0.0.0.0 --port 8080 --workers 4

Production deployment:
    gunicorn eosim.api.server:app -k uvicorn.workers.UvicornWorker -w 4
"""
from __future__ import annotations

import os
import time
import logging
from typing import Any

logger = logging.getLogger(__name__)


class EoSimAPIServer:
    """Production REST API server for EoSim simulation control.

    Features:
    - Full CORS support for production domains
    - Structured JSON error responses with proper HTTP status codes
    - Health check endpoints (/health, /api/v1/health)
    - Request ID + response-time headers
    - Gzip compression
    - OpenAPI / Swagger UI at /docs, ReDoc at /redoc
    - Multi-region server definitions
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 8080, workers: int = 1) -> None:
        self.host = host
        self.port = port
        self.workers = workers
        self.app = None
        self._simulations: dict[str, Any] = {}
        self._start_time = time.time()

    def create_app(self):
        """Create and configure the FastAPI application."""
        try:
            from fastapi import FastAPI
            from fastapi.middleware.cors import CORSMiddleware
            from fastapi.middleware.gzip import GZipMiddleware
        except ImportError as exc:
            raise RuntimeError(
                "FastAPI not installed. Install with: pip install 'eosim[api]'"
            ) from exc

        from eosim import __version__

        self.app = FastAPI(
            title="EoSim API",
            version=__version__,
            description=(
                "World's most powerful universal simulation platform REST API. "
                "Supersedes 250+ industry tools across 20 simulation domains."
            ),
            contact={
                "name": "EoS Project",
                "url": "https://github.com/embeddedos-org/EoSim",
                "email": "team@embeddedos.org",
            },
            license_info={"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
            docs_url="/docs",
            redoc_url="/redoc",
            openapi_url="/openapi.json",
            servers=[
                {"url": "https://api.eosim.io", "description": "Production"},
                {"url": "https://eu.api.eosim.io", "description": "EU Region"},
                {"url": "https://ap.api.eosim.io", "description": "Asia-Pacific Region"},
                {"url": "http://localhost:8080", "description": "Local Development"},
            ],
        )

        # CORS — allow production domains + localhost for dev
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=[
                "https://app.eosim.io",
                "https://eosim.io",
                "https://docs.eosim.io",
                "https://embeddedos-org.github.io",
                "http://localhost:3000",
                "http://localhost:5173",
                "http://localhost:8080",
            ],
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["*"],
            expose_headers=["X-Request-ID", "X-EoSim-Version", "X-Response-Time"],
        )

        # Gzip responses > 1 KB
        self.app.add_middleware(GZipMiddleware, minimum_size=1024)

        # Request-ID + timing headers
        try:
            import uuid
            from starlette.middleware.base import BaseHTTPMiddleware
            from starlette.requests import Request as _Req

            _ver = __version__

            class _MetaMW(BaseHTTPMiddleware):
                async def dispatch(self, request: _Req, call_next):
                    rid = str(uuid.uuid4())[:8]
                    t0 = time.perf_counter()
                    resp = await call_next(request)
                    resp.headers["X-Request-ID"] = rid
                    resp.headers["X-Response-Time"] = f"{(time.perf_counter()-t0)*1000:.1f}ms"
                    resp.headers["X-EoSim-Version"] = _ver
                    return resp

            self.app.add_middleware(_MetaMW)
        except Exception:
            pass

        self._register_routes()
        logger.info("EoSim API server v%s ready", __version__)
        return self.app

    def _register_routes(self) -> None:
        from eosim.api.routes import register_routes
        register_routes(self.app, self)

    def run(self) -> None:
        """Start the uvicorn server."""
        if self.app is None:
            self.create_app()
        try:
            import uvicorn
        except ImportError as exc:
            raise RuntimeError(
                "uvicorn not installed. Install with: pip install 'eosim[api]'"
            ) from exc
        uvicorn.run(
            self.app,
            host=self.host,
            port=self.port,
            workers=self.workers,
            log_level=os.environ.get("EOSIM_LOG_LEVEL", "info").lower(),
            access_log=True,
            proxy_headers=True,
            forwarded_allow_ips="*",
        )

    def add_simulation(self, name: str, sim: Any) -> None:
        self._simulations[name] = sim

    def get_simulation(self, name: str) -> Any | None:
        return self._simulations.get(name)

    def list_simulations(self) -> list[str]:
        return list(self._simulations.keys())

    def uptime(self) -> float:
        return time.time() - self._start_time


def create_app():
    """Factory function for ASGI servers (uvicorn, gunicorn)."""
    server = EoSimAPIServer(
        host=os.environ.get("EOSIM_HOST", "0.0.0.0"),
        port=int(os.environ.get("EOSIM_PORT", "8080")),
        workers=int(os.environ.get("EOSIM_WORKERS", "1")),
    )
    return server.create_app()


# Module-level app for: uvicorn eosim.api.server:app
try:
    app = create_app()
except Exception:
    app = None


if __name__ == "__main__":
    _server = EoSimAPIServer(
        host=os.environ.get("EOSIM_HOST", "0.0.0.0"),
        port=int(os.environ.get("EOSIM_PORT", "8080")),
    )
    _server.run()
