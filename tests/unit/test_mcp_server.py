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
from eosim.mcp.tools import _validate_schema, call_tool, list_tools, set_platforms_dir


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
    assert names == ["console_tail", "gpio_poke", "list_platforms", "net_capture", "sim_build", "sim_flash", "sim_launch", "sim_status"]
    for t in tools:
        assert t["description"]
        assert t["inputSchema"]["type"] == "object"


def test_call_unknown_tool_is_an_error_dict_not_a_crash():
    res = call_tool("nope", {})
    assert res["ok"] is False
    assert "unknown tool" in res["error"]


@pytest.mark.parametrize(
    ("tool", "arguments", "expected_error"),
    [
        (
            "sim_launch",
            {"platform": "demo-arm", "timeout": 0},
            "arguments.timeout must be at least 1",
        ),
        (
            "sim_launch",
            {"platform": "demo-arm", "timeout": 3601},
            "arguments.timeout must be at most 3600",
        ),
        (
            "sim_launch",
            {"platform": "demo-arm", "timeout": True},
            "arguments.timeout must be integer",
        ),
        (
            "sim_launch",
            {"platform": "demo-arm", "headless": "yes"},
            "arguments.headless must be boolean",
        ),
        (
            "sim_launch",
            {"platform": "demo-arm", "unexpected": 1},
            "arguments contains unknown property 'unexpected'",
        ),
        (
            "sim_flash",
            {"platform": "demo-arm", "firmware": "fw.bin", "dry_run": 1},
            "arguments.dry_run must be boolean",
        ),
        ("list_platforms", {"limit": 0}, "arguments.limit must be at least 1"),
        ("list_platforms", {"limit": 501}, "arguments.limit must be at most 500"),
        ("list_platforms", {"limit": 1.5}, "arguments.limit must be integer"),
        ("list_platforms", {"limit": False}, "arguments.limit must be integer"),
        ("list_platforms", {"limit": float("inf")}, "arguments.limit must be integer"),
        (
            "console_tail",
            {"session_id": "abc123", "lines": 0},
            "arguments.lines must be at least 1",
        ),
        (
            "console_tail",
            {"session_id": "abc123", "lines": 1001},
            "arguments.lines must be at most 1000",
        ),
        (
            "gpio_poke",
            {"session_id": "abc123", "pin": True, "value": 0},
            "arguments.pin must be integer",
        ),
        (
            "gpio_poke",
            {"session_id": "abc123", "pin": 1, "value": 3},
            "arguments.value must be at most 1",
        ),
        (
            "net_capture",
            {"session_id": "abc123", "max_packets": 0},
            "arguments.max_packets must be at least 1",
        ),
        # session_id is present, so only the unknown property can cause the rejection.
        (
            "sim_status",
            {"session_id": "abc123", "unexpected": "value"},
            "arguments contains unknown property 'unexpected'",
        ),
    ],
)
def test_call_tool_rejects_arguments_outside_published_schema(tool, arguments, expected_error):
    # The exact message proves schema validation rejected the call; a handler
    # failure (TypeError, domain error) would return a different error string.
    assert call_tool(tool, arguments) == {"ok": False, "error": expected_error}


@pytest.mark.parametrize("arguments", [[], False, 0, ""])
@pytest.mark.parametrize("tool", ["list_platforms", "sim_build"])
def test_call_tool_rejects_falsy_non_object_arguments(tool, arguments):
    # Both tools have no required arguments, so turning these into {} would
    # run the handler. They must fail the root "type": "object" check instead.
    assert call_tool(tool, arguments) == {"ok": False, "error": "arguments must be object"}


def test_call_tool_treats_missing_arguments_as_empty_object(registry_dir):
    res = call_tool("list_platforms", None)
    assert res["count"] == 2


