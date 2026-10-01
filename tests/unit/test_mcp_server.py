# SPDX-License-Identifier: MIT
"""Client-harness tests for the EoSim MCP server scaffold.

Covers the two shipped tools (list_platforms, sim_launch) at the domain
layer and the JSON-RPC stdio framing end to end, using a scratch platform
registry so the tests never depend on the shipped 150+ board catalog.
"""

import io
import json

import pytest
import yaml

from eosim.mcp import server as mcp_server
from eosim.mcp.server import McpServer, handle_message
from eosim.mcp.tools import call_tool, list_tools, set_platforms_dir


@pytest.fixture
def registry_dir(tmp_path):
    plat = tmp_path / "demo-arm"
    plat.mkdir()
    (plat / "platform.yml").write_text(
        yaml.safe_dump(
            {
                "name": "demo-arm",
                "display_name": "Demo ARM Board",
                "arch": "arm",
                "engine": "eosim",
                "vendor": "DemoVendor",
                "soc": "DEMO1234",
                "class": "mcu",
                "domain": "industrial",
            }
        ),
        encoding="utf-8",
    )
    plat2 = tmp_path / "demo-riscv"
    plat2.mkdir()
    (plat2 / "platform.yml").write_text(
        yaml.safe_dump(
            {
                "name": "demo-riscv",
                "display_name": "Demo RISC-V Board",
                "arch": "riscv",
                "engine": "qemu",
                "vendor": "DemoVendor",
                "soc": "DEMO5678",
                "class": "mcu",
                "domain": "automotive",
            }
        ),
        encoding="utf-8",
    )
    set_platforms_dir(tmp_path)
    yield tmp_path
    set_platforms_dir(None)  # back to packaged default


# --- tool descriptors -------------------------------------------------------


def test_tools_list_has_exactly_the_shipped_surface():
    tools = list_tools()
    names = sorted(t["name"] for t in tools)
    assert names == ["list_platforms", "sim_launch"]
    for t in tools:
        assert t["description"]
        assert t["inputSchema"]["type"] == "object"


def test_call_unknown_tool_is_an_error_dict_not_a_crash():
    res = call_tool("nope", {})
    assert res["ok"] is False
    assert "unknown tool" in res["error"]


# --- list_platforms ---------------------------------------------------------


def test_list_platforms_returns_registry(registry_dir):
    res = call_tool("list_platforms", {})
    assert res["count"] == 2
    assert res["total"] == 2
    names = sorted(p["name"] for p in res["platforms"])
    assert names == ["demo-arm", "demo-riscv"]


def test_list_platforms_filter_by_arch(registry_dir):
    res = call_tool("list_platforms", {"arch": "riscv"})
    assert res["count"] == 1
    assert res["platforms"][0]["name"] == "demo-riscv"


def test_list_platforms_respects_limit(registry_dir):
    res = call_tool("list_platforms", {"limit": 1})
    assert res["count"] == 1


# --- sim_launch -------------------------------------------------------------


def test_sim_launch_dry_run_returns_plan(registry_dir):
    res = call_tool("sim_launch", {"platform": "demo-arm"})
    assert res["ok"] is True
    assert res["dry_run"] is True
    assert res["platform"]["name"] == "demo-arm"
    assert res["command"][:3] == ["eosim", "run", "demo-arm"]
    assert "session_id" not in res  # nothing started


def test_sim_launch_unknown_platform_errors(registry_dir):
    res = call_tool("sim_launch", {"platform": "nope"})
    assert res["ok"] is False
    assert "unknown platform" in res["error"]


def test_sim_launch_missing_firmware_errors(registry_dir):
    res = call_tool(
        "sim_launch", {"platform": "demo-arm", "firmware": "/does/not/exist.elf"}
    )
    assert res["ok"] is False
    assert "firmware not found" in res["error"]


def test_sim_launch_requires_platform_arg():
    res = call_tool("sim_launch", {})
    assert res["ok"] is False
    assert "invalid arguments" in res["error"]


# --- JSON-RPC stdio framing --------------------------------------------------


def _rpc(messages):
    stdin = io.StringIO("\n".join(json.dumps(m) for m in messages) + "\n")
    stdout = io.StringIO()
    McpServer(stdin=stdin, stdout=stdout).serve_forever()
    return [json.loads(line) for line in stdout.getvalue().splitlines() if line.strip()]


def test_stdio_initialize_handshake():
    replies = _rpc(
        [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
        ]
    )
    assert len(replies) == 1  # notification gets no reply
    result = replies[0]["result"]
    assert result["protocolVersion"] == mcp_server.PROTOCOL_VERSION
    assert result["serverInfo"]["name"] == "eosim-mcp"
    assert "tools" in result["capabilities"]


def test_stdio_tools_list_and_call(registry_dir):
    replies = _rpc(
        [
            {"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": "list_platforms", "arguments": {"arch": "arm"}},
            },
        ]
    )
    tools = replies[0]["result"]["tools"]
    assert sorted(t["name"] for t in tools) == ["list_platforms", "sim_launch"]
    payload = json.loads(replies[1]["result"]["content"][0]["text"])
    assert payload["count"] == 1
    assert payload["platforms"][0]["name"] == "demo-arm"


def test_stdio_unknown_method_is_32601():
    replies = _rpc([{"jsonrpc": "2.0", "id": 9, "method": "tools/nonexistent"}])
    assert replies[0]["error"]["code"] == -32601


def test_stdio_parse_error_is_32700():
    stdin = io.StringIO("this is not json\n")
    stdout = io.StringIO()
    McpServer(stdin=stdin, stdout=stdout).serve_forever()
    reply = json.loads(stdout.getvalue().strip())
    assert reply["error"]["code"] == -32700


def test_handle_message_rejects_non_jsonrpc():
    reply = handle_message({"id": 1, "method": "tools/list"})
    assert reply["error"]["code"] == -32600
