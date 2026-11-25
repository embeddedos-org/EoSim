# SPDX-License-Identifier: MIT
"""EoSim MCP server — Model Context Protocol tool surface for simulations.

Exposes EoSim's platform registry and simulation launch as MCP tools over
JSON-RPC 2.0 on stdio, per the MCP spec (rev 2026-07-28). This lets coding
agents drive simulations directly: list platforms, launch a sim, and (soon)
poke peripherals — verifying against ground truth instead of hallucinating.

Shipped tools: ``list_platforms``, ``sim_launch``.
Roadmap: ``sim_build``, ``sim_flash``, ``console_tail``, ``gpio_poke``,
``i2c_poke``, ``spi_poke``.
"""

from eosim.mcp.server import McpServer, main
from eosim.mcp.tools import TOOLS, call_tool, list_tools

__all__ = ["McpServer", "main", "TOOLS", "call_tool", "list_tools"]