@pytest.mark.parametrize(
    ("value", "schema", "expected"),
    [
        (200, {"type": "integer"}, None),
        (200.0, {"type": "integer"}, None),
        (200.5, {"type": "integer"}, "arguments must be integer"),
        (float("inf"), {"type": "integer"}, "arguments must be integer"),
        (float("nan"), {"type": "integer"}, "arguments must be integer"),
        (True, {"type": "integer"}, "arguments must be integer"),
        (False, {"type": "integer"}, "arguments must be integer"),
        (2.5, {"type": "number"}, None),
        (True, {"type": "number"}, "arguments must be number"),
        (False, {"type": "number"}, "arguments must be number"),
    ],
)
def test_validate_schema_integer_and_number_types(value, schema, expected):
    assert _validate_schema(value, schema) == expected


def test_whole_float_integer_arguments_reach_handlers_as_int(registry_dir, tmp_path):
    # list_platforms slices with limit; 1.0 would raise TypeError if passed on as a float.
    res = call_tool("list_platforms", {"limit": 1.0})
    assert res["count"] == 1

    # sim_launch puts timeout on the CLI; it must read "60", not "60.0".
    res = call_tool("sim_launch", {"platform": "demo-arm", "timeout": 60.0})
    assert res["ok"] is True
    assert res["timeout"] == 60 and type(res["timeout"]) is int
    assert res["command"][res["command"].index("--timeout") + 1] == "60"

    # console_tail slices with lines.
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    (log_dir / "demo-arm-abc123.log").write_text("a\nb\nc\n", encoding="utf-8")
    res = call_tool("console_tail", {"session_id": "abc123", "lines": 2.0, "log_dir": str(log_dir)})
    assert res["ok"] is True
    assert res["lines"] == ["b", "c"]

    # gpio_poke checks isinstance(pin, int) before the session lookup, so
    # reaching "no session" shows 4.0 and 1.0 arrived as int.
    res = call_tool(
        "gpio_poke", {"session_id": "nope99", "pin": 4.0, "value": 1.0, "log_dir": str(tmp_path)}
    )
    assert res["ok"] is False
    assert "no session" in res["error"]

    # The reviewer's example: net_capture with max_packets 200.0.
    pcap = _sample_pcap(tmp_path)
    res = call_tool(
        "net_capture", {"session_id": "abc123", "pcap_path": str(pcap), "max_packets": 200.0}
    )
    assert res["ok"] is True
    assert res["max_packets"] == 200 and type(res["max_packets"]) is int


def test_call_tool_does_not_mutate_caller_arguments(registry_dir):
    arguments = {"limit": 1.0}
    call_tool("list_platforms", arguments)
    assert arguments == {"limit": 1.0} and type(arguments["limit"]) is float


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
    assert "platform is required" in res["error"]


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
    assert sorted(t["name"] for t in tools) == ["console_tail", "gpio_poke", "list_platforms", "net_capture", "sim_build", "sim_flash", "sim_launch", "sim_status"]
    payload = json.loads(replies[1]["result"]["content"][0]["text"])
    assert payload["count"] == 1
    assert payload["platforms"][0]["name"] == "demo-arm"


def test_tools_call_rejects_non_object_arguments():
    reply = handle_message(
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
         "params": {"name": "list_platforms", "arguments": []}}
    )
    assert reply["error"]["code"] == -32602


def test_tools_call_marks_domain_errors_as_mcp_tool_errors(registry_dir):
    # A known tool whose arguments pass the schema, so its handler runs and
    # itself returns ok: false. The error text shows it came from the handler.
    reply = handle_message(
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {"name": "sim_launch", "arguments": {"platform": "nope"}},
        }
    )
    payload = json.loads(reply["result"]["content"][0]["text"])
    assert payload == {"ok": False, "error": "unknown platform: 'nope'"}
    assert reply["result"]["isError"] is True


