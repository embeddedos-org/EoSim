# SPDX-License-Identifier: MIT
"""MCP stdio server for EoSim (JSON-RPC 2.0 framing, MCP spec rev 2026-07-28).

Wire protocol (newline-delimited JSON-RPC 2.0 over stdio):
  client -> {"jsonrpc":"2.0","id":1,"method":"server/discover"}
  server -> {"jsonrpc":"2.0","id":1,"result":{"supportedVersions":...,
             "capabilities":{"tools":{}},"serverInfo":{...}}}
  client -> {"jsonrpc":"2.0","id":2,"method":"tools/list"}
  client -> {"jsonrpc":"2.0","id":3,"method":"tools/call",
             "params":{"name":"list_platforms","arguments":{...}}}

Implemented methods: server/discover, tools/list, tools/call, ping.
Unknown methods return JSON-RPC -32601; bad params -32602; tool errors are
returned as a result payload with ok:false (the call itself succeeded).

Modern-only 2026-07-28 (gap G3, EoSim #66): there is no negotiation
handshake — "initialize" is a removed method and is rejected with -32601
(see handle_message). Clients learn what the server supports from
server/discover instead.

Stateless 2026-07-28: every id-bearing request must carry _meta with
io.modelcontextprotocol/protocolVersion and
io.modelcontextprotocol/clientCapabilities, else -32602 (gap G2, EoSim
#66); every result carries _meta with io.modelcontextprotocol/serverInfo
(gap G4, EoSim #66). Notifications (no id) get no reply and are not
_meta-checked.
"""

from __future__ import annotations

import json
import sys
from typing import Any

from eosim.mcp.tools import call_tool, list_tools

PROTOCOL_VERSION = "2026-07-28"
SERVER_NAME = "eosim-mcp"
SERVER_VERSION = "0.1.0"

META_PROTOCOL_VERSION_KEY = "io.modelcontextprotocol/protocolVersion"
META_CLIENT_CAPABILITIES_KEY = "io.modelcontextprotocol/clientCapabilities"
META_SERVER_INFO_KEY = "io.modelcontextprotocol/serverInfo"


def _response(msg_id: Any, result: Any) -> dict[str, Any]:
    """Success envelope; every result carries serverInfo _meta (G4)."""
    return {
        "jsonrpc": "2.0",
        "id": msg_id,
        "result": result,
        "_meta": {META_SERVER_INFO_KEY: {"name": SERVER_NAME, "version": SERVER_VERSION}},
    }


def _error(msg_id: Any, code: int, message: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": msg_id,
        "error": {"code": code, "message": message},
    }


def _handle_server_discover(msg_id: Any) -> dict[str, Any]:
    """MCP 2026-07-28 server/discover (gap G1, EoSim #66).

    Returns a DiscoverResult: the versions this server speaks plus its
    capabilities. serverInfo keeps the server.py constants (0.1.0); the
    server.json 3.1.0 discrepancy recorded in the probe findings doc is
    NOT reconciled here — that is a separate version-truth decision.
    """
    return _response(
        msg_id,
        {
            "supportedVersions": [PROTOCOL_VERSION],
            "capabilities": {"tools": {}},
            "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
        },
    )


def _handle_tools_list(msg_id: Any) -> dict[str, Any]:
    return _response(msg_id, {"tools": list_tools()})


def _handle_tools_call(msg_id: Any, params: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(params, dict) or "name" not in params:
        return _error(msg_id, -32602, "tools/call requires params.name")
    arguments = params.get("arguments", {})
    if not isinstance(arguments, dict):
        return _error(msg_id, -32602, "tools/call params.arguments must be an object")
    result = call_tool(params["name"], arguments)
    response = {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
    if result.get("ok") is False:
        response["isError"] = True
    return _response(msg_id, response)


def handle_message(msg: dict[str, Any]) -> dict[str, Any] | None:
    """Handle one JSON-RPC message; returns the reply, or None for notifications."""
    if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0":
        return _error(
            msg.get("id") if isinstance(msg, dict) else None, -32600, "invalid JSON-RPC 2.0 message"
        )
    method = msg.get("method")
    msg_id = msg.get("id")
    params = msg.get("params") or {}

    # Notifications (no id) get no reply.
    if msg_id is None:
        return None

    # Stateless 2026-07-28 (gap G2): a request missing the required _meta
    # fields is malformed and MUST be rejected with -32602.
    meta = msg.get("_meta")
    if (
        not isinstance(meta, dict)
        or META_PROTOCOL_VERSION_KEY not in meta
        or META_CLIENT_CAPABILITIES_KEY not in meta
    ):
        return _error(
            msg_id,
            -32602,
            "request _meta must carry io.modelcontextprotocol/protocolVersion "
            "and io.modelcontextprotocol/clientCapabilities",
        )

    if method == "initialize":
        # Gap G3 (EoSim #66), modern-only decision: spec 2026-07-28
        # removes the negotiation handshake ("There is no negotiation
        # handshake. Every request carries its protocol version, and the
        # server accepts or rejects each request independently"). The
        # server declares 2026-07-28 and is NOT dual-era, so initialize
        # is a removed method and is rejected as unknown (-32601), not
        # answered. Clients discover via server/discover instead.
        return _error(
            msg_id,
            -32601,
            "initialize was removed in MCP 2026-07-28 (no negotiation "
            "handshake); use server/discover",
        )
    if method == "server/discover":
        return _handle_server_discover(msg_id)
    if method == "tools/list":
        return _handle_tools_list(msg_id)
    if method == "tools/call":
        return _handle_tools_call(msg_id, params)
    if method == "ping":
        return _response(msg_id, {})
    return _error(msg_id, -32601, f"method not found: {method}")


class McpServer:
    """Line-delimited JSON-RPC 2.0 MCP server on stdin/stdout."""

    def __init__(self, stdin=None, stdout=None):
        self.stdin = stdin or sys.stdin
        self.stdout = stdout or sys.stdout

    def serve_forever(self) -> None:
        for line in self.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                self._write(_error(None, -32700, "parse error"))
                continue
            # Batch requests are not supported in the scaffold.
            if isinstance(msg, list):
                self._write(_error(None, -32600, "batch requests not supported"))
                continue
            reply = handle_message(msg)
            if reply is not None:
                self._write(reply)

    def _write(self, obj: dict[str, Any]) -> None:
        self.stdout.write(json.dumps(obj) + "\n")
        self.stdout.flush()


def main() -> None:
    """Entry point: `python -m eosim.mcp` or `eosim-mcp`."""
    McpServer().serve_forever()


if __name__ == "__main__":
    main()
