# SPDX-License-Identifier: MIT
"""Protocol-level tests for the QEMU/OpenOCD bridge clients.

The GDB RSP and QMP clients are exercised against an in-memory socket so the
exact bytes sent on the wire and the parsing of server replies can be checked
without launching an emulator.
"""

import json
import logging
import socket
import struct
import threading
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from eosim.engine.qemu import gdb_client as gdb_mod
from eosim.engine.qemu import qmp_client as qmp_mod
from eosim.engine.qemu.elf_loader import parse_elf, parse_elf_bytes
from eosim.engine.qemu.gdb_client import GDBError, GDBRemoteClient
from eosim.engine.qemu.qmp_client import QMPClient, QMPError
from eosim.engine.qemu.state_bridge import TargetStateBridge


class FakeSocket:
    """Byte-stream socket double: replies come from a queue of chunks."""

    def __init__(self, *chunks: bytes):
        self.chunks = [bytes(c) for c in chunks]
        self.sent: list[bytes] = []
        self.timeout = None
        self.address = None
        self.closed = False
        self.shutdown_calls = []

    def feed(self, *chunks: bytes):
        self.chunks.extend(bytes(c) for c in chunks)

    def settimeout(self, t):
        self.timeout = t

    def connect(self, addr):
        self.address = addr

    def sendall(self, data):
        self.sent.append(bytes(data))

    def recv(self, n):
        if not self.chunks:
            return b""
        head = self.chunks[0]
        out, rest = head[:n], head[n:]
        if rest:
            self.chunks[0] = rest
        else:
            self.chunks.pop(0)
        return out

    def shutdown(self, how):
        self.shutdown_calls.append(how)

    def close(self):
        self.closed = True


def socket_module_for(sock):
    return SimpleNamespace(
        socket=lambda *args: sock,
        AF_INET=socket.AF_INET,
        AF_UNIX=getattr(socket, "AF_UNIX", None),
        SOCK_STREAM=socket.SOCK_STREAM,
        SHUT_RDWR=socket.SHUT_RDWR,
        timeout=socket.timeout,
    )


def rsp(payload: str) -> bytes:
    checksum = sum(payload.encode("ascii")) % 256
    return f"${payload}#{checksum:02x}".encode("ascii")


def le_hex(value: int, size: int) -> str:
    return value.to_bytes(size, "little").hex()


@pytest.fixture
def gdb():
    client = GDBRemoteClient(arch="arm")
    client._sock = FakeSocket()
    client._connected = True
    client._no_ack_mode = True
    return client


# --- GDB Remote Serial Protocol -------------------------------------------


class TestGDBFraming:
    def test_checksum_matches_rsp_spec(self):
        assert GDBRemoteClient._checksum("OK") == 0x9A
        assert GDBRemoteClient._checksum("") == 0

    def test_send_packet_framing(self, gdb):
        gdb._send_packet("g")
        assert gdb._sock.sent == [b"$g#67"]

    def test_recv_skips_acks_and_strips_checksum(self, gdb):
        gdb._sock.feed(b"++" + rsp("S05"))
        assert gdb._recv_packet() == "S05"
        assert gdb._sock.sent == []  # no-ack mode: nothing echoed

    def test_recv_acknowledges_in_ack_mode(self, gdb):
        gdb._no_ack_mode = False
        gdb._sock.feed(rsp("OK"))
        assert gdb._recv_packet() == "OK"
        assert gdb._sock.sent == [b"+"]

    def test_connection_closed_before_packet(self, gdb):
        with pytest.raises(GDBError, match="Connection closed"):
            gdb._recv_packet()

    def test_connection_closed_mid_packet(self, gdb):
        gdb._sock.feed(b"$partial")
        with pytest.raises(GDBError, match="Connection closed"):
            gdb._recv_packet()