@pytest.mark.parametrize(
    ("name", "arguments"),
    [
        ("unknown_tool", {}),  # unknown tool name
        ("list_platforms", {"limit": 0}),  # rejected by the published schema
    ],
)
def test_tools_call_marks_dispatch_errors_as_mcp_tool_errors(name, arguments):
    reply = handle_message(
        {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        }
    )
    assert reply["result"]["isError"] is True


def test_tools_call_success_is_not_marked_as_error(registry_dir):
    reply = handle_message(
        {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "tools/call",
            "params": {"name": "list_platforms", "arguments": {}},
        }
    )
    assert "isError" not in reply["result"]
    assert json.loads(reply["result"]["content"][0]["text"])["count"] == 2


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


# --- sim_flash ---------------------------------------------------------------


def test_sim_flash_dry_run_returns_plan(registry_dir, tmp_path):
    fw = tmp_path / "firmware.bin"
    fw.write_bytes(b"\x00\x01\x02\x03")
    res = call_tool("sim_flash", {"platform": "demo-arm", "firmware": str(fw)})
    assert res["ok"] is True
    assert res["dry_run"] is True
    assert res["size"] == 4
    assert len(res["sha256"]) == 64
    assert res["staged_path"].endswith("firmware.bin")
    # nothing written
    assert not (tmp_path / "out").exists()


def test_sim_flash_unknown_platform_errors(tmp_path):
    fw = tmp_path / "firmware.bin"
    fw.write_bytes(b"\x00")
    res = call_tool("sim_flash", {"platform": "nope", "firmware": str(fw)})
    assert res["ok"] is False
    assert "unknown platform" in res["error"]


def test_sim_flash_missing_firmware_errors(registry_dir):
    res = call_tool(
        "sim_flash", {"platform": "demo-arm", "firmware": "/nonexistent/fw.bin"}
    )
    assert res["ok"] is False
    assert "firmware not found" in res["error"]


def test_sim_flash_requires_firmware_arg():
    res = call_tool("sim_flash", {"platform": "demo-arm"})
    assert res["ok"] is False  # missing required arg -> handler TypeError


# --- console_tail ------------------------------------------------------------


def test_console_tail_reads_session_log(tmp_path):
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    lines = ["line%d" % i for i in range(10)]
    (log_dir / "demo-arm-abc123.log").write_text(
        "\n".join(lines), encoding="utf-8"
    )
    res = call_tool(
        "console_tail",
        {"session_id": "abc123", "lines": 3, "log_dir": str(log_dir)},
    )
    assert res["ok"] is True
    assert res["total_lines"] == 10
    assert res["truncated"] is True
    assert res["lines"] == ["line7", "line8", "line9"]


def test_console_tail_unknown_session_errors(tmp_path):
    res = call_tool(
        "console_tail", {"session_id": "zzz", "log_dir": str(tmp_path)}
    )
    assert res["ok"] is False
    assert "no log found" in res["error"]


def test_console_tail_rejects_bad_session_id(tmp_path):
    res = call_tool(
        "console_tail", {"session_id": "../../etc", "log_dir": str(tmp_path)}
    )
    assert res["ok"] is False
    assert "invalid session_id" in res["error"]


# --- sim_status --------------------------------------------------------------


def _write_session(tmp_path, session_id, pid, platform="demo-arm"):
    import time as _time

    log_dir = tmp_path / "logs"
    log_dir.mkdir(exist_ok=True)
    (log_dir / f"{platform}-{session_id}.log").write_text("boot ok\n", encoding="utf-8")
    (log_dir / f"{platform}-{session_id}.session.json").write_text(
        json.dumps(
            {
                "session_id": session_id,
                "pid": pid,
                "platform": platform,
                "log_file": str(log_dir / f"{platform}-{session_id}.log"),
                "started_at": "2026-10-12T00:00:00Z",
                "started_epoch": _time.time(),
            }
        ),
        encoding="utf-8",
    )
    return str(log_dir)


