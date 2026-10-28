# SPDX-License-Identifier: MIT
"""MCP tool implementations for EoSim.

Each tool is a plain function returning a JSON-serializable result dict.
The server layer (server.py) handles JSON-RPC framing; this module holds
the domain logic so tools are unit-testable without stdio.
"""

from __future__ import annotations

import hashlib
import ipaddress
import json
import os
import re
import shutil
import struct
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
        "limit": {
            "type": "integer",
            "minimum": 1,
            "maximum": 500,
            "default": 100,
            "description": "Max platforms to return",
        },
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


def list_platforms(
    arch: str = "", vendor: str = "", engine: str = "", domain: str = "", limit: int = 100
) -> dict[str, Any]:
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
        "headless": {"type": "boolean", "default": True, "description": "Run headless (no GUI)"},
        "timeout": {
            "type": "integer",
            "minimum": 1,
            "maximum": 3600,
            "default": 60,
            "description": "Timeout in seconds",
        },
        "firmware": {"type": "string", "description": "Path to firmware image to load (optional)"},
        "dry_run": {
            "type": "boolean",
            "default": True,
            "description": "If true (default), validate and return the launch plan "
            "without starting any process",
        },
    },
    "required": ["platform"],
    "additionalProperties": False,
}


def sim_launch(
    platform: str,
    headless: bool = True,
    timeout: int = 60,
    firmware: str | None = None,
    dry_run: bool = True,
) -> dict[str, Any]:
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
            stdout=lf,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    plan["session_id"] = session_id
    plan["pid"] = proc.pid
    plan["log_file"] = log_file
    plan["started_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    # Persist a session record so sim_status can report on this launch after
    # the launching call returns (the Popen handle is gone by then).
    session_file = os.path.join(log_dir, f"{platform}-{session_id}.session.json")
    with open(session_file, "w", encoding="utf-8") as sf:
        json.dump(
            {
                "session_id": session_id,
                "pid": proc.pid,
                "platform": platform,
                "log_file": log_file,
                "started_at": plan["started_at"],
                "started_epoch": time.time(),
            },
            sf,
            indent=2,
        )
    plan["session_file"] = session_file
    return plan


# ---------------------------------------------------------------------------
# Tool: sim_build
# ---------------------------------------------------------------------------

SIM_BUILD_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "source": {
            "type": "string",
            "description": "Path to the EoS source tree (optional; resolved via "
            "EOS_SOURCE / ./eos when omitted)",
        },
        "dry_run": {
            "type": "boolean",
            "default": True,
            "description": "If true (default), resolve the source and return the "
            "build plan without building",
        },
    },
    "additionalProperties": False,
}


def sim_build(source: str | None = None, dry_run: bool = True) -> dict[str, Any]:
    """Build EoS from source (the ``eosim eos build`` path).

    With ``dry_run=true`` (default) this resolves the EoS source tree and
    returns the exact build plan without running anything — safe for agents
    to probe. With ``dry_run=false`` the build actually runs via
    ``eosim.integrations.eos_runner.build_eos`` and a bounded tail of the
    build log is returned. This completes the list -> build -> flash ->
    console surface of issue #37's roadmap.
    """
    from eosim.integrations.eos_runner import build_eos, find_eos_source

    src = source or find_eos_source()
    if not src:
        return {
            "ok": False,
            "error": "EoS source not found (pass source, set EOS_SOURCE, or clone EoS to ./eos)",
        }
    if not os.path.isdir(src):
        return {"ok": False, "error": f"source is not a directory: {src!r}"}

    plan: dict[str, Any] = {
        "ok": True,
        "dry_run": dry_run,
        "source": src,
        "command": ["eosim", "eos", "build", "--source", src],
    }
    if dry_run:
        return plan

    started = time.time()
    ok, log = build_eos(src)
    plan["ok"] = ok
    plan["started_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started))
    plan["duration_s"] = round(time.time() - started, 3)
    # Builds can log megabytes; the CLI precedent tails 500 chars on failure.
    # 2000 is the agent-useful bound.
    plan["log_tail"] = log[-2000:]
    return plan


# ---------------------------------------------------------------------------
# Tool: sim_flash
# ---------------------------------------------------------------------------

SIM_FLASH_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "platform": {"type": "string", "description": "Platform name (see list_platforms)"},
        "firmware": {"type": "string", "description": "Path to firmware image to stage"},
        "dry_run": {
            "type": "boolean",
            "default": True,
            "description": "If true (default), validate and return the flash plan "
            "without writing anything",
        },
    },
    "required": ["platform", "firmware"],
    "additionalProperties": False,
}