class TestGDBConnect:
    def _connect(self, monkeypatch, *server_bytes):
        sock = FakeSocket(*server_bytes)
        monkeypatch.setattr(gdb_mod, "socket", socket_module_for(sock))
        client = GDBRemoteClient()
        client.connect(host="127.0.0.1", port=3333, timeout=2.5)
        return client, sock

    def test_negotiates_no_ack_mode(self, monkeypatch):
        client, sock = self._connect(monkeypatch, b"+" + rsp("OK"))
        assert client.connected is True
        assert client._no_ack_mode is True
        assert sock.address == ("127.0.0.1", 3333)
        assert sock.timeout == 2.5
        assert sock.sent == [rsp("QStartNoAckMode"), b"+"]

    def test_unsupported_no_ack_mode_keeps_acks(self, monkeypatch):
        client, _ = self._connect(monkeypatch, rsp(""))
        assert client.connected is True
        assert client._no_ack_mode is False

    def test_negotiation_failure_is_tolerated(self, monkeypatch):
        client, _ = self._connect(monkeypatch)  # server closes immediately
        assert client.connected is True
        assert client._no_ack_mode is False


class TestGDBRegisters:
    def test_arm_layout(self):
        client = GDBRemoteClient(arch="arm32")
        assert client.arch == "arm32"
        assert client.register_names == [f"r{i}" for i in range(16)] + ["cpsr"]

    def test_aarch64_layout(self):
        client = GDBRemoteClient(arch="aarch64")
        names = client.register_names
        assert len(names) == 34
        assert names[:2] == ["x0", "x1"] and names[-3:] == ["sp", "pc", "cpsr"]
        names.append("bogus")  # returned list is a copy
        assert len(client.register_names) == 34

    def test_read_all_registers_decodes_little_endian(self, gdb):
        values = list(range(16)) + [0x600001D3]
        values[1] = 0x12345678
        gdb._sock.feed(rsp("".join(le_hex(v, 4) for v in values)))
        regs = gdb.read_all_registers()
        assert gdb._sock.sent == [b"$g#67"]
        assert regs["r1"] == 0x12345678
        assert regs["r15"] == 15
        assert regs["cpsr"] == 0x600001D3
        assert len(regs) == 17

    def test_read_all_registers_truncated_reply(self, gdb):
        gdb._sock.feed(rsp(le_hex(7, 4) + le_hex(9, 4)))
        assert gdb.read_all_registers() == {"r0": 7, "r1": 9}

    def test_read_all_registers_aarch64(self):
        client = GDBRemoteClient(arch="aarch64")
        client._sock = FakeSocket(rsp(le_hex(0x1122334455667788, 8)))
        client._no_ack_mode = True
        assert client.read_all_registers() == {"x0": 0x1122334455667788}

    @pytest.mark.parametrize("reply", ["E01", ""])
    def test_read_all_registers_error(self, gdb, reply):
        gdb._sock.feed(rsp(reply))
        with pytest.raises(GDBError, match="Register read failed"):
            gdb.read_all_registers()

    def test_read_single_register(self, gdb):
        gdb._sock.feed(rsp("00800008"))
        assert gdb.read_register(15) == 0x08008000
        assert gdb._sock.sent == [rsp("pf")]

    def test_read_single_register_error(self, gdb):
        gdb._sock.feed(rsp("E45"))
        with pytest.raises(GDBError):
            gdb.read_register(3)

    def test_write_register(self, gdb):
        gdb._sock.feed(rsp("OK"))
        gdb.write_register(1, 0xDEADBEEF)
        assert gdb._sock.sent == [rsp("P1=efbeadde")]

    def test_write_register_error(self, gdb):
        gdb._sock.feed(rsp("E02"))
        with pytest.raises(GDBError, match="Register write failed: E02"):
            gdb.write_register(0, 1)


