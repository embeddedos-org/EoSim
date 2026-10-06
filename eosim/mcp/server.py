# SPDX-License-Identifier: MIT
"""MCP stdio server for EoSim (JSON-RPC 2.0 framing, MCP spec rev 2026-07-28).

Wire protocol (newline-delimited JSON-RPC 2.0 over stdio):
  client -> {"jsonrpc":"2.0","id":1,"method":"initialize","params":{...}}
  server -> {"jsonrpc":"2.0","id":1,"result":{"protocolVersion":...,
             "capabilities":{"tools":{}},"serverInfo":{...}}}
  client -> {"jsonrpc":"2.0","method":"notifications/initialized"}
  client -> {"jsonrpc":"2.0","id":2,"method":"tools/list"}
  client -> {"jsonrpc":"2.0","id":3,"method":"tools/call",
             "params":{"name":"list_platforms","arguments":{...}}}

Only the methods above are implemented (the scaffold surface). Unknown
methods return JSON-RPC -32601; bad params -32602; tool errors are returned
as a result payload with ok:false (the call itself succeeded).
"""

from __future__ import annotations

import json
import sys
from typing import Any

from eosim.mcp.tools import call_tool, list_tools

PROTOCOL_VERSION = "2026-07-28"
SERVER_NAME = "eosim-mcp"
SERVER_VERSION = "0.1.0"


def _response(msg_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": msg_id, "result": result}


def _error(msg_id: Any, code: int, message: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": msg_id,
        "error": {"code": code, "message": message},
    }


def _handle_initialize(msg_id: Any, params: dict[str, Any]) -> dict[str, Any]:
    return _response(
        msg_id,
        {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
        },
    )


def _handle_tools_list(msg_id: Any) -> dict[str, Any]:
    return _response(msg_id, {"tools": list_tools()})


def _handle_tools_call(msg_id: Any, params: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(params, dict) or "name" not in params:
        return _error(msg_id, -32602, "tools/call requires params.name")
    arguments = params.get("arguments") or {}
    if not isinstance(arguments, dict):
        return _error(msg_id, -32602, "tools/call params.arguments must be an object")
    result = call_tool(params["name"], arguments)
    return _response(
        msg_id,
        {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]},
    )


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

    if method == "initialize":
        return _handle_initialize(msg_id, params if isinstance(params, dict) else {})
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