def _sha256_file(path: str, chunk_size: int = 65536) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def sim_flash(
    platform: str,
    firmware: str,
    dry_run: bool = True,
) -> dict[str, Any]:
    """Stage a firmware image into a platform's simulated flash.

    With ``dry_run=true`` (default) this validates the platform and the
    firmware file and returns the exact flash plan without writing anything
    -- safe for agents to probe. With ``dry_run=false`` the image is copied
    to ``out/firmware/<platform>/`` with a ``.meta.json`` sidecar (sha256,
    size, staged_at); pass the returned ``staged_path`` as ``firmware`` to
    ``sim_launch`` to boot it.
    """
    reg = _load_registry()
    p = reg.get(platform)
    if p is None:
        return {"ok": False, "error": f"unknown platform: {platform!r}"}
    if not os.path.isfile(firmware):
        return {"ok": False, "error": f"firmware not found: {firmware!r}"}

    size = os.path.getsize(firmware)
    digest = _sha256_file(firmware)
    staged_dir = os.path.join("out", "firmware", platform)
    staged_path = os.path.join(staged_dir, os.path.basename(firmware))
    plan: dict[str, Any] = {
        "ok": True,
        "dry_run": dry_run,
        "platform": _platform_summary(p),
        "firmware": firmware,
        "size": size,
        "sha256": digest,
        "staged_path": staged_path,
    }

    if dry_run:
        return plan

    os.makedirs(staged_dir, exist_ok=True)
    shutil.copy2(firmware, staged_path)
    meta_path = staged_path + ".meta.json"
    with open(meta_path, "w", encoding="utf-8") as mf:
        json.dump(
            {
                "platform": platform,
                "source": os.path.abspath(firmware),
                "size": size,
                "sha256": digest,
                "staged_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            },
            mf,
            indent=2,
        )
    plan["staged_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    plan["meta_path"] = meta_path
    return plan


# ---------------------------------------------------------------------------
# Tool: sim_status
# ---------------------------------------------------------------------------

SIM_STATUS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "session_id": {
            "type": "string",
            "description": "Session id returned by sim_launch (dry_run=false)",
        },
        "log_dir": {
            "type": "string",
            "default": os.path.join("out", "logs"),
            "description": "Directory holding session logs and records",
        },
    },
    "required": ["session_id"],
    "additionalProperties": False,
}


def _pid_alive(pid: int) -> bool:
    if os.name == "nt":
        # Windows has no signal-0 probe: os.kill(pid, 0) is not a liveness
        # check there (it can raise/interrupt in the *calling* process).
        # OpenProcess + GetExitCodeProcess is the supported test.
        import ctypes

        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        handle = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        try:
            code = ctypes.c_ulong()
            if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
                return False
            return code.value == 259  # STILL_ACTIVE
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # exists, owned by someone else
    except OSError:
        return False
    return True