class TestGDBMemory:
    def test_read_memory(self, gdb):
        gdb._sock.feed(rsp("01020304"))
        assert gdb.read_memory(0x20000000, 4) == b"\x01\x02\x03\x04"
        assert gdb._sock.sent == [rsp("m20000000,4")]

    def test_read_memory_error(self, gdb):
        gdb._sock.feed(rsp("E14"))
        with pytest.raises(GDBError, match="Memory read failed"):
            gdb.read_memory(0, 4)

    def test_write_memory(self, gdb):
        gdb._sock.feed(rsp("OK"))
        gdb.write_memory(0x1000, b"\xaa\xbb")
        assert gdb._sock.sent == [rsp("M1000,2:aabb")]

    def test_write_memory_error(self, gdb):
        gdb._sock.feed(rsp("E01"))
        with pytest.raises(GDBError, match="Memory write failed"):
            gdb.write_memory(0x1000, b"\x00")


class TestGDBBreakpoints:
    @pytest.mark.parametrize(
        "method, args, packet",
        [
            ("set_breakpoint", (0x8000,), "Z0,8000,4"),
            ("clear_breakpoint", (0x8000, 2), "z0,8000,2"),
            ("set_watchpoint", (0x2000, 4, "read"), "Z3,2000,4"),
            ("set_watchpoint", (0x2000, 8, "access"), "Z4,2000,8"),
            ("set_watchpoint", (0x2000, 4, "bogus"), "Z2,2000,4"),
            ("clear_watchpoint", (0x2000,), "z2,2000,4"),
            ("clear_watchpoint", (0x2000, 4, "access"), "z4,2000,4"),
        ],
    )
    def test_packet_and_ok_reply(self, gdb, method, args, packet):
        gdb._sock.feed(rsp("OK"))
        assert getattr(gdb, method)(*args) is True
        assert gdb._sock.sent == [rsp(packet)]

    def test_unsupported_reply_returns_false(self, gdb):
        gdb._sock.feed(rsp(""))
        assert gdb.set_breakpoint(0x100) is False


class TestGDBExecution:
    def test_step_returns_stop_reply(self, gdb):
        gdb._sock.feed(rsp("S05"))
        assert gdb.step() == "S05"
        assert gdb._sock.sent == [rsp("s")]

    def test_continue_returns_stop_reply(self, gdb):
        gdb._sock.feed(rsp("T05thread:01;"))
        assert gdb.continue_execution() == "T05thread:01;"
        assert gdb._sock.sent == [rsp("c")]

    @pytest.mark.parametrize("method", ["step", "continue_execution"])
    def test_error_reply_raises(self, gdb, method):
        gdb._sock.feed(rsp("E01"))
        with pytest.raises(GDBError):
            getattr(gdb, method)()

    def test_halt_sends_ctrl_c(self, gdb):
        gdb._sock.feed(rsp("S02"))
        assert gdb.halt() == "S02"
        assert gdb._sock.sent == [b"\x03"]


class TestGDBTargetInfo:
    def test_thread_list_is_paged(self, gdb):
        gdb._sock.feed(rsp("m1,2"), rsp("m3"), rsp("l"))
        assert gdb.get_thread_info() == ["1", "2", "3"]
        assert gdb._sock.sent == [rsp("qfThreadInfo"), rsp("qsThreadInfo"), rsp("qsThreadInfo")]

    def test_target_description_single_chunk(self, gdb):
        gdb._sock.feed(rsp("l<target/>"))
        assert gdb.get_target_description() == "<target/>"

    def test_target_description_multi_chunk_uses_offsets(self, gdb):
        gdb._sock.feed(rsp("m<targ"), rsp("met>"), rsp("l</x>"))
        assert gdb.get_target_description() == "<target></x>"
        assert gdb._sock.sent[1] == rsp("qXfer:features:read:target.xml:5,ffff")
        assert gdb._sock.sent[2] == rsp("qXfer:features:read:target.xml:8,ffff")

    def test_target_description_stops_on_unexpected_reply(self, gdb):
        gdb._sock.feed(rsp("m<a"), rsp("E00"))
        assert gdb.get_target_description() == "<a"

    def test_target_description_unsupported(self, gdb):
        gdb._sock.feed(rsp(""))
        assert gdb.get_target_description() == ""


