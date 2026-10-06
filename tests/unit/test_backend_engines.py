# SPDX-License-Identifier: MIT
"""Command construction and result handling of the simulation backends.

External emulators are never launched: ``shutil.which``, ``subprocess`` and
the bridge connection classes are replaced so each test can check the exact
command line built for a platform and how its outcome is reported.
"""

import importlib
import os
import struct
import subprocess
import sys
from unittest.mock import MagicMock

import pytest

from eosim.core.platform import BootConfig, Platform, QemuConfig, RuntimeConfig
from eosim.engine import backend
from eosim.engine.backend import (
    AirSimEngine,
    CARLAEngine,
    EoSimEngine,
    GazeboEngine,
    OpenFOAMEngine,
    QemuEngine,
    QemuLiveEngine,
    RenodeEngine,
    ROS2Engine,
    SimResult,
    XPlaneEngine,
    get_engine,
)
from eosim.engine.qemu.state_bridge import TargetStateBridge


def which_map(mapping):
    return lambda name: mapping.get(name)


def completed(rc=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(args=[], returncode=rc, stdout=stdout, stderr=stderr)


@pytest.fixture
def fake_run(monkeypatch):
    run = MagicMock(return_value=completed())
    monkeypatch.setattr(backend.subprocess, "run", run)
    return run


def make_platform(tmp_path, **overrides):
    fields = dict(
        name="board",
        arch="arm",
        source_dir=str(tmp_path),
        runtime=RuntimeConfig(memory_mb=256),
        qemu=QemuConfig(machine="virt"),
        boot=BootConfig(),
    )
    fields.update(overrides)
    return Platform(**fields)


class TestSimResult:
    def test_artifacts_default_is_per_instance(self):
        a, b = SimResult(), SimResult()
        a.artifacts.append("x")
        assert b.artifacts == []
        assert (a.success, a.exit_code) == (False, -1)


class TestRenodeEngine:
    def test_available_follows_path_lookup(self, monkeypatch):
        monkeypatch.setattr(backend.shutil, "which", which_map({"renode": "/opt/renode"}))
        assert RenodeEngine.available() is True
        monkeypatch.setattr(backend.shutil, "which", which_map({}))
        assert RenodeEngine.available() is False

    def test_not_installed(self, tmp_path, monkeypatch):
        monkeypatch.setattr(backend.shutil, "which", which_map({}))
        res = RenodeEngine.run(make_platform(tmp_path))
        assert (res.success, res.stderr, res.engine) == (False, "Renode not installed", "renode")

    @pytest.mark.parametrize("resc", [None, "missing.resc"])
    def test_missing_script(self, tmp_path, monkeypatch, fake_run, resc):
        monkeypatch.setattr(backend.shutil, "which", which_map({"renode": "/opt/renode"}))
        res = RenodeEngine.run(make_platform(tmp_path, resc=resc))
        assert res.stderr == "No .resc file for platform: board"
        fake_run.assert_not_called()

    def test_successful_boot_writes_log(self, tmp_path, monkeypatch, fake_run):
        (tmp_path / "board.resc").write_text("mach create")
        monkeypatch.setattr(backend.shutil, "which", which_map({"renode": "/opt/renode"}))
        fake_run.return_value = completed(0, "Welcome\nboard login: ", "warn: slow")
        log = tmp_path / "logs" / "renode.log"
        res = RenodeEngine.run(
            make_platform(tmp_path, resc="board.resc"), timeout=9, log_file=str(log)
        )
        resc = os.path.join(str(tmp_path), "board.resc")
        assert fake_run.call_args.args[0] == ["/opt/renode", "--disable-xwt", "--plain", resc]
        assert fake_run.call_args.kwargs["timeout"] == 9
        assert (res.success, res.exit_code, res.boot_detected) == (True, 0, True)
        assert res.artifacts == [str(log)] and res.log_file == str(log)
        text = log.read_text(encoding="utf-8")
        assert text.startswith("=== EoSim Renode Log ===\nPlatform: board\nArch: arm\n")
        assert "board login:" in text
        assert text.endswith("=== STDERR ===\nwarn: slow")

    def test_nonzero_exit_is_failure(self, tmp_path, monkeypatch, fake_run):
        (tmp_path / "b.resc").write_text("")
        monkeypatch.setattr(backend.shutil, "which", which_map({"renode": "/opt/renode"}))
        fake_run.return_value = completed(3, "crash", "")
        res = RenodeEngine.run(make_platform(tmp_path, resc="b.resc"))
        assert (res.success, res.exit_code, res.boot_detected) == (False, 3, False)
        assert res.artifacts == []

    def test_timeout_counts_as_success(self, tmp_path, monkeypatch, fake_run):
        (tmp_path / "b.resc").write_text("")
        monkeypatch.setattr(backend.shutil, "which", which_map({"renode": "/opt/renode"}))
        fake_run.side_effect = subprocess.TimeoutExpired(cmd="renode", timeout=7)
        res = RenodeEngine.run(make_platform(tmp_path, resc="b.resc"), timeout=7)
        assert (res.success, res.stdout) == (True, "Timeout after 7s")


QEMU_ARM = "/usr/bin/qemu-system-arm"


class TestQemuEngine:
    @pytest.mark.parametrize(
        "arch, binary",
        [
            ("arm64", "qemu-system-aarch64"),
            ("x86_64", "qemu-system-x86_64"),
            ("sparc", "qemu-system-sparc"),
        ],
    )
    def test_available_maps_arch_to_binary(self, monkeypatch, arch, binary):
        asked = []
        monkeypatch.setattr(backend.shutil, "which", lambda n: asked.append(n) or "/bin/q")
        assert QemuEngine.available(arch) is True
        assert asked == [binary]

    def test_dry_run_when_binary_missing(self, tmp_path, monkeypatch, fake_run):
        monkeypatch.setattr(backend.shutil, "which", which_map({}))
        log = tmp_path / "out" / "q.log"
        res = QemuEngine.run(make_platform(tmp_path), log_file=str(log))
        assert (res.success, res.boot_detected) == (True, False)
        assert res.stderr == "qemu-system-arm not installed"
        assert res.stdout == "QEMU not available for arm\n"
        assert "PASSED (dry run)" in log.read_text(encoding="utf-8")
        assert res.artifacts == [str(log)]
        fake_run.assert_not_called()

    def test_dry_run_without_log(self, tmp_path, monkeypatch):
        monkeypatch.setattr(backend.shutil, "which", which_map({}))
        res = QemuEngine.run(make_platform(tmp_path))
        assert res.artifacts == [] and res.log_file == ""

    def test_full_command_line(self, tmp_path, monkeypatch, fake_run):
        (tmp_path / "zImage").write_bytes(b"k")
        (tmp_path / "initrd.img").write_bytes(b"i")
        monkeypatch.setattr(backend.shutil, "which", which_map({"qemu-system-arm": QEMU_ARM}))
        fake_run.return_value = completed(0, "Linux version 6.1\nbuildroot login:", "")
        plat = make_platform(
            tmp_path,
            qemu=QemuConfig(machine="vexpress-a9", cpu="cortex-a9", extra_args=["-bios", "none"]),
            boot=BootConfig(kernel="zImage", initrd="initrd.img", append="console=ttyAMA0"),
        )
        res = QemuEngine.run(plat, timeout=11)
        assert fake_run.call_args.args[0] == [
            QEMU_ARM,
            "-machine",
            "vexpress-a9",
            "-m",
            "256",
            "-nographic",
            "-no-reboot",
            "-monitor",
            "none",
            "-serial",
            "stdio",
            "-cpu",
            "cortex-a9",
            "-kernel",
            os.path.join(str(tmp_path), "zImage"),
            "-initrd",
            os.path.join(str(tmp_path), "initrd.img"),
            "-append",
            "console=ttyAMA0",
            "-bios",
            "none",
        ]
        assert fake_run.call_args.kwargs["timeout"] == 11
        assert (res.success, res.exit_code, res.boot_detected) == (True, 0, True)

    def test_missing_boot_images_are_not_passed(self, tmp_path, monkeypatch, fake_run):
        monkeypatch.setattr(backend.shutil, "which", which_map({"qemu-system-arm": QEMU_ARM}))
        plat = make_platform(tmp_path, boot=BootConfig(kernel="nope", initrd="nope2"))
        QemuEngine.run(plat)
        cmd = fake_run.call_args.args[0]
        assert "-kernel" not in cmd and "-initrd" not in cmd

    def test_platform_without_extra_args(self, tmp_path, monkeypatch, fake_run):
        """QemuConfig.extra_args defaults to None; that must mean "no extra args"."""
        monkeypatch.setattr(backend.shutil, "which", which_map({"qemu-system-arm": QEMU_ARM}))
        res = QemuEngine.run(make_platform(tmp_path))
        assert fake_run.call_args.args[0][-2:] == ["-serial", "stdio"]
        assert res.success is True

    def test_timeout_and_log(self, tmp_path, monkeypatch, fake_run):
        monkeypatch.setattr(backend.shutil, "which", which_map({"qemu-system-arm": QEMU_ARM}))
        fake_run.side_effect = subprocess.TimeoutExpired(cmd="qemu", timeout=4)
        log = tmp_path / "q.log"
        res = QemuEngine.run(make_platform(tmp_path, qemu=QemuConfig(extra_args=[])), 4, str(log))
        assert res.stdout == "Timeout after 4s (normal for boot)"
        text = log.read_text(encoding="utf-8")
        assert "Engine: qemu-system-arm" in text and "STDERR" not in text

    def test_binary_vanishes_between_lookup_and_exec(self, tmp_path, monkeypatch, fake_run):
        monkeypatch.setattr(backend.shutil, "which", which_map({"qemu-system-arm": QEMU_ARM}))
        fake_run.side_effect = FileNotFoundError
        log = tmp_path / "q.log"
        res = QemuEngine.run(
            make_platform(tmp_path, qemu=QemuConfig(extra_args=[])), log_file=str(log)
        )
        assert res.stderr == "QEMU binary not found: qemu-system-arm"
        assert "=== STDERR ===\nQEMU binary not found" in log.read_text(encoding="utf-8")

    def test_boot_detection_is_case_insensitive(self, tmp_path, monkeypatch, fake_run):
        monkeypatch.setattr(backend.shutil, "which", which_map({"qemu-system-arm": QEMU_ARM}))
        fake_run.return_value = completed(1, "Kernel BOOTED", "")
        res = QemuEngine.run(make_platform(tmp_path, qemu=QemuConfig(extra_args=[])))
        assert (res.exit_code, res.boot_detected) == (1, True)


def arm_program(*words):
    return b"".join(struct.pack("<I", w) for w in words)


class TestEoSimEngine:
    def test_always_available(self):
        assert EoSimEngine.available() is True

    def test_without_firmware_reports_failure(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        plat = make_platform(tmp_path, runtime=RuntimeConfig(memory_mb=1))
        res = EoSimEngine.run(plat, timeout=5, log_file="native.log")
        assert (res.success, res.boot_detected, res.engine) == (False, False, "eosim")
        assert "No firmware loaded" in res.stdout
        text = (tmp_path / "native.log").read_text(encoding="utf-8")
        assert text.startswith("=== EoSim Native Log ===\nPlatform: board\nArch: arm\n")
        assert res.artifacts == ["native.log"]

    def test_runs_firmware_to_halt(self, tmp_path):
        (tmp_path / "fw.bin").write_bytes(arm_program(0xE3A00001, 0xE7FFDEFE))  # MOV r0,#1; UDF
        plat = make_platform(
            tmp_path, runtime=RuntimeConfig(memory_mb=1), boot=BootConfig(firmware="fw.bin")
        )
        res = EoSimEngine.run(plat, timeout=5)
        assert res.success is True
        assert "Simulation stopped (halted)" in res.stdout
        assert res.log_file == ""

    def test_missing_firmware_file_is_not_loaded(self, tmp_path):
        plat = make_platform(
            tmp_path, runtime=RuntimeConfig(memory_mb=1), boot=BootConfig(firmware="gone.bin")
        )
        res = EoSimEngine.run(plat, timeout=5)
        assert res.success is False
        assert "No firmware loaded" in res.stdout


def connection_class(connects=True, **attrs):
    instance = MagicMock(**attrs)
    instance.connect.return_value = connects
    return MagicMock(return_value=instance), instance


class TestBridgeEngines:
    def test_xplane_connected_reports_data_groups(self, tmp_path, monkeypatch):
        import eosim.integrations.xplane as xp

        cls, conn = connection_class(host="10.1.1.1", port=49000)
        conn.receive_data.return_value = {"speed": 1, "alt": 2}
        monkeypatch.setattr(xp, "XPlaneConnection", cls)
        res = XPlaneEngine.run(make_platform(tmp_path))
        assert res.success is True
        assert res.stdout == "X-Plane connected on 10.1.1.1:49000\nReceived 2 data groups"
        conn.disconnect.assert_called_once()

    def test_xplane_connected_without_data(self, tmp_path, monkeypatch):
        import eosim.integrations.xplane as xp

        cls, conn = connection_class(host="h", port=1)
        conn.receive_data.return_value = {}
        monkeypatch.setattr(xp, "XPlaneConnection", cls)
        assert XPlaneEngine.run(make_platform(tmp_path)).stdout == "X-Plane connected on h:1"

    @pytest.mark.parametrize(
        "engine, module, cls_name, failure_text",
        [
            (
                XPlaneEngine,
                "eosim.integrations.xplane",
                "XPlaneConnection",
                "X-Plane not available (connection failed)",
            ),
            (GazeboEngine, "eosim.integrations.gazebo", "GazeboConnection", "Gazebo not available"),
            (
                CARLAEngine,
                "eosim.integrations.carla",
                "CARLAConnection",
                "CARLA not available (connection failed)",
            ),
            (AirSimEngine, "eosim.integrations.airsim", "AirSimConnection", "AirSim not available"),
            (ROS2Engine, "eosim.integrations.ros2", "ROS2Bridge", "ROS 2 not available"),
        ],
    )
    def test_connection_failure(
        self, tmp_path, monkeypatch, engine, module, cls_name, failure_text
    ):
        cls, conn = connection_class(connects=False)
        monkeypatch.setattr(importlib.import_module(module), cls_name, cls)
        res = engine.run(make_platform(tmp_path))
        assert (res.success, res.stdout) == (False, failure_text)
        conn.disconnect.assert_not_called()

    @pytest.mark.parametrize(
        "engine, module, cls_name, success_text",
        [
            (GazeboEngine, "eosim.integrations.gazebo", "GazeboConnection", "Gazebo connected"),
            (
                CARLAEngine,
                "eosim.integrations.carla",
                "CARLAConnection",
                "CARLA connected on 127.0.0.1:2000",
            ),
            (AirSimEngine, "eosim.integrations.airsim", "AirSimConnection", "AirSim connected"),
            (ROS2Engine, "eosim.integrations.ros2", "ROS2Bridge", "ROS 2 bridge connected"),
        ],
    )
    def test_connection_success(
        self, tmp_path, monkeypatch, engine, module, cls_name, success_text
    ):
        cls, conn = connection_class(host="127.0.0.1", port=2000)
        monkeypatch.setattr(importlib.import_module(module), cls_name, cls)
        res = engine.run(make_platform(tmp_path))
        assert (res.success, res.stdout) == (True, success_text)
        conn.disconnect.assert_called_once()

    def test_openfoam_run_passes_case_and_solver(self, tmp_path, monkeypatch):
        import eosim.integrations.openfoam as of

        runner = MagicMock()
        runner.run.return_value = {"success": True, "log": "End\n"}
        cls = MagicMock(return_value=runner)
        monkeypatch.setattr(of, "OpenFOAMRunner", cls)
        res = OpenFOAMEngine.run(
            make_platform(tmp_path), timeout=30, case_dir="/case", solver="icoFoam"
        )
        cls.assert_called_once_with(case_dir="/case")
        runner.set_solver.assert_called_once_with("icoFoam")
        runner.run.assert_called_once_with(timeout=30)
        assert (res.success, res.stdout, res.engine) == (True, "End\n", "openfoam")


class TestBridgeAvailability:
    def test_gazebo_accepts_either_binary(self, monkeypatch):
        monkeypatch.setattr(backend.shutil, "which", which_map({"gzserver": "/usr/bin/gzserver"}))
        assert GazeboEngine.available() is True
        monkeypatch.setattr(backend.shutil, "which", which_map({}))
        assert GazeboEngine.available() is False

    def test_openfoam_accepts_any_solver(self, monkeypatch):
        monkeypatch.setattr(backend.shutil, "which", which_map({"icoFoam": "/opt/of/icoFoam"}))
        assert OpenFOAMEngine.available() is True
        monkeypatch.setattr(backend.shutil, "which", which_map({}))
        assert OpenFOAMEngine.available() is False

    def test_ros2_depends_on_rclpy_import(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "rclpy", MagicMock())
        assert ROS2Engine.available() is True
        monkeypatch.setitem(sys.modules, "rclpy", None)  # forces ImportError
        assert ROS2Engine.available() is False

    @pytest.mark.parametrize(
        "engine, port", [(CARLAEngine, 2000), (AirSimEngine, 41451), (XPlaneEngine, 49000)]
    )
    def test_socket_probe(self, monkeypatch, engine, port):
        import socket

        sock = MagicMock()
        monkeypatch.setattr(socket, "socket", MagicMock(return_value=sock))
        assert engine.available() is True
        sock.connect.assert_called_once_with(("127.0.0.1", port))
        sock.close.assert_called_once()
        sock.connect.side_effect = ConnectionRefusedError
        assert engine.available() is False


class TestGetEngine:
    @pytest.mark.parametrize(
        "engine_name, expected",
        [
            ("qemu-live", QemuLiveEngine),
            ("xplane", XPlaneEngine),
            ("gazebo", GazeboEngine),
            ("openfoam", OpenFOAMEngine),
            ("carla", CARLAEngine),
            ("airsim", AirSimEngine),
            ("ros2", ROS2Engine),
            ("eosim", EoSimEngine),
        ],
    )
    def test_named_engines(self, engine_name, expected):
        assert type(get_engine(Platform(engine=engine_name, arch="arm"))) is expected

    def test_renode_when_installed(self, monkeypatch):
        monkeypatch.setattr(backend.shutil, "which", which_map({"renode": "/opt/renode"}))
        assert type(get_engine(Platform(engine="renode", arch="arm"))) is RenodeEngine

    @pytest.mark.parametrize("installed", [{}, {"qemu-system-arm": QEMU_ARM}])
    def test_falls_back_to_qemu(self, monkeypatch, installed):
        monkeypatch.setattr(backend.shutil, "which", which_map(installed))
        assert type(get_engine(Platform(engine="renode", arch="arm"))) is QemuEngine


@pytest.fixture
def live_env(monkeypatch):
    """Patch process launch and protocol clients used by QemuLiveEngine."""
    import time

    import eosim.engine.qemu.gdb_client as gdb_mod
    import eosim.engine.qemu.qmp_client as qmp_mod

    monkeypatch.setattr(time, "sleep", lambda s: None)
    monkeypatch.setattr(
        backend.shutil, "which", which_map({"qemu-system-aarch64": "/usr/bin/qemu-system-aarch64"})
    )
    proc = MagicMock()
    proc.poll.return_value = None
    popen = MagicMock(return_value=proc)
    monkeypatch.setattr(backend.subprocess, "Popen", popen)
    qmp = MagicMock()
    gdb = MagicMock()
    gdb_cls = MagicMock(return_value=gdb)
    monkeypatch.setattr(qmp_mod, "QMPClient", MagicMock(return_value=qmp))
    monkeypatch.setattr(gdb_mod, "GDBRemoteClient", gdb_cls)
    return MagicMock(proc=proc, popen=popen, qmp=qmp, gdb=gdb, gdb_cls=gdb_cls)


class TestQemuLiveEngine:
    def test_requires_binary(self, tmp_path, monkeypatch):
        monkeypatch.setattr(backend.shutil, "which", which_map({}))
        res = QemuLiveEngine().run(make_platform(tmp_path))
        assert (res.success, res.stderr) == (False, "qemu-system-arm not installed")

    def test_launch_with_default_ports(self, tmp_path, live_env):
        engine = QemuLiveEngine()
        plat = make_platform(
            tmp_path, arch="arm64", qemu=QemuConfig(machine="virt", extra_args=["-s"])
        )
        res = engine.run(plat)
        cmd = live_env.popen.call_args.args[0]
        assert cmd[:12] == [
            "/usr/bin/qemu-system-aarch64",
            "-machine",
            "virt",
            "-m",
            "256",
            "-nographic",
            "-no-reboot",
            "-gdb",
            "tcp::1234",
            "-qmp",
            "tcp:localhost:4444,server=on,wait=off",
            "-s",
        ]
        assert "-S" not in cmd
        assert res.success is True
        assert res.stdout == "QEMU live session started (GDB:1234 QMP:4444)"
        live_env.qmp.connect_tcp.assert_called_once_with(port=4444)
        live_env.gdb_cls.assert_called_once_with(arch="aarch64")
        live_env.gdb.connect.assert_called_once_with(port=1234)
        assert engine.qmp is live_env.qmp and engine.gdb is live_env.gdb
        assert isinstance(engine.state_bridge, TargetStateBridge)

    def test_custom_ports_paused_cpu_and_boot_args(self, tmp_path, live_env, monkeypatch):
        monkeypatch.setattr(backend.shutil, "which", which_map({"qemu-system-arm": QEMU_ARM}))
        (tmp_path / "k").write_bytes(b"")
        (tmp_path / "i").write_bytes(b"")
        qemu = QemuConfig(
            machine="virt",
            cpu="cortex-a15",
            gdb_port=3333,
            qmp_port=5555,
            start_paused=True,
            extra_args=[],
        )
        boot = BootConfig(kernel="k", initrd="i", append="quiet")
        res = QemuLiveEngine().run(make_platform(tmp_path, qemu=qemu, boot=boot))
        cmd = live_env.popen.call_args.args[0]
        assert cmd[cmd.index("-gdb") + 1] == "tcp::3333"
        assert cmd[cmd.index("-qmp") + 1] == "tcp:localhost:5555,server=on,wait=off"
        assert cmd[-9:] == [
            "-S",
            "-cpu",
            "cortex-a15",
            "-kernel",
            os.path.join(str(tmp_path), "k"),
            "-initrd",
            os.path.join(str(tmp_path), "i"),
            "-append",
            "quiet",
        ]
        live_env.gdb_cls.assert_called_once_with(arch="arm")
        assert res.stdout == "QEMU live session started (GDB:3333 QMP:5555)"

    def test_platform_without_extra_args(self, tmp_path, live_env):
        res = QemuLiveEngine().run(make_platform(tmp_path, arch="arm64"))
        assert res.success is True
        assert live_env.popen.call_args.args[0][-1] == "tcp:localhost:4444,server=on,wait=off"

    def test_process_exits_immediately(self, tmp_path, live_env):
        live_env.proc.poll.return_value = 1
        res = QemuLiveEngine().run(
            make_platform(tmp_path, arch="arm64", qemu=QemuConfig(extra_args=[]))
        )
        assert (res.success, res.stderr) == (False, "QEMU exited immediately")
        live_env.qmp.connect_tcp.assert_not_called()

    def test_protocol_failures_are_reported_but_session_starts(self, tmp_path, live_env):
        live_env.qmp.connect_tcp.side_effect = ConnectionRefusedError("qmp down")
        live_env.gdb.connect.side_effect = ConnectionRefusedError("gdb down")
        res = QemuLiveEngine().run(
            make_platform(tmp_path, arch="arm64", qemu=QemuConfig(extra_args=[]))
        )
        assert res.success is True
        assert "QMP connection failed: qmp down" in res.stderr
        assert "GDB connection failed: gdb down" in res.stderr

    def test_launch_error(self, tmp_path, live_env):
        live_env.popen.side_effect = PermissionError("denied")
        res = QemuLiveEngine().run(
            make_platform(tmp_path, arch="arm64", qemu=QemuConfig(extra_args=[]))
        )
        assert (res.success, res.stderr) == (False, "denied")

    def test_controls_delegate_to_clients(self):
        engine = QemuLiveEngine()
        assert (engine.pause(), engine.resume(), engine.step()) == (None, None, None)
        engine._qmp, engine._gdb = MagicMock(), MagicMock()
        engine._qmp.stop.return_value = {"return": {}}
        engine._qmp.cont.return_value = {"return": {"c": 1}}
        engine._gdb.step.return_value = "S05"
        assert engine.pause() == {"return": {}}
        assert engine.resume() == {"return": {"c": 1}}
        assert engine.step() == "S05"

    def test_stop_tears_everything_down(self):
        engine = QemuLiveEngine()
        bridge, gdb, qmp, proc = MagicMock(), MagicMock(), MagicMock(), MagicMock()
        qmp.quit.side_effect = OSError("already gone")
        engine._bridge, engine._gdb, engine._qmp, engine._process = bridge, gdb, qmp, proc
        engine.stop()
        bridge.stop_polling.assert_called_once()
        gdb.disconnect.assert_called_once()
        qmp.disconnect.assert_called_once()
        proc.terminate.assert_called_once()
        proc.wait.assert_called_once_with(timeout=5)
        proc.kill.assert_not_called()
        assert engine._process is None

    def test_stop_kills_unresponsive_process(self):
        engine = QemuLiveEngine()
        proc = MagicMock()
        proc.wait.side_effect = subprocess.TimeoutExpired(cmd="qemu", timeout=5)
        proc.kill.side_effect = ProcessLookupError
        engine._process = proc
        engine.stop()
        proc.kill.assert_called_once()
        assert engine._process is None