def sim_status(
    session_id: str,
    log_dir: str = os.path.join("out", "logs"),
) -> dict[str, Any]:
    """Report the state of a simulation launched via sim_launch.

    Reads the session record sim_launch persisted next to the log and
    checks whether the recorded pid is still alive. Sessions launched
    before session records existed report state "unknown" (log presence
    only) rather than a fabricated running/exited verdict.
    """
    if not _SESSION_ID_RE.match(session_id or ""):
        return {"ok": False, "error": f"invalid session_id: {session_id!r}"}
    log_path = Path(log_dir)
    records = sorted(log_path.glob(f"*-{session_id}.session.json")) if log_path.is_dir() else []
    logs = sorted(log_path.glob(f"*-{session_id}.log")) if log_path.is_dir() else []
    if not records and not logs:
        return {
            "ok": False,
            "error": f"no session {session_id!r} found in {log_dir!r}; "
            "launch with sim_launch(dry_run=false) first",
        }
    result: dict[str, Any] = {"ok": True, "session_id": session_id}
    if logs:
        result["log_file"] = str(logs[0])
        result["log_size"] = logs[0].stat().st_size
    if not records:
        result["state"] = "unknown"
        result["note"] = "no session record (launched before sim_status existed); log presence only"
        return result
    try:
        record = json.loads(records[0].read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"ok": False, "error": f"cannot read session record {records[0]}: {exc}"}
    pid = int(record.get("pid", 0))
    alive = _pid_alive(pid) if pid > 0 else False
    result.update(
        {
            "platform": record.get("platform"),
            "pid": pid,
            "started_at": record.get("started_at"),
            "state": "running" if alive else "exited",
        }
    )
    if alive and record.get("started_epoch"):
        result["uptime_seconds"] = round(time.time() - float(record["started_epoch"]), 1)
    return result


# ---------------------------------------------------------------------------
# Tool: console_tail
# ---------------------------------------------------------------------------

CONSOLE_TAIL_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "session_id": {
            "type": "string",
            "description": "Session id returned by sim_launch (dry_run=false)",
        },
        "lines": {
            "type": "integer",
            "minimum": 1,
            "maximum": 1000,
            "default": 50,
            "description": "Number of trailing log lines to return",
        },
        "log_dir": {
            "type": "string",
            "default": os.path.join("out", "logs"),
            "description": "Directory holding session logs",
        },
    },
    "required": ["session_id"],
    "additionalProperties": False,
}

_SESSION_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def console_tail(
    session_id: str,
    lines: int = 50,
    log_dir: str = os.path.join("out", "logs"),
) -> dict[str, Any]:
    """Return the tail of a simulation session's console log.

    ``sim_launch`` with ``dry_run=false`` writes the simulator's stdout to
    ``<log_dir>/<platform>-<session_id>.log``; this tool reads back the last
    ``lines`` lines so an agent can check boot output, faults, or test
    results without shell access.
    """
    if not _SESSION_ID_RE.match(session_id or ""):
        return {"ok": False, "error": f"invalid session_id: {session_id!r}"}
    log_path = Path(log_dir)
    matches = sorted(log_path.glob(f"*-{session_id}.log")) if log_path.is_dir() else []
    if not matches:
        return {
            "ok": False,
            "error": f"no log found for session {session_id!r} in {log_dir!r}; "
            "launch with sim_launch(dry_run=false) first",
        }
    log_file = matches[0]
    try:
        text = log_file.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return {"ok": False, "error": f"cannot read {log_file}: {exc}"}
    all_lines = text.splitlines()
    tail = all_lines[-max(1, min(lines, 1000)) :]
    return {
        "ok": True,
        "session_id": session_id,
        "log_file": str(log_file),
        "size": log_file.stat().st_size,
        "total_lines": len(all_lines),
        "truncated": len(all_lines) > len(tail),
        "lines": tail,
    }


# ---------------------------------------------------------------------------
# Tool: gpio_poke
# ---------------------------------------------------------------------------

GPIO_POKE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "session_id": {
            "type": "string",
            "description": "Session id returned by sim_launch (dry_run=false)",
        },
        "pin": {
            "type": "integer",
            "minimum": 0,
            "maximum": 255,
            "description": "GPIO pin number to drive (the simulator validates "
            "it against the platform's actual GPIO count)",
        },
        "value": {
            "type": "integer",
            "minimum": 0,
            "maximum": 1,
            "description": "Logic level to drive: 0 (low) or 1 (high)",
        },
        "log_dir": {
            "type": "string",
            "default": os.path.join("out", "logs"),
            "description": "Directory holding session logs and records",
        },
        "dry_run": {
            "type": "boolean",
            "default": True,
            "description": "If true (default), validate and return the poke "
            "plan without queueing anything",
        },
    },
    "required": ["session_id", "pin", "value"],
    "additionalProperties": False,
}