class TestGDBLifecycle:
    def test_disconnect_detaches_and_closes(self, gdb):
        sock = gdb._sock
        sock.feed(rsp("OK"))
        gdb.disconnect()
        assert sock.sent == [rsp("D")]
        assert sock.closed is True
        assert gdb.connected is False
        assert gdb._sock is None

    def test_detach_swallows_errors(self, gdb):
        gdb.detach()  # server already gone: recv returns b""
        assert gdb._sock.sent == [rsp("D")]

    def test_disconnect_without_socket(self):
        client = GDBRemoteClient()
        client.disconnect()
        assert client.connected is False

    def test_disconnect_tolerates_close_failure(self, gdb):
        gdb._sock.close = MagicMock(side_effect=OSError("boom"))
        gdb.disconnect()
        assert gdb._sock is None


# --- QMP -------------------------------------------------------------------


def jline(obj) -> bytes:
    return json.dumps(obj).encode() + b"\r\n"


GREETING = {"QMP": {"version": {"qemu": {"major": 8}}, "capabilities": []}}


@pytest.fixture
def qmp():
    client = QMPClient()
    client._sock = FakeSocket()
    client._connected = True
    return client


def sent_json(sock):
    return [json.loads(chunk) for chunk in sock.sent]


class TestQMPConnect:
    def test_tcp_negotiation(self, monkeypatch):
        sock = FakeSocket(jline(GREETING) + jline({"return": {}}))
        monkeypatch.setattr(qmp_mod, "socket", socket_module_for(sock))
        client = QMPClient()
        client.connect_tcp(port=5555, timeout=1.5)
        assert client.connected is True
        assert sock.address == ("localhost", 5555)
        assert sock.timeout == 1.5
        assert sock.sent == [b'{"execute": "qmp_capabilities"}\r\n']

    def test_non_localhost_warns(self, monkeypatch, caplog):
        sock = FakeSocket(jline(GREETING), jline({"return": {}}))
        monkeypatch.setattr(qmp_mod, "socket", socket_module_for(sock))
        with caplog.at_level(logging.WARNING, logger=qmp_mod.__name__):
            QMPClient().connect_tcp(host="10.0.0.5", port=4444)
        assert "NO authentication" in caplog.text

    @pytest.mark.skipif(not hasattr(socket, "AF_UNIX"), reason="no AF_UNIX")
    def test_unix_negotiation(self, monkeypatch):
        sock = FakeSocket(jline(GREETING), jline({"return": {}}))
        monkeypatch.setattr(qmp_mod, "socket", socket_module_for(sock))
        client = QMPClient()
        client.connect_unix("/tmp/qmp.sock")
        assert client.connected is True
        assert sock.address == "/tmp/qmp.sock"

    def test_invalid_greeting(self, monkeypatch):
        sock = FakeSocket(jline({"hello": 1}))
        monkeypatch.setattr(qmp_mod, "socket", socket_module_for(sock))
        with pytest.raises(QMPError, match="Invalid QMP greeting"):
            QMPClient().connect_tcp()

    def test_capabilities_rejected(self, monkeypatch):
        sock = FakeSocket(jline(GREETING), jline({"error": {"class": "GenericError"}}))
        monkeypatch.setattr(qmp_mod, "socket", socket_module_for(sock))
        client = QMPClient()
        with pytest.raises(QMPError, match="Capability negotiation failed"):
            client.connect_tcp()
        assert client.connected is False