def test_sim_status_running_process(tmp_path):
    import subprocess
    import sys as _sys

    proc = subprocess.Popen([_sys.executable, "-c", "import time; time.sleep(30)"])
    try:
        log_dir = _write_session(tmp_path, "run123", proc.pid)
        res = call_tool("sim_status", {"session_id": "run123", "log_dir": log_dir})
        assert res["ok"] is True
        assert res["state"] == "running"
        assert res["pid"] == proc.pid
        assert res["platform"] == "demo-arm"
        assert res["uptime_seconds"] >= 0
    finally:
        proc.terminate()
        proc.wait(timeout=5)


def test_sim_status_exited_process(tmp_path):
    import subprocess
    import sys as _sys

    proc = subprocess.Popen([_sys.executable, "-c", "pass"])
    proc.wait(timeout=5)
    log_dir = _write_session(tmp_path, "done456", proc.pid)
    res = call_tool("sim_status", {"session_id": "done456", "log_dir": log_dir})
    assert res["ok"] is True
    assert res["state"] == "exited"


def test_sim_status_unknown_session_errors(tmp_path):
    res = call_tool("sim_status", {"session_id": "nope99", "log_dir": str(tmp_path)})
    assert res["ok"] is False
    assert "no session" in res["error"]


def test_sim_status_log_only_session_is_unknown_not_fabricated(tmp_path):
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    (log_dir / "demo-arm-old789.log").write_text("old boot\n", encoding="utf-8")
    res = call_tool("sim_status", {"session_id": "old789", "log_dir": str(log_dir)})
    assert res["ok"] is True
    assert res["state"] == "unknown"



# --- gpio_poke ---------------------------------------------------------------


def test_gpio_poke_dry_run_plans_without_writing(tmp_path):
    import os as _os
    import subprocess
    import sys as _sys

    proc = subprocess.Popen([_sys.executable, "-c", "import time; time.sleep(30)"])
    try:
        log_dir = _write_session(tmp_path, "poke1", proc.pid)
        res = call_tool(
            "gpio_poke", {"session_id": "poke1", "pin": 4, "value": 1, "log_dir": log_dir}
        )
        assert res["ok"] is True
        assert res["dry_run"] is True
        assert res["pin"] == 4 and res["value"] == 1
        assert res["control_file"].endswith("demo-arm-poke1.gpio.jsonl")
        assert not _os.path.exists(res["control_file"])
    finally:
        proc.terminate()
        proc.wait(timeout=5)


def test_gpio_poke_appends_event_for_running_session(tmp_path):
    import subprocess
    import sys as _sys

    proc = subprocess.Popen([_sys.executable, "-c", "import time; time.sleep(30)"])
    try:
        log_dir = _write_session(tmp_path, "poke2", proc.pid)
        res = call_tool(
            "gpio_poke",
            {"session_id": "poke2", "pin": 17, "value": 0, "log_dir": log_dir, "dry_run": False},
        )
        assert res["ok"] is True
        assert res["dry_run"] is False
        lines = open(res["control_file"], encoding="utf-8").read().strip().splitlines()
        assert len(lines) == 1
        event = json.loads(lines[0])
        assert event["pin"] == 17 and event["value"] == 0
    finally:
        proc.terminate()
        proc.wait(timeout=5)


def test_gpio_poke_exited_session_fails_closed(tmp_path):
    import subprocess
    import sys as _sys

    proc = subprocess.Popen([_sys.executable, "-c", "pass"])
    proc.wait(timeout=5)
    log_dir = _write_session(tmp_path, "poke3", proc.pid)
    res = call_tool(
        "gpio_poke",
        {"session_id": "poke3", "pin": 1, "value": 1, "log_dir": log_dir, "dry_run": False},
    )
    assert res["ok"] is False
    assert "not running" in res["error"]


def test_gpio_poke_unknown_session_errors(tmp_path):
    res = call_tool(
        "gpio_poke", {"session_id": "nope99", "pin": 1, "value": 1, "log_dir": str(tmp_path)}
    )
    assert res["ok"] is False
    assert "no session" in res["error"]