def gpio_poke(
    session_id: str,
    pin: int,
    value: int,
    log_dir: str = os.path.join("out", "logs"),
    dry_run: bool = True,
) -> dict[str, Any]:
    """Queue a GPIO pin change for a running simulation session.

    Delivery is the session control file
    ``<log_dir>/<platform>-<session_id>.gpio.jsonl`` — one JSON object
    per poke, appended in call order, for the simulator to consume.
    ``dry_run=true`` (the default) validates the session and returns
    the plan without writing anything.

    A poke is queued only for a session whose recorded pid is still
    alive: poking an exited or record-less session fails closed
    rather than queueing an event nothing will ever consume.
    """
    if not _SESSION_ID_RE.match(session_id or ""):
        return {"ok": False, "error": f"invalid session_id: {session_id!r}"}
    if isinstance(pin, bool) or not isinstance(pin, int) or not 0 <= pin <= 255:
        return {"ok": False, "error": f"invalid pin: {pin!r} (integer 0-255)"}
    if isinstance(value, bool):
        value = int(value)
    if not isinstance(value, int) or value not in (0, 1):
        return {"ok": False, "error": f"invalid value: {value!r} (0 or 1)"}
    log_path = Path(log_dir)
    records = sorted(log_path.glob(f"*-{session_id}.session.json")) if log_path.is_dir() else []
    if not records:
        return {
            "ok": False,
            "error": f"no session {session_id!r} found in {log_dir!r}; "
            "launch with sim_launch(dry_run=false) first",
        }
    try:
        record = json.loads(records[0].read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"ok": False, "error": f"cannot read session record {records[0]}: {exc}"}
    pid = int(record.get("pid", 0))
    if pid <= 0 or not _pid_alive(pid):
        return {
            "ok": False,
            "error": f"session {session_id!r} is not running (pid {pid}); "
            "a poke cannot be delivered to an exited session",
        }
    control_file = str(records[0]).removesuffix(".session.json") + ".gpio.jsonl"
    plan: dict[str, Any] = {
        "ok": True,
        "dry_run": dry_run,
        "session_id": session_id,
        "platform": record.get("platform"),
        "pin": pin,
        "value": value,
        "control_file": control_file,
    }
    if dry_run:
        plan["note"] = "dry run: nothing queued; set dry_run=false to append the poke event"
        return plan
    event = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "epoch": time.time(),
        "pin": pin,
        "value": value,
    }
    try:
        with open(control_file, "a", encoding="utf-8") as cf:
            cf.write(json.dumps(event) + "\n")
    except OSError as exc:
        return {"ok": False, "error": f"cannot write control file {control_file}: {exc}"}
    plan["event"] = event
    return plan


# ---------------------------------------------------------------------------
# Tool: net_capture (offline pcap summary only)
# ---------------------------------------------------------------------------

NET_CAPTURE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "session_id": {
            "type": "string",
            "description": "Session id returned by sim_launch (dry_run=false)",
        },
        "pcap_path": {
            "type": "string",
            "description": "Explicit path to a .pcap file (offline analysis only); "
            "defaults to a pcap recorded for the session in log_dir",
        },
        "max_packets": {
            "type": "integer",
            "minimum": 1,
            "maximum": 1000,
            "default": 200,
            "description": "Max one-line packet summaries to return (clamped server-side)",
        },
        "log_dir": {
            "type": "string",
            "default": os.path.join("out", "logs"),
            "description": "Directory holding session logs / recorded pcaps",
        },
    },
    "required": ["session_id"],
    "additionalProperties": False,
}

#: Server-side hard cap on packet summaries, whatever the caller asks for.
NET_CAPTURE_MAX_PACKETS = 1000

# pcap magic -> (struct endianness prefix, timestamp divisor)
_PCAP_MAGICS = {
    b"\xd4\xc3\xb2\xa1": ("<", 1_000_000),  # little-endian, microsecond
    b"\xa1\xb2\xc3\xd4": (">", 1_000_000),  # big-endian, microsecond
    b"\x4d\x3c\xb2\xa1": ("<", 1_000_000_000),  # little-endian, nanosecond
    b"\xa1\xb2\x3c\x4d": (">", 1_000_000_000),  # big-endian, nanosecond
}