class TestQMPCommands:
    def test_execute_with_arguments(self, qmp):
        qmp._sock.feed(jline({"return": {"ok": True}}))
        assert qmp.execute("device_add", {"driver": "e1000"}) == {"return": {"ok": True}}
        assert sent_json(qmp._sock) == [{"execute": "device_add", "arguments": {"driver": "e1000"}}]

    def test_response_reassembled_from_fragments(self, qmp):
        line = jline({"return": {"status": "running"}})
        qmp._sock.feed(line[:5], line[5:12], line[12:])
        assert qmp.query_status() == {"status": "running"}

    def test_blank_line_before_later_reply_is_skipped(self, qmp):
        qmp._sock.feed(b"\r\n", jline({"return": "x"}))
        assert qmp.hmp_command("info version") == "x"

    def test_connection_closed(self, qmp):
        with pytest.raises(QMPError, match="Connection closed"):
            qmp.execute("stop")

    @pytest.mark.parametrize(
        "method, command",
        [
            ("stop", "stop"),
            ("cont", "cont"),
            ("system_reset", "system_reset"),
            ("system_powerdown", "system_powerdown"),
            ("quit", "quit"),
        ],
    )
    def test_vm_control_commands(self, qmp, method, command):
        qmp._sock.feed(jline({"return": {}}))
        assert getattr(qmp, method)() == {"return": {}}
        assert sent_json(qmp._sock) == [{"execute": command}]

    @pytest.mark.parametrize(
        "method, command",
        [
            ("query_cpus", "query-cpus-fast"),
            ("query_block", "query-block"),
            ("query_chardev", "query-chardev"),
        ],
    )
    def test_list_queries(self, qmp, method, command):
        qmp._sock.feed(jline({"return": [{"id": 0}]}), jline({}))
        assert getattr(qmp, method)() == [{"id": 0}]
        assert getattr(qmp, method)() == []  # missing "return" -> empty list
        assert sent_json(qmp._sock)[0] == {"execute": command}

    def test_query_status_default(self, qmp):
        qmp._sock.feed(jline({}))
        assert qmp.query_status() == {}

    def test_hmp_helpers_build_command_lines(self, qmp):
        qmp._sock.feed(jline({"return": "mem"}), jline({"return": "regs"}))
        assert qmp.read_memory(0x1000, size=16) == "mem"
        assert qmp.read_registers() == "regs"
        args = [m["arguments"]["command-line"] for m in sent_json(qmp._sock)]
        assert args == ["xp /4x 0x1000", "info registers"]


class TestQMPEvents:
    def test_events_dispatched_while_waiting_for_reply(self, qmp):
        seen = []
        qmp.on_event("STOP", seen.append)
        qmp._sock.feed(jline({"event": "STOP", "data": {}}), jline({"return": {}}))
        assert qmp.stop() == {"return": {}}
        assert seen == [{"event": "STOP", "data": {}}]

    def test_failing_handler_is_logged_and_others_still_run(self, qmp, caplog):
        seen = []

        def bad(_):
            raise RuntimeError("handler bug")

        qmp.on_event("RESET", bad)
        qmp.on_event("RESET", seen.append)
        with caplog.at_level(logging.ERROR, logger=qmp_mod.__name__):
            qmp._dispatch_event({"event": "RESET"})
        assert seen == [{"event": "RESET"}]
        assert "failed for event RESET" in caplog.text

    def test_unhandled_event_is_ignored(self, qmp):
        qmp._dispatch_event({"event": "UNKNOWN"})

    def test_background_listener_dispatches_until_eof(self, qmp):
        got = threading.Event()
        qmp.on_event("SHUTDOWN", lambda e: got.set())
        qmp._sock.feed(jline({"return": {}}), jline({"event": "SHUTDOWN"}))
        qmp.start_event_listener()
        thread = qmp._event_thread
        thread.join(timeout=5)
        assert got.is_set()
        assert not thread.is_alive()  # EOF ends the loop


class TestQMPDisconnect:
    def test_disconnect_shuts_down_and_closes(self, qmp):
        sock = qmp._sock
        qmp.disconnect()
        assert sock.shutdown_calls == [socket.SHUT_RDWR]
        assert sock.closed is True
        assert qmp._sock is None
        assert qmp.connected is False

    def test_disconnect_tolerates_socket_errors(self, qmp):
        qmp._sock.shutdown = MagicMock(side_effect=OSError)
        qmp._sock.close = MagicMock(side_effect=RuntimeError)
        qmp.disconnect()
        assert qmp._sock is None