def test_gpio_poke_rejects_bad_pin_and_value(tmp_path):
    res = call_tool("gpio_poke", {"session_id": "poke1", "pin": 300, "value": 1})
    assert res["ok"] is False and "pin" in res["error"]
    res = call_tool("gpio_poke", {"session_id": "poke1", "pin": 1, "value": 2})
    assert res["ok"] is False and "value" in res["error"]
    res = call_tool("gpio_poke", {"session_id": "bad id!", "pin": 1, "value": 1})
    assert res["ok"] is False and "session_id" in res["error"]


# --- net_capture -------------------------------------------------------------


def _eth_ip_packet(src_ip, dst_ip, proto_num, l4, payload=b""):
    import struct as _s

    src = bytes(int(x) for x in src_ip.split("."))
    dst = bytes(int(x) for x in dst_ip.split("."))
    total_len = 20 + len(l4) + len(payload)
    ip = _s.pack(">BBHHHBBH", 0x45, 0, total_len, 1, 0, 64, proto_num, 0) + src + dst
    eth = bytes.fromhex("001122334455") + bytes.fromhex("66778899aabb") + _s.pack(">H", 0x0800)
    return eth + ip + l4 + payload


def _tcp_packet(src_ip, dst_ip, sport, dport, flags=0x02):
    import struct as _s

    tcp = _s.pack(">HHIIBBHHH", sport, dport, 1, 0, 0x50, flags, 8192, 0, 0)
    return _eth_ip_packet(src_ip, dst_ip, 6, tcp, payload=b"PAYLOADBYTES")


def _udp_packet(src_ip, dst_ip, sport, dport):
    import struct as _s

    udp = _s.pack(">HHHH", sport, dport, 8, 0)
    return _eth_ip_packet(src_ip, dst_ip, 17, udp, payload=b"PAYLOADBYTES")