_IP_PROTO_NAMES = {1: "ICMP", 6: "TCP", 17: "UDP", 58: "ICMPv6"}


def _mac(raw: bytes) -> str:
    return ":".join(f"{b:02x}" for b in raw)


def _parse_packet(data: bytes, linktype: int):
    """Walk Ethernet/IP/TCP/UDP headers; return (proto, src, dst, summary_tail).

    Headers only — payload bytes are never inspected or returned.
    """
    if linktype == 1:  # Ethernet
        if len(data) < 14:
            return "Other", "", "", "truncated ethernet header"
        dst_mac, src_mac = _mac(data[0:6]), _mac(data[6:12])
        ethertype = struct.unpack(">H", data[12:14])[0]
        offset = 14
        if ethertype == 0x8100 and len(data) >= 18:  # 802.1Q VLAN tag
            ethertype = struct.unpack(">H", data[16:18])[0]
            offset = 18
        payload = data[offset:]
        if ethertype == 0x0806:
            return "ARP", src_mac, dst_mac, "ARP"
        if ethertype == 0x0800:
            return _parse_ip(payload, 4)
        if ethertype == 0x86DD:
            return _parse_ip(payload, 6)
        return "Other", src_mac, dst_mac, f"ethertype=0x{ethertype:04x}"
    if linktype == 0:  # BSD loopback: 4-byte AF header, then IP
        if len(data) < 5:
            return "Other", "", "", "truncated loopback header"
        version = data[4] >> 4
        return _parse_ip(data[4:], version if version in (4, 6) else 4)
    if linktype == 101:  # raw IP
        if not data:
            return "Other", "", "", "empty packet"
        return _parse_ip(data, data[0] >> 4)
    return "Other", "", "", f"linktype={linktype}"


def _parse_ip(data: bytes, version: int):
    if version == 4:
        if len(data) < 20:
            return "IPv4", "", "", "truncated ipv4 header"
        ihl = (data[0] & 0x0F) * 4
        proto_num = data[9]
        src = str(ipaddress.IPv4Address(data[12:16]))
        dst = str(ipaddress.IPv4Address(data[16:20]))
        header = data[ihl:] if ihl >= 20 else data[20:]
    else:
        if len(data) < 40:
            return "IPv6", "", "", "truncated ipv6 header"
        proto_num = data[6]
        src = str(ipaddress.IPv6Address(data[8:24]))
        dst = str(ipaddress.IPv6Address(data[24:40]))
        header = data[40:]
    proto = _IP_PROTO_NAMES.get(proto_num, f"IP/{proto_num}")
    tail = proto
    if proto_num in (6, 17) and len(header) >= 4:  # TCP / UDP ports
        sport, dport = struct.unpack(">HH", header[0:4])
        src = f"{src}:{sport}"
        dst = f"{dst}:{dport}"
        tail = f"{proto} {sport} -> {dport}"
        if proto_num == 6 and len(header) >= 14:
            flags = header[13]
            names = "".join(
                ch
                for bit, ch in ((0x02, "S"), (0x10, "A"), (0x01, "F"), (0x04, "R"), (0x08, "P"))
                if flags & bit
            )
            if names:
                tail += f" [{names}]"
    return proto, src, dst, tail