# --- Target state bridge ---------------------------------------------------


def fake_gdb(arch="arm", regs=None, memory=b"", connected=True):
    g = MagicMock()
    g.connected = connected
    g.arch = arch
    g.read_all_registers.return_value = regs or {}
    g.read_memory.return_value = memory
    return g


def cpu_state(nregs=32):
    return SimpleNamespace(regs=[0] * nregs, pc=0, sp=0, lr=0, cpsr=0)


class TestTargetStateBridge:
    @pytest.mark.parametrize("gdb_client", [None, fake_gdb(connected=False)])
    def test_reads_empty_without_live_target(self, gdb_client):
        bridge = TargetStateBridge(gdb_client)
        assert bridge.read_registers() == {}
        assert bridge.read_memory(0, 4) == b""

    def test_reads_swallow_client_errors(self):
        g = fake_gdb()
        g.read_all_registers.side_effect = GDBError("x")
        g.read_memory.side_effect = GDBError("x")
        bridge = TargetStateBridge(g)
        assert bridge.read_registers() == {}
        assert bridge.read_memory(0, 4) == b""

    def test_arm_registers_populate_cpu_state(self):
        regs = {f"r{i}": 0x100 + i for i in range(16)}
        regs["cpsr"] = 0x1D3
        bridge = TargetStateBridge()
        bridge.set_gdb_client(fake_gdb("arm", regs))
        state = cpu_state()
        bridge.set_cpu_state(state)
        bridge.update_cpu_state()
        assert state.regs[:16] == [0x100 + i for i in range(16)]
        assert (state.pc, state.sp, state.lr, state.cpsr) == (0x10F, 0x10D, 0x10E, 0x1D3)
        assert bridge.last_pc == 0x10F
        assert bridge.last_registers == regs

    def test_aarch64_registers_populate_cpu_state(self):
        regs = {f"x{i}": i * 2 for i in range(31)}
        regs.update(sp=0x7FF0, pc=0x40080000, cpsr=0x3C5)
        bridge = TargetStateBridge(fake_gdb("aarch64", regs))
        state = cpu_state()
        bridge.set_cpu_state(state)
        bridge.update_cpu_state()
        assert state.regs[:31] == [i * 2 for i in range(31)]
        assert (state.pc, state.sp, state.cpsr) == (0x40080000, 0x7FF0, 0x3C5)
        assert state.lr == 0

    def test_partial_register_set_keeps_previous_values(self):
        bridge = TargetStateBridge(fake_gdb("arm", {"r0": 5}))
        state = cpu_state()
        state.pc, state.sp = 0x8000, 0x2000
        bridge.set_cpu_state(state)
        bridge.update_cpu_state()
        assert state.regs[0] == 5
        assert (state.pc, state.sp) == (0x8000, 0x2000)

    def test_update_without_cpu_state_is_noop(self):
        bridge = TargetStateBridge(fake_gdb("arm", {"r0": 1}))
        bridge.update_cpu_state()
        assert bridge.last_registers == {}

    def test_update_memory_bus_copies_bytes(self):
        bus = MagicMock()
        bridge = TargetStateBridge(fake_gdb(memory=b"\x01\x02\x03"))
        bridge.update_memory_bus(bus, addr=0x100, length=3)
        assert [c.args for c in bus.write8.call_args_list] == [(0x100, 1), (0x101, 2), (0x102, 3)]

    def test_update_memory_bus_stops_on_write_error(self):
        bus = MagicMock()
        bus.write8.side_effect = [None, IndexError("readonly")]
        bridge = TargetStateBridge(fake_gdb(memory=b"\x01\x02\x03"))
        bridge.update_memory_bus(bus, addr=0, length=3)
        assert bus.write8.call_count == 2

    def test_update_memory_bus_without_data(self):
        bus = MagicMock()
        TargetStateBridge(fake_gdb(memory=b"")).update_memory_bus(bus)
        bus.write8.assert_not_called()

    def test_poll_once_invokes_callback_and_survives_errors(self, caplog):
        calls = []
        bridge = TargetStateBridge(fake_gdb("arm", {"r15": 0x42}))
        bridge.set_cpu_state(cpu_state())
        bridge.set_on_update(lambda: calls.append(bridge.last_pc))
        bridge.poll_once()
        assert calls == [0x42]

        def boom():
            raise RuntimeError("gui gone")

        bridge.set_on_update(boom)
        with caplog.at_level(logging.ERROR):
            bridge.poll_once()
        assert "State update callback failed" in caplog.text

    def test_background_polling_start_stop(self):
        polled = threading.Event()
        bridge = TargetStateBridge(fake_gdb("arm", {"r0": 1}), poll_interval=0.01)
        bridge.set_cpu_state(cpu_state())
        bridge.set_on_update(polled.set)
        bridge.start_polling()
        first_thread = bridge._thread
        bridge.start_polling()  # already running: no second thread
        assert bridge._thread is first_thread
        assert polled.wait(timeout=5)
        bridge.stop_polling()
        assert bridge._thread is None
        assert not first_thread.is_alive()