def _write_pcap(path, packets):
    import struct as _s

    out = [_s.pack("<IHHIIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 1)]
    for i, pkt in enumerate(packets):
        out.append(_s.pack("<IIII", 1_700_000_000 + i, 500_000, len(pkt), len(pkt)))
        out.append(pkt)
    path.write_bytes(b"".join(out))
    return path


def _sample_pcap(tmp_path):
    packets = [
        _tcp_packet("10.0.0.1", "10.0.0.2", 1234, 80, flags=0x02),
        _udp_packet("10.0.0.1", "8.8.8.8", 5353, 53),
        _tcp_packet("10.0.0.2", "10.0.0.1", 80, 1234, flags=0x12),
    ]
    return _write_pcap(tmp_path / "capture.pcap", packets)


def test_net_capture_summarizes_synthetic_pcap(tmp_path):
    pcap = _sample_pcap(tmp_path)
    res = call_tool(
        "net_capture", {"session_id": "abc123", "pcap_path": str(pcap)}
    )
    assert res["ok"] is True
    assert res["packet_count"] == 3
    assert res["protocol_histogram"] == {"TCP": 2, "UDP": 1}
    assert len(res["packets"]) == 3
    assert res["first_timestamp"] == 1_700_000_000.5
    assert res["last_timestamp"] == 1_700_000_002.5
    talkers = {(t["src"], t["dst"]): t["count"] for t in res["top_talkers"]}
    assert talkers[("10.0.0.1:1234", "10.0.0.2:80")] == 1
    assert talkers[("10.0.0.1:5353", "8.8.8.8:53")] == 1
    # Headers/summary only: payload bytes never appear in the output.
    assert "PAYLOADBYTES" not in json.dumps(res)


def test_net_capture_clamps_max_packets(tmp_path):
    pcap = _sample_pcap(tmp_path)
    res = call_tool(
        "net_capture",
        {"session_id": "abc123", "pcap_path": str(pcap), "max_packets": 1000},
    )
    assert res["ok"] is True
    assert res["max_packets"] == 1000  # server-side cap
    assert len(res["packets"]) == 3

    res = call_tool(
        "net_capture",
        {"session_id": "abc123", "pcap_path": str(pcap), "max_packets": 2},
    )
    assert res["ok"] is True
    assert len(res["packets"]) == 2
    assert res["packet_count"] == 3  # exact total despite the summary cap
    assert res["truncated"] is True
    assert res["protocol_histogram"] == {"TCP": 2, "UDP": 1}


def test_net_capture_missing_file_fails_closed(tmp_path):
    res = call_tool(
        "net_capture",
        {"session_id": "abc123", "pcap_path": str(tmp_path / "nope.pcap")},
    )
    assert res["ok"] is False
    assert "not found" in res["error"]


def test_net_capture_rejects_non_pcap(tmp_path):
    bad = tmp_path / "not-a-pcap.pcap"
    bad.write_text("this is not a pcap file at all", encoding="utf-8")
    res = call_tool(
        "net_capture", {"session_id": "abc123", "pcap_path": str(bad)}
    )
    assert res["ok"] is False
    assert "pcap" in res["error"]


def test_net_capture_finds_session_pcap_in_log_dir(tmp_path):
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    _write_pcap(
        log_dir / "demo-arm-cap123.pcap",
        [_udp_packet("10.0.0.1", "8.8.8.8", 5353, 53)],
    )
    res = call_tool(
        "net_capture", {"session_id": "cap123", "log_dir": str(log_dir)}
    )
    assert res["ok"] is True
    assert res["packet_count"] == 1


def test_net_capture_is_read_only_hint():
    tools = {t["name"]: t for t in list_tools()}
    assert tools["net_capture"]["annotations"] == {"readOnlyHint": True}


# --- sim_build ---------------------------------------------------------------


def test_sim_build_dry_run_returns_plan_without_building(tmp_path, monkeypatch):
    import eosim.integrations.eos_runner as runner

    def _boom(src):  # pragma: no cover - must never be called in dry-run
        raise AssertionError("build_eos called during a dry run")

    monkeypatch.setattr(runner, "build_eos", _boom)
    res = call_tool("sim_build", {"source": str(tmp_path)})
    assert res["ok"] is True
    assert res["dry_run"] is True
    assert res["source"] == str(tmp_path)
    assert res["command"] == ["eosim", "eos", "build", "--source", str(tmp_path)]


def test_sim_build_missing_source_errors(tmp_path, monkeypatch):
    import eosim.integrations.eos_runner as runner

    monkeypatch.setattr(runner, "find_eos_source", lambda: None)
    res = call_tool("sim_build", {})
    assert res["ok"] is False
    assert "source not found" in res["error"]


def test_sim_build_rejects_non_directory_source(tmp_path):
    res = call_tool("sim_build", {"source": str(tmp_path / "does-not-exist")})
    assert res["ok"] is False
    assert "not a directory" in res["error"]


def test_sim_build_real_run_returns_log_tail(tmp_path, monkeypatch):
    import eosim.integrations.eos_runner as runner

    monkeypatch.setattr(runner, "build_eos", lambda src: (True, "BUILD: PASSED"))
    res = call_tool("sim_build", {"source": str(tmp_path), "dry_run": False})
    assert res["ok"] is True
    assert res["dry_run"] is False
    assert res["log_tail"] == "BUILD: PASSED"


def test_sim_build_failure_log_is_bounded(tmp_path, monkeypatch):
    import eosim.integrations.eos_runner as runner

    monkeypatch.setattr(runner, "build_eos", lambda src: (False, "x" * 10000))
    res = call_tool("sim_build", {"source": str(tmp_path), "dry_run": False})
    assert res["ok"] is False
    assert len(res["log_tail"]) == 2000
