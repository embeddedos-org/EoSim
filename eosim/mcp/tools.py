# SPDX-License-Identifier: MIT
"""MCP tool implementations for EoSim.

Each tool is a plain function returning a JSON-serializable result dict.
The server layer (server.py) handles JSON-RPC framing; this module holds
the domain logic so tools are unit-testable without stdio.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Registry access (lazy so import stays cheap and test-friendly)
# ---------------------------------------------------------------------------

_PLATFORMS_DIR: Path | None = None


def _platforms_dir() -> Path:
    """Locate the packaged platform registry (mirrors eosim.cli.main)."""
    global _PLATFORMS_DIR
    if _PLATFORMS_DIR is None:
        packaged = Path(__file__).parent.parent / "platforms"
        if packaged.is_dir():
            _PLATFORMS_DIR = packaged
        else:  # repo-root layout fallback
            _PLATFORMS_DIR = Path(__file__).parent.parent.parent / "platforms"
    return _PLATFORMS_DIR


def _load_registry():
    from eosim.core.registry import PlatformRegistry

    return PlatformRegistry(str(_platforms_dir()))


def set_platforms_dir(path: str | Path | None) -> None:
    """Override the registry location (tests). Pass None to reset to default."""
    global _PLATFORMS_DIR
    _PLATFORMS_DIR = Path(path) if path is not None else None


# ---------------------------------------------------------------------------
# Tool: list_platforms
# ---------------------------------------------------------------------------

LIST_PLATFORMS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "arch": {"type": "string", "description": "Filter by architecture (e.g. 'arm', 'riscv')"},
        "vendor": {"type": "string", "description": "Filter by vendor"},
        "engine": {"type": "string", "description": "Filter by engine (renode, qemu, eosim)"},
        "domain": {"type": "string", "description": "Filter by domain (e.g. 'automotive')"},
        "limit": {"type": "integer", "minimum": 1, "maximum": 500, "default": 100,
                  "description": "Max platforms to return"},
    },
    "additionalProperties": False,
}


def _platform_summary(p) -> dict[str, Any]:
    return {
        "name": p.name,
        "arch": p.arch,
        "engine": p.engine,
        "vendor": p.vendor,
        "class": p.platform_class,
        "soc": p.soc,
        "domain": p.domain,
        "display_name": p.display_name,
    }


def list_platforms(arch: str = "", vendor: str = "", engine: str = "",
                   domain: str = "", limit: int = 100) -> dict[str, Any]:
    """List available simulation platforms, with optional filters."""
    reg = _load_registry()
    platforms = reg.filter(
        arch=arch or None,
        vendor=vendor or None,
        engine=engine or None,
        domain=domain or None,
    )
    platforms = sorted(platforms, key=lambda p: p.name)[: max(1, min(limit, 500))]
    return {
        "count": len(platforms),
        "total": reg.count(),
        "platforms": [_platform_summary(p) for p in platforms],
    }


# ---------------------------------------------------------------------------
# Tool: sim_launch
# ---------------------------------------------------------------------------

SIM_LAUNCH_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "platform": {"type": "string", "description": "Platform name (see list_platforms)"},
        "headless": {"type": "boolean", "default": True,
                     "description": "Run headless (no GUI)"},
        "timeout": {"type": "integer", "minimum": 1, "maximum": 3600, "default": 60,
                    "description": "Timeout in seconds"},
        "firmware": {"type": "string", "description": "Path to firmware image to load (optional)"},
        "dry_run": {"type": "boolean", "default": True,
                    "description": "If true (default), validate and return the launch plan "
                                   "without starting any process"},
    },
    "required": ["platform"],
    "additionalProperties": False,
}


def sim_launch(platform: str, headless: bool = True, timeout: int = 60,
               firmware: str | None = None, dry_run: bool = True) -> dict[str, Any]:
    """Launch a simulation for a platform.

    With ``dry_run=true`` (default) this validates the platform and returns
    the exact launch plan without starting anything — safe for agents to
    probe. With ``dry_run=false`` the simulation is spawned detached via the
    ``eosim run`` CLI and a session id is returned.
    """
    reg = _load_registry()
    p = reg.get(platform)
    if p is None:
        return {"ok": False, "error": f"unknown platform: {platform!r}"}
    if firmware is not None and not os.path.isfile(firmware):
        return {"ok": False, "error": f"firmware not found: {firmware!r}"}

    log_dir = os.path.join("out", "logs")
    plan = {
        "ok": True,
        "dry_run": dry_run,
        "platform": _platform_summary(p),
        "headless": headless,
        "timeout": timeout,
        "firmware": firmware,
        "log_dir": log_dir,
        "command": ["eosim", "run", platform]
        + (["--interactive"] if not headless else [])
        + ["--timeout", str(timeout)]
        + (["--firmware", firmware] if firmware else []),
    }

    if dry_run:
        return plan

    os.makedirs(log_dir, exist_ok=True)
    session_id = uuid.uuid4().hex[:12]
    log_file = os.path.join(log_dir, f"{platform}-{session_id}.log")
    with open(log_file, "w", encoding="utf-8") as lf:
        proc = subprocess.Popen(
            [sys.executable, "-m", "eosim", "run", platform]
            + (["--interactive"] if not headless else [])
            + ["--timeout", str(timeout), "--log-dir", log_dir]
            + (["--firmware", firmware] if firmware else []),
            stdout=lf, stderr=subprocess.STDOUT, start_new_session=True,
        )
    plan["session_id"] = session_id
    plan["pid"] = proc.pid
    plan["log_file"] = log_file
    plan["started_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    return plan


# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------

TOOLS: dict[str, dict[str, Any]] = {
    "list_platforms": {
        "description": "List available EoSim simulation platforms, with optional "
                       "filters (arch, vendor, engine, domain).",
        "inputSchema": LIST_PLATFORMS_SCHEMA,
        "handler": list_platforms,
    },
    "sim_launch": {
        "description": "Launch a simulation for a platform. Dry-run by default "
                       "(validates and returns the launch plan); set dry_run=false "
                       "to actually start the simulator detached.",
        "inputSchema": SIM_LAUNCH_SCHEMA,
        "handler": sim_launch,
    },
}


def list_tools() -> list[dict[str, Any]]:
    """Return MCP tool descriptors (name, description, inputSchema)."""
    return [
        {"name": name, "description": spec["description"], "inputSchema": spec["inputSchema"]}
        for name, spec in TOOLS.items()
    ]


def call_tool(name: str, arguments: dict[str, Any] | None) -> dict[str, Any]:
    """Dispatch a tool call; returns the result dict (or an error dict)."""
    spec = TOOLS.get(name)
    if spec is None:
        return {"ok": False, "error": f"unknown tool: {name!r}"}
    try:
        result = spec["handler"](**(arguments or {}))
    except TypeError as exc:
        return {"ok": False, "error": f"invalid arguments for {name}: {exc}"}
    except Exception as exc:  # never let a tool crash the server loop
        return {"ok": False, "error": f"{name} failed: {exc}"}
    if isinstance(result, dict):
        return result
    return {"ok": True, "result": result}