# --- ELF parser ------------------------------------------------------------


def _strtab(names):
    blob, offsets = b"\x00", {}
    for n in names:
        offsets[n] = len(blob)
        blob += n.encode() + b"\x00"
    return blob, offsets


def build_elf(
    bits=32, machine=0x28, entry=0x8000, big_endian=False, symtab_entsize=None, sections=True
):
    """Assemble a small ELF image with one PT_LOAD, one PT_NOTE and a symtab."""
    ec = ">" if big_endian else "<"
    is64 = bits == 64
    ehsize, phentsize, shentsize = (64, 56, 64) if is64 else (52, 32, 40)
    text = bytes(range(8))

    strtab, soff = _strtab(["main", "counter", "file.c"])
    shstrtab, hoff = _strtab([".text", ".symtab", ".strtab", ".shstrtab"])

    # (name, value, size, info): info = bind << 4 | type
    syms = [
        (0, 0, 0, 0),
        (soff["main"], entry, 8, (1 << 4) | 2),  # GLOBAL FUNC
        (soff["counter"], 0x20000000, 4, (0 << 4) | 1),  # LOCAL OBJECT
        (soff["file.c"], 0, 0, 4),  # FILE: filtered out
        (0, 0x8000, 0, 3),  # unnamed SECTION: filtered out
    ]
    if is64:
        symtab = b"".join(struct.pack(ec + "IBBHQQ", n, i, 0, 1, v, s) for n, v, s, i in syms)
    else:
        symtab = b"".join(struct.pack(ec + "IIIBBH", n, v, s, i, 0, 1) for n, v, s, i in syms)

    phoff = ehsize
    text_off = phoff + 2 * phentsize
    symtab_off = text_off + len(text)
    strtab_off = symtab_off + len(symtab)
    shstrtab_off = strtab_off + len(strtab)
    shoff = shstrtab_off + len(shstrtab)

    ident = b"\x7fELF" + bytes([2 if is64 else 1, 2 if big_endian else 1, 1]) + b"\x00" * 9
    ehdr_fmt = ec + ("HHIQQQIHHHHHH" if is64 else "HHIIIIIHHHHHH")
    ehdr = ident + struct.pack(
        ehdr_fmt,
        2,
        machine,
        1,
        entry,
        phoff,
        shoff if sections else 0,
        0,
        ehsize,
        phentsize,
        2,
        shentsize,
        5 if sections else 0,
        4 if sections else 0,
    )

    def phdr(p_type, off, vaddr, size):
        if is64:
            return struct.pack(ec + "IIQQQQQQ", p_type, 5, off, vaddr, vaddr, size, size, 4)
        return struct.pack(ec + "IIIIIIII", p_type, off, vaddr, vaddr, size, size, 5, 4)

    phdrs = phdr(1, text_off, entry, len(text)) + phdr(4, 0, 0, 0)

    sym_ent = (24 if is64 else 16) if symtab_entsize is None else symtab_entsize
    shdr_fmt = ec + ("IIQQQQIIQQ" if is64 else "IIIIIIIIII")
    shdr_rows = [
        (0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
        (hoff[".text"], 1, 6, entry, text_off, len(text), 0, 0, 4, 0),
        (hoff[".symtab"], 2, 0, 0, symtab_off, len(symtab), 3, 2, 4, sym_ent),
        (hoff[".strtab"], 3, 0, 0, strtab_off, len(strtab), 0, 0, 1, 0),
        (hoff[".shstrtab"], 3, 0, 0, shstrtab_off, len(shstrtab), 0, 0, 1, 0),
    ]
    shdrs = b"".join(struct.pack(shdr_fmt, *row) for row in shdr_rows)

    image = ehdr + phdrs + text + symtab + strtab + shstrtab
    assert len(image) == shoff
    return image + shdrs


EXPECTED_SYMBOLS = [
    ("main", 0x8000, 8, "FUNC", "GLOBAL"),
    ("counter", 0x20000000, 4, "OBJECT", "LOCAL"),
]


class TestELFParser:
    def test_rejects_non_elf(self):
        with pytest.raises(ValueError, match="Not an ELF file"):
            parse_elf_bytes(b"MZ\x90\x00" + b"\x00" * 60)

    def test_elf32_arm(self):
        info = parse_elf_bytes(build_elf(bits=32, machine=0x28, entry=0x8000))
        assert (info.arch, info.bits, info.endian, info.entry_point) == (
            "arm",
            32,
            "little",
            0x8000,
        )
        assert [s.type for s in info.segments] == [1, 4]
        (load,) = info.load_segments
        assert (load.vaddr, load.filesz, load.flags, load.data) == (0x8000, 8, 5, bytes(range(8)))
        assert set(info.sections) == {"", ".text", ".symtab", ".strtab", ".shstrtab"}
        assert info.sections[".text"]["size"] == 8
        assert [tuple(s) for s in info.symbols] == EXPECTED_SYMBOLS

    def test_elf64_aarch64(self):
        info = parse_elf_bytes(build_elf(bits=64, machine=0xB7, entry=0x8000))
        assert (info.arch, info.bits, info.entry_point) == ("aarch64", 64, 0x8000)
        (load,) = info.load_segments
        assert (load.offset, load.vaddr, load.flags) == (64 + 2 * 56, 0x8000, 5)
        assert load.data == bytes(range(8))
        assert [tuple(s) for s in info.symbols] == EXPECTED_SYMBOLS

    def test_big_endian_mips(self):
        info = parse_elf_bytes(build_elf(machine=0x08, entry=0x8000, big_endian=True))
        assert (info.arch, info.endian, info.entry_point) == ("mips", "big", 0x8000)
        assert [s.name for s in info.symbols] == ["main", "counter"]

    def test_unknown_machine_is_reported(self):
        info = parse_elf_bytes(build_elf(machine=0x1234))
        assert info.arch == "unknown(0x1234)"

    def test_zero_symtab_entsize_falls_back_to_default(self):
        info = parse_elf_bytes(build_elf(bits=32, symtab_entsize=0))
        assert [s.name for s in info.symbols] == ["main", "counter"]

    def test_image_without_section_headers(self):
        info = parse_elf_bytes(build_elf(sections=False))
        assert info.sections == {}
        assert info.symbols == []
        assert len(info.load_segments) == 1

    def test_parse_elf_reads_file(self, tmp_path):
        path = tmp_path / "fw.elf"
        path.write_bytes(build_elf(bits=64, machine=0xF3, entry=0x80000000))
        info = parse_elf(str(path))
        assert (info.arch, info.entry_point) == ("riscv", 0x80000000)