def _read_pcap(path: Path, limit: int):
    """Parse a classic pcap file with stdlib only.

    Returns (linktype, packets, total, histogram, talkers, first_ts,
    last_ts): ``packets`` holds at most ``limit`` summarized entries,
    while the count, histogram, talkers, and timestamps cover every
    packet in the file.
    """
    raw = path.read_bytes()
    if len(raw) < 24:
        raise ValueError("not a pcap file: shorter than the 24-byte global header")
    magic = raw[0:4]
    if magic not in _PCAP_MAGICS:
        raise ValueError(
            "not a pcap file: bad magic (pcapng and other containers are not supported)"
        )
    endian, divisor = _PCAP_MAGICS[magic]
    _vmaj, _vmin, _tz, _sig, _snap, linktype = struct.unpack(endian + "HHIIII", raw[4:24])
    if linktype not in (0, 1, 101):
        raise ValueError(f"unsupported pcap linktype: {linktype}")
    from collections import Counter

    packets: list[tuple[float, str, str, str, int, str]] = []
    histogram: Counter = Counter()
    talkers: Counter = Counter()
    first_ts: float | None = None
    last_ts: float | None = None
    total = 0
    offset = 24
    header_struct = struct.Struct(endian + "IIII")
    while offset + header_struct.size <= len(raw):
        ts_sec, ts_frac, incl_len, orig_len = header_struct.unpack_from(raw, offset)
        offset += header_struct.size
        if incl_len > len(raw) - offset:
            raise ValueError("truncated pcap file: packet record overruns end of file")
        data = raw[offset : offset + incl_len]
        offset += incl_len
        total += 1
        ts = ts_sec + ts_frac / divisor
        if first_ts is None:
            first_ts = ts
        last_ts = ts
        proto, src, dst, tail = _parse_packet(data, linktype)
        histogram[proto] += 1
        if src and dst:
            talkers[(src, dst)] += 1
        if len(packets) < limit:
            packets.append((ts, proto, src, dst, orig_len, tail))
    return linktype, packets, total, histogram, talkers, first_ts, last_ts


def net_capture(
    session_id: str,
    pcap_path: str | None = None,
    max_packets: int = 200,
    log_dir: str = os.path.join("out", "logs"),
) -> dict[str, Any]:
    """Summarize a recorded pcap for a session — OFFLINE analysis only.

    No live capture, no interface access, no elevated permissions, and
    no raw payload bytes in the output (headers / summary only). Reads
    ``pcap_path`` when given, otherwise the pcap recorded for the
    session under ``log_dir``. ``max_packets`` is clamped server-side
    to :data:`NET_CAPTURE_MAX_PACKETS`.
    """
    if not _SESSION_ID_RE.match(session_id or ""):
        return {"ok": False, "error": f"invalid session_id: {session_id!r}"}
    effective_max = max(1, min(int(max_packets or 200), NET_CAPTURE_MAX_PACKETS))
    if pcap_path:
        candidate = Path(pcap_path)
    else:
        log_path = Path(log_dir)
        matches = sorted(log_path.glob(f"*-{session_id}.pcap")) if log_path.is_dir() else []
        if not matches:
            return {
                "ok": False,
                "error": f"no pcap found for session {session_id!r} in {log_dir!r}; "
                "pass pcap_path explicitly",
            }
        candidate = matches[0]
    if not candidate.is_file():
        return {"ok": False, "error": f"pcap not found: {str(candidate)!r}"}
    try:
        linktype, packets, total, histogram, talkers, first_ts, last_ts = _read_pcap(
            candidate, effective_max
        )
    except (OSError, ValueError) as exc:
        return {"ok": False, "error": f"cannot parse pcap {candidate}: {exc}"}

    summaries: list[str] = []
    for idx, (ts, proto, src, dst, length, tail) in enumerate(packets, start=1):
        summaries.append(f"#{idx} {ts:.6f} {src or '?'} -> {dst or '?'} {tail} len={length}")
    return {
        "ok": True,
        "session_id": session_id,
        "pcap_path": str(candidate),
        "linktype": linktype,
        "packet_count": total,
        "summarized": len(packets),
        "max_packets": effective_max,
        "truncated": total > len(packets),
        "protocol_histogram": dict(sorted(histogram.items())),
        "top_talkers": [
            {"src": src, "dst": dst, "count": count}
            for (src, dst), count in talkers.most_common(10)
        ],
        "first_timestamp": first_ts,
        "last_timestamp": last_ts,
        "packets": summaries,
    }


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
    "sim_build": {
        "description": "Build EoS from source. Dry-run by default (resolves the "
        "source tree and returns the build plan); set dry_run=false to "
        "actually run the build and get a bounded log tail.",
        "inputSchema": SIM_BUILD_SCHEMA,
        "handler": sim_build,
    },
    "sim_flash": {
        "description": "Stage a firmware image into a platform's simulated "
        "flash. Dry-run by default; set dry_run=false to copy the image to "
        "out/firmware/<platform>/ with a .meta.json sidecar.",
        "inputSchema": SIM_FLASH_SCHEMA,
        "handler": sim_flash,
    },
    "sim_status": {
        "description": "Report the state of a simulation launched with "
        "sim_launch(dry_run=false): running/exited (from the persisted "
        "session record + pid liveness), pid, platform, uptime, log size.",
        "inputSchema": SIM_STATUS_SCHEMA,
        "handler": sim_status,
    },
    "console_tail": {
        "description": "Return the tail of a simulation session's console log "
        "(from sim_launch with dry_run=false), so boot output and faults can "
        "be inspected without shell access.",
        "inputSchema": CONSOLE_TAIL_SCHEMA,
        "handler": console_tail,
    },
    "gpio_poke": {
        "description": "Queue a GPIO pin change for a running simulation "
        "session (appends one event to the session's .gpio.jsonl control "
        "file for the simulator to consume). Dry-run by default; fails "
        "closed for exited or unknown sessions.",
        "inputSchema": GPIO_POKE_SCHEMA,
        "handler": gpio_poke,
    },
    "net_capture": {
        "description": "Summarize a recorded pcap for a session (offline "
        "analysis only: packet count, protocol histogram, top talkers, "
        "bounded one-line packet summaries; no live capture, no payloads).",
        "inputSchema": NET_CAPTURE_SCHEMA,
        "handler": net_capture,
        "annotations": {"readOnlyHint": True},
    },
}


def _validate_schema(value: Any, schema: dict[str, Any], path: str = "arguments") -> str | None:
    """Validate the JSON Schema subset used by the published MCP tools."""
    kind = schema.get("type")
    matches = {
        "object": lambda v: isinstance(v, dict),
        "array": lambda v: isinstance(v, list),
        "string": lambda v: isinstance(v, str),
        "boolean": lambda v: isinstance(v, bool),
        "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
        "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    }
    if kind in matches and not matches[kind](value):
        return f"{path} must be {kind}"
    if "enum" in schema and value not in schema["enum"]:
        return f"{path} must be one of {schema['enum']}"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            return f"{path} must be at least {schema['minimum']}"
        if "maximum" in schema and value > schema["maximum"]:
            return f"{path} must be at most {schema['maximum']}"
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            return f"{path} is too short"
        if len(value) > schema.get("maxLength", float("inf")):
            return f"{path} is too long"
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0) or len(value) > schema.get("maxItems", float("inf")):
            return f"{path} has an invalid number of items"
        if "items" in schema:
            for index, item in enumerate(value):
                error = _validate_schema(item, schema["items"], f"{path}[{index}]")
                if error:
                    return error
    if isinstance(value, dict):
        for required in schema.get("required", []):
            if required not in value:
                return f"{path}.{required} is required"
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            unknown = value.keys() - properties.keys()
            if unknown:
                return f"{path} contains unknown property {sorted(unknown)[0]!r}"
        for key, item in value.items():
            if key in properties:
                error = _validate_schema(item, properties[key], f"{path}.{key}")
                if error:
                    return error
    return None


def list_tools() -> list[dict[str, Any]]:
    """Return MCP tool descriptors (name, description, inputSchema)."""
    descriptors = []
    for name, spec in TOOLS.items():
        descriptor = {
            "name": name,
            "description": spec["description"],
            "inputSchema": spec["inputSchema"],
        }
        if spec.get("annotations"):
            descriptor["annotations"] = spec["annotations"]
        descriptors.append(descriptor)
    return descriptors


def call_tool(name: str, arguments: dict[str, Any] | None) -> dict[str, Any]:
    """Dispatch a tool call; returns the result dict (or an error dict)."""
    spec = TOOLS.get(name)
    if spec is None:
        return {"ok": False, "error": f"unknown tool: {name!r}"}
    error = _validate_schema(arguments or {}, spec["inputSchema"])
    if error:
        return {"ok": False, "error": error}
    try:
        result = spec["handler"](**(arguments or {}))
    except TypeError as exc:
        return {"ok": False, "error": f"invalid arguments for {name}: {exc}"}
    except Exception as exc:  # never let a tool crash the server loop
        return {"ok": False, "error": f"{name} failed: {exc}"}
    if isinstance(result, dict):
        return result
    return {"ok": True, "result": result}
