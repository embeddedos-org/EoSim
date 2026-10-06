# SPDX-License-Identifier: MIT
"""CLI command behaviour against an isolated platform registry.

``PLATFORMS_DIR`` is pointed at a temporary tree so every command sees a
known set of platforms. Engines, integrations and subprocesses are replaced,
so no emulator, network service or hardware is touched.
"""

import os
import subprocess
import time
from unittest.mock import MagicMock

import pytest
import yaml
from click.testing import CliRunner

import eosim.cli.main as cli_main
from eosim.cli.main import cli
from eosim.integrations import ecosystem as eco
from eosim.integrations import eos_runner as er
from eosim.integrations.eos_runner import EosTestResult, EosTestSuite

PLATFORMS = {
    "renode-board": {
        "name": "renode-board",
        "arch": "arm",
        "engine": "renode",
        "resc": "sim.resc",
        "runtime": {"memory_mb": 1},
    },
    "qemu-board": {
        "name": "qemu-board",
        "arch": "arm64",
        "engine": "qemu",
        "qemu": {"machine": "virt", "cpu": "cortex-a57"},
        "runtime": {"memory_mb": 256},
    },
    "native-board": {
        "name": "native-board",
        "arch": "arm",
        "engine": "eosim",
        "runtime": {"memory_mb": 1},
    },
    "odd-board": {"name": "odd-board", "arch": "arm", "engine": "verilator"},
    "alias-dir": {"name": "different-name", "arch": "riscv64", "engine": "eosim"},
}


def write_yaml(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data), encoding="utf-8")


@pytest.fixture
def platforms(tmp_path, monkeypatch):
    root = tmp_path / "platforms"
    for dirname, data in PLATFORMS.items():
        write_yaml(root / dirname / "platform.yml", data)
    write_yaml(
        root / "native-board" / "tests.yml",
        {
            "checks": [
                {"type": "serial_contains", "value": "Booting"},
                {"type": "timeout", "seconds": 30},
            ]
        },
    )
    (root / "broken").mkdir()
    (root / "broken" / "platform.yml").write_text("name: [unclosed\n", encoding="utf-8")
    monkeypatch.setattr(cli_main, "PLATFORMS_DIR", root)
    monkeypatch.chdir(tmp_path)
    return root


@pytest.fixture
def invoke():
    runner = CliRunner()
    return lambda *args: runner.invoke(cli, list(args))


def tool_paths(monkeypatch, mapping):
    monkeypatch.setattr(cli_main.shutil, "which", lambda name: mapping.get(name))


@pytest.fixture
def fake_run(monkeypatch):
    run = MagicMock(return_value=subprocess.CompletedProcess([], 0, "renode boot ok\n", ""))
    monkeypatch.setattr(cli_main.subprocess, "run", run)
    return run


class TestPlatformLookup:
    def test_info_by_name(self, platforms, invoke):
        res = invoke("info", "qemu-board")
        assert res.exit_code == 0
        assert yaml.safe_load(res.output)["qemu"] == {"machine": "virt", "cpu": "cortex-a57"}

    def test_info_falls_back_to_directory_name(self, platforms, invoke):
        res = invoke("info", "alias-dir")
        assert res.exit_code == 0
        assert yaml.safe_load(res.output)["name"] == "different-name"

    def test_unparseable_platform_is_not_found(self, platforms, invoke):
        res = invoke("info", "broken")
        assert res.exit_code == 1
        assert "Platform not found: broken" in res.output

    def test_list_platforms_alias(self, platforms, invoke):
        res = invoke("list-platforms")
        assert res.exit_code == 0
        names = ["different-name", "native-board", "odd-board", "qemu-board", "renode-board"]
        assert "Available platforms (5):" in res.output
        positions = [res.output.index(f"  {n} ") for n in names]
        assert positions == sorted(positions)


class TestRunRenode:
    def test_missing_renode_falls_back_to_native(self, platforms, invoke, monkeypatch):
        tool_paths(monkeypatch, {})
        res = invoke("run", "renode-board", "--log-dir", "logs")
        assert "Renode not found. Install: https://renode.io" in res.output
        assert "Falling back to EoSim native engine..." in res.output
        assert "NO FIRMWARE" in res.output
        assert res.exit_code == 2

    def test_headless_run_passes_and_logs(self, platforms, invoke, monkeypatch, fake_run):
        tool_paths(monkeypatch, {"renode": "/opt/renode"})
        res = invoke("run", "renode-board", "--log-dir", "logs", "--timeout", "9")
        resc = str(platforms / "renode-board" / "sim.resc")
        assert fake_run.call_args.args[0] == [
            "/opt/renode",
            "--disable-xwt",
            "--plain",
            resc,
            "--hide-log",
        ]
        assert fake_run.call_args.kwargs["timeout"] == 9
        assert "EoSim: launching renode-board (arm) via renode" in res.output
        assert res.output.rstrip().endswith("PASSED")
        assert (platforms.parent / "logs" / "renode-board.log").read_text() == "renode boot ok\n"
        assert res.exit_code == 0

    def test_interactive_run_shows_log(self, platforms, invoke, monkeypatch, fake_run):
        tool_paths(monkeypatch, {"renode": "/opt/renode"})
        invoke("run", "renode-board", "--interactive", "--log-dir", "logs")
        assert "--hide-log" not in fake_run.call_args.args[0]

    def test_nonzero_exit_fails(self, platforms, invoke, monkeypatch, fake_run):
        tool_paths(monkeypatch, {"renode": "/opt/renode"})
        fake_run.return_value = subprocess.CompletedProcess([], 4, "", "error")
        res = invoke("run", "renode-board", "--log-dir", "logs")
        assert "FAILED (exit 4)" in res.output
        assert res.exit_code == 1

    def test_timeout_is_reported(self, platforms, invoke, monkeypatch, fake_run):
        tool_paths(monkeypatch, {"renode": "/opt/renode"})
        fake_run.side_effect = subprocess.TimeoutExpired(cmd="renode", timeout=5)
        res = invoke("run", "renode-board", "--log-dir", "logs", "--timeout", "5")
        assert "Timeout after 5s — saving log" in res.output
        assert res.exit_code == 0

    def test_exec_failure_falls_back_to_native(self, platforms, invoke, monkeypatch, fake_run):
        tool_paths(monkeypatch, {"renode": "/opt/renode"})
        fake_run.side_effect = FileNotFoundError
        res = invoke("run", "renode-board", "--log-dir", "logs")
        assert "Engine not found, falling back to EoSim native engine" in res.output
        assert res.exit_code == 2


class TestRunQemuAndNative:
    def test_qemu_missing_is_not_a_pass(self, platforms, invoke, monkeypatch, fake_run):
        asked = []
        monkeypatch.setattr(cli_main.shutil, "which", lambda n: asked.append(n))
        res = invoke("run", "qemu-board", "--log-dir", "logs")
        assert asked == ["qemu-system-aarch64"]
        assert "QEMU NOT INSTALLED for arm64 — nothing was executed." in res.output
        assert "Install: sudo apt install qemu-system-arm64, or pass --dry-run." in res.output
        assert "PASSED" not in res.output
        log = (platforms.parent / "logs" / "qemu-board.log").read_text(encoding="utf-8")
        assert log == "QEMU NOT INSTALLED for arm64 — nothing was executed.\n"
        assert res.exit_code == 2
        fake_run.assert_not_called()

    def test_qemu_dry_run_is_logged_and_not_executed(self, platforms, invoke, monkeypatch, fake_run):
        tool_paths(monkeypatch, {})
        res = invoke("run", "qemu-board", "--log-dir", "logs", "--dry-run")
        assert "DRY RUN — qemu was not executed." in res.output
        log = (platforms.parent / "logs" / "qemu-board.log").read_text(encoding="utf-8")
        assert log == (
            "DRY RUN — qemu was not executed (explicit --dry-run).\n"
            "qemu-system-aarch64 -machine virt -m 256 -nographic -no-reboot -cpu cortex-a57\n"
        )
        assert res.exit_code == 0
        fake_run.assert_not_called()

    def test_qemu_command_line_is_built_and_executed(
        self, platforms, invoke, monkeypatch, fake_run
    ):
        tool_paths(monkeypatch, {"qemu-system-aarch64": "/usr/bin/qemu-system-aarch64"})
        res = invoke("run", "qemu-board", "--log-dir", "logs")
        cmd = "/usr/bin/qemu-system-aarch64 -machine virt -m 256 -nographic -no-reboot -cpu cortex-a57"
        assert "Running: " + cmd in res.output
        fake_run.assert_called_once_with(cmd.split(), timeout=60, capture_output=True, text=True)
        assert "PASSED" in res.output
        assert res.exit_code == 0

    def test_unknown_engine(self, platforms, invoke):
        res = invoke("run", "odd-board", "--log-dir", "logs")
        assert "Unknown engine: verilator" in res.output
        assert res.exit_code == 1

    def test_native_failure_reports_reason_and_cycles(self, platforms, invoke, monkeypatch):
        from eosim.engine.native import VirtualMachine

        monkeypatch.setattr(
            VirtualMachine,
            "run",
            lambda self, **kw: {
                "success": False,
                "reason": "timeout",
                "cycles": 42,
                "boot_log": "x",
            },
        )
        res = invoke("run", "native-board", "--log-dir", "logs")
        assert "FAILED (timeout after 42 cycles)" in res.output
        assert res.exit_code == 1
        log = (platforms.parent / "logs" / "native-board.log").read_text()
        assert "Firmware: (none)" in log

    def test_native_firmware_load_failure(self, platforms, invoke, monkeypatch, tmp_path):
        from eosim.engine.native import VirtualMachine

        fw = tmp_path / "fw.bin"
        fw.write_bytes(b"\x00" * 8)
        monkeypatch.setattr(VirtualMachine, "load_firmware", lambda self, path: False)
        res = invoke("run", "native-board", "--log-dir", "logs", "--firmware", str(fw))
        assert f"Could not load firmware: {fw}" in res.output
        assert res.exit_code == 1


class TestTestAndValidate:
    def test_test_lists_checks_from_tests_yml(self, platforms, invoke):
        res = invoke("test", "native-board")
        assert "EoSim test: native-board (2 checks)" in res.output
        assert "  [CHECK] serial_contains: Booting" in res.output
        assert "  [CHECK] timeout: 30" in res.output

    def test_test_without_tests_yml(self, platforms, invoke):
        res = invoke("test", "qemu-board")
        assert "EoSim test: qemu-board (0 checks)" in res.output

    @pytest.fixture
    def validate_tree(self, tmp_path, monkeypatch):
        root = tmp_path / "vplatforms"
        write_yaml(
            root / "good" / "platform.yml", {"name": "good", "arch": "arm", "engine": "qemu"}
        )
        write_yaml(root / "templates" / "platform.yml", {"arch": "z80"})
        (root / "empty").mkdir()
        monkeypatch.setattr(cli_main, "PLATFORMS_DIR", root)
        return root

    def test_validate_all_passes(self, validate_tree, invoke):
        res = invoke("validate", "--all")
        assert res.output.strip() == "Validated: 1 passed, 0 failed"
        assert res.exit_code == 0

    def test_validate_all_reports_each_error(self, validate_tree, invoke):
        write_yaml(
            validate_tree / "bad" / "platform.yml",
            {"name": "bad", "arch": "z80", "engine": "magic"},
        )
        res = invoke("validate", "--all")
        assert (
            "FAILED: bad\n  ERROR: invalid arch: z80\n  ERROR: invalid engine: magic\n"
            in res.output
        )
        assert "Validated: 1 passed, 1 failed" in res.output
        assert res.exit_code == 1

    def test_validate_single_file(self, tmp_path, invoke):
        good = tmp_path / "ok.yml"
        write_yaml(good, {"name": "x", "arch": "riscv64", "engine": "renode"})
        res = invoke("validate", str(good))
        assert (res.exit_code, res.output.strip()) == (0, f"Valid: {good}")

    def test_validate_single_file_errors(self, tmp_path, invoke):
        bad = tmp_path / "bad.yml"
        write_yaml(bad, {"arch": "arm", "engine": "qemu", "domain": "cooking"})
        res = invoke("validate", str(bad))
        assert res.output.splitlines() == [
            "ERROR: missing required field: name",
            "ERROR: invalid domain: cooking",
        ]
        assert res.exit_code == 1


class TestSimulate:
    def test_qemu_missing_stops_before_nested_install(self, platforms, invoke, monkeypatch):
        tool_paths(monkeypatch, {})
        res = invoke("simulate", "--platform", "qemu-board", "--nested-install")
        assert "EoSim: simulating qemu-board (arm64) via qemu" in res.output
        assert "QEMU NOT INSTALLED for arm64" in res.output
        assert "Nested install" not in res.output
        assert (platforms.parent / "out" / "logs" / "qemu-board.log").exists()
        assert res.exit_code == 2

    def test_qemu_run_then_nested_install(self, platforms, invoke, monkeypatch, fake_run):
        tool_paths(monkeypatch, {"qemu-system-aarch64": "/usr/bin/qemu-system-aarch64"})
        res = invoke("simulate", "--platform", "qemu-board", "--nested-install")
        fake_run.assert_called_once()
        assert "Nested install test: simulated for qemu-board" in res.output
        assert res.exit_code == 0

    def test_duration_is_renode_timeout(self, platforms, invoke, monkeypatch, fake_run):
        tool_paths(monkeypatch, {"renode": "/opt/renode"})
        res = invoke("simulate", "--platform", "renode-board", "--duration", "7")
        assert fake_run.call_args.kwargs["timeout"] == 7
        assert "Nested install" not in res.output
        assert res.exit_code == 0

    def test_native_without_firmware(self, platforms, invoke):
        assert invoke("simulate", "--platform", "native-board").exit_code == 2

    def test_unknown_engine_and_missing_platform(self, platforms, invoke):
        res = invoke("simulate", "--platform", "odd-board")
        assert (res.exit_code, "Unknown engine: verilator" in res.output) == (1, True)
        res = invoke("simulate", "--platform", "nope")
        assert (res.exit_code, "Platform not found: nope" in res.output) == (1, True)


class TestDomainInfo:
    def test_domain_without_safety_levels(self, invoke):
        res = invoke("domain", "info", "consumer")
        assert res.exit_code == 0
        assert "Safety Levels" not in res.output
        assert "Test Scenarios:" in res.output


class TestEosCommands:
    def test_find(self, invoke, monkeypatch):
        monkeypatch.setattr(er, "find_eos_source", lambda: "/src/eos")
        assert invoke("eos", "find").output.strip() == "EoS source found: /src/eos"
        monkeypatch.setattr(er, "find_eos_source", lambda: None)
        assert "EoS source not found. Set EOS_SOURCE" in invoke("eos", "find").output

    def test_build_pass(self, invoke, monkeypatch):
        calls = []
        monkeypatch.setattr(er, "build_eos", lambda src: calls.append(src) or (True, "log"))
        res = invoke("eos", "build", "--source", "/src/eos")
        assert calls == ["/src/eos"]
        assert res.output.splitlines() == ["Building EoS from: /src/eos", "BUILD: PASSED"]

    def test_build_failure_shows_log_tail(self, invoke, monkeypatch):
        monkeypatch.setattr(er, "build_eos", lambda src: (False, "A" * 100 + "B" * 500))
        res = invoke("eos", "build", "--source", "/src/eos")
        assert "BUILD: FAILED" in res.output
        assert "B" * 500 in res.output and "A" not in res.output.split("BUILD: FAILED")[1]
        assert res.exit_code == 1

    def test_build_short_failure_log_printed_whole(self, invoke, monkeypatch):
        monkeypatch.setattr(er, "build_eos", lambda src: (False, "cmake: error"))
        res = invoke("eos", "build", "--source", "/s")
        assert res.output.splitlines()[-1] == "cmake: error"

    @pytest.mark.parametrize("subcommand", ["build", "test"])
    def test_source_not_found(self, invoke, monkeypatch, subcommand):
        monkeypatch.setattr(er, "find_eos_source", lambda: None)
        res = invoke("eos", subcommand)
        assert (res.exit_code, "EoS source not found" in res.output) == (1, True)

    def _suite(self, failing):
        suite = EosTestSuite(platform="eos-native", total=2, passed=2 - failing, failed=failing)
        suite.results = [
            EosTestResult("build", True, output="Build successful"),
            EosTestResult("test_x", not failing, output="x" * 400 + "TAIL"),
        ]
        return suite

    def test_test_failure_verbose_shows_failing_output(self, invoke, monkeypatch):
        monkeypatch.setattr(er, "run_eos_tests", lambda src: self._suite(failing=1))
        res = invoke("eos", "test", "--source", "/s", "-v")
        assert "EoSim Test Suite: eos-native" in res.output
        assert "--- test_x ---" in res.output and "--- build ---" not in res.output
        assert ("x" * 296 + "TAIL") in res.output and ("x" * 297 + "TAIL") not in res.output
        assert res.exit_code == 1

    def test_test_success(self, invoke, monkeypatch):
        monkeypatch.setattr(er, "run_eos_tests", lambda src: self._suite(failing=0))
        res = invoke("eos", "test", "--source", "/s", "--verbose")
        assert "---" not in res.output
        assert res.exit_code == 0

    def test_test_suite_with_source(self, invoke, monkeypatch, tmp_path):
        (tmp_path / "tests").mkdir()
        seen = []
        monkeypatch.setattr(
            er, "run_eosuite_tests", lambda src: seen.append(src) or EosTestSuite(platform="eapps")
        )
        res = invoke("eos", "test-suite", "--source", str(tmp_path))
        assert seen == [str(tmp_path)]
        assert f"EoSim: Testing eApps from: {tmp_path}" in res.output
        assert "EoSim Test Suite: eapps" in res.output

    def test_test_suite_not_found(self, invoke, monkeypatch, tmp_path):
        real_isdir = os.path.isdir
        monkeypatch.setattr(cli_main.os.path, "isdir", lambda p: "eApps" not in p and real_isdir(p))
        res = invoke("eos", "test-suite", "--source", str(tmp_path))  # no tests/ dir
        assert (res.exit_code, "eApps source not found" in res.output) == (1, True)


class TestEcosystem:
    @pytest.fixture
    def eco_env(self, monkeypatch):
        repos = {"eos": "/ws/eos", "eosim": "/ws/eosim"}
        monkeypatch.setattr(eco, "find_repos", lambda ws: dict(repos))
        monkeypatch.setattr(
            eco, "detect_kind", lambda path: "cmake" if path.endswith("eos") else "python"
        )
        report = MagicMock(repos_failed=0)
        report.summary.return_value = "ECOSYSTEM SUMMARY"
        run = MagicMock(return_value=report)
        monkeypatch.setattr(eco, "run_ecosystem_tests", run)
        return run, report

    def test_no_repos(self, invoke, monkeypatch):
        monkeypatch.setattr(eco, "find_repos", lambda ws: {})
        res = invoke("ecosystem")
        assert (res.exit_code, "No EoS repos found" in res.output) == (1, True)

    def test_list_only(self, invoke, eco_env):
        run, _ = eco_env
        res = invoke("ecosystem", "--list")
        lines = res.output.splitlines()
        assert "Found 2 repo(s):" in lines
        assert lines[lines.index("Found 2 repo(s):") + 1].split() == ["eos", "cmake"]
        assert lines[lines.index("Found 2 repo(s):") + 2].split() == ["eosim", "python"]
        run.assert_not_called()

    def test_only_unknown_repo(self, invoke, eco_env):
        res = invoke("ecosystem", "--only", "zzz")
        assert "Not in the workspace: zzz" in res.output
        assert "Available: eos, eosim" in res.output
        assert res.exit_code == 1

    def test_only_filters_and_runs(self, invoke, eco_env):
        run, _ = eco_env
        res = invoke("ecosystem", "--workspace", "/ws", "--only", "eos")
        assert "Found 1 repo(s):" in res.output
        run.assert_called_once_with("/ws", simulate=True, only=["eos"])
        assert "ECOSYSTEM SUMMARY" in res.output
        assert res.exit_code == 0

    def test_failures_set_exit_code(self, invoke, eco_env):
        run, report = eco_env
        report.repos_failed = 1
        res = invoke("ecosystem", "--no-simulate")
        run.assert_called_once_with(None, simulate=False, only=None)
        assert res.exit_code == 1


@pytest.fixture
def hil_session(monkeypatch):
    import eosim.integrations.hil_session as hs

    session = MagicMock()
    session.get_state.return_value = {"connected": True, "target": "stm32f4"}
    session.read_registers.return_value = {"r0": 1, "pc": 0x8000}
    monkeypatch.setattr(hs, "HILSession", MagicMock(return_value=session))
    return session


def interrupt_sleep(monkeypatch):
    def sleep(_):
        raise KeyboardInterrupt

    monkeypatch.setattr(time, "sleep", sleep)


class TestHIL:
    def test_detect_with_tools(self, invoke, monkeypatch):
        import eosim.integrations.openocd as oo
        import eosim.integrations.serial_bridge as sb

        monkeypatch.setattr(
            oo.OpenOCDManager, "find_openocd", staticmethod(lambda: "/usr/bin/openocd")
        )
        monkeypatch.setattr(sb.SerialBridge, "available", staticmethod(lambda: True))
        monkeypatch.setattr(
            sb.SerialBridge,
            "list_ports",
            staticmethod(lambda: [{"device": "/dev/ttyACM0", "description": "ST-Link"}]),
        )
        monkeypatch.setattr(
            sb.SerialBridge,
            "detect_dev_boards",
            staticmethod(lambda: [{"device": "/dev/ttyACM0", "board": "Nucleo"}]),
        )
        out = invoke("hil", "detect").output
        assert "OpenOCD: /usr/bin/openocd" in out
        assert "/dev/ttyACM0" in out and "ST-Link" in out
        assert "Detected Dev Boards:" in out and "Nucleo" in out

    def test_detect_without_tools(self, invoke, monkeypatch):
        import eosim.integrations.openocd as oo
        import eosim.integrations.serial_bridge as sb

        monkeypatch.setattr(oo.OpenOCDManager, "find_openocd", staticmethod(lambda: None))
        monkeypatch.setattr(sb.SerialBridge, "available", staticmethod(lambda: False))
        out = invoke("hil", "detect").output
        assert "OpenOCD: NOT FOUND" in out
        assert "pyserial not installed" in out

    def test_detect_no_ports(self, invoke, monkeypatch):
        import eosim.integrations.openocd as oo
        import eosim.integrations.serial_bridge as sb

        monkeypatch.setattr(oo.OpenOCDManager, "find_openocd", staticmethod(lambda: None))
        monkeypatch.setattr(sb.SerialBridge, "available", staticmethod(lambda: True))
        monkeypatch.setattr(sb.SerialBridge, "list_ports", staticmethod(lambda: []))
        monkeypatch.setattr(sb.SerialBridge, "detect_dev_boards", staticmethod(lambda: []))
        out = invoke("hil", "detect").output
        assert "(none found)" in out and "Detected Dev Boards" not in out

    def test_connect_until_interrupted(self, invoke, monkeypatch, hil_session):
        interrupt_sleep(monkeypatch)
        res = invoke(
            "hil",
            "connect",
            "--target",
            "nrf52",
            "--adapter",
            "jlink",
            "--serial",
            "/dev/ttyUSB0",
            "--gdb-port",
            "4000",
        )
        hil_session.start.assert_called_once_with(
            adapter="jlink",
            target="nrf52",
            serial_port="/dev/ttyUSB0",
            baudrate=115200,
            gdb_port=4000,
        )
        assert "Connected! GDB on port 4000" in res.output
        assert "Serial bridge: /dev/ttyUSB0 @ 115200 baud" in res.output
        assert "target" in res.output and "stm32f4" in res.output
        assert res.output.rstrip().endswith("Disconnected.")
        hil_session.stop.assert_called_once()
        assert res.exit_code == 0

    def test_connect_failure_still_stops_session(self, invoke, hil_session):
        hil_session.start.side_effect = RuntimeError("no probe")
        res = invoke("hil", "connect")
        assert "Connection failed: no probe" in res.output
        hil_session.stop.assert_called_once()
        assert res.exit_code == 1

    def test_monitor_prints_sorted_registers(self, invoke, monkeypatch, hil_session):
        interrupt_sleep(monkeypatch)
        res = invoke("hil", "monitor", "--target", "stm32h7")
        hil_session.halt.assert_called_once()
        assert "=== stm32h7 Registers ===" in res.output
        assert res.output.index("  pc     0x00008000") < res.output.index("  r0     0x00000001")
        hil_session.stop.assert_called_once()

    @pytest.mark.parametrize(
        "flash_result, text, code",
        [
            (True, "Flash: PASSED", 0),
            (False, "Flash: FAILED", 1),
            (OSError("usb"), "Flash error: usb", 1),
        ],
    )
    def test_flash(self, invoke, monkeypatch, tmp_path, flash_result, text, code):
        import eosim.integrations.openocd as oo

        fw = tmp_path / "fw.elf"
        fw.write_bytes(b"\x7fELF")
        mgr = MagicMock()
        if isinstance(flash_result, Exception):
            mgr.flash.side_effect = flash_result
        else:
            mgr.flash.return_value = flash_result
        monkeypatch.setattr(oo, "OpenOCDManager", MagicMock(return_value=mgr))
        res = invoke("hil", "flash", str(fw))
        mgr.flash.assert_called_once_with(str(fw))
        assert text in res.output
        assert res.exit_code == code


class TestBridgeCommands:
    @pytest.mark.parametrize(
        "group, module, cls_name, default_port, label",
        [
            ("xplane", "eosim.integrations.xplane", "XPlaneConnection", 49000, "X-Plane"),
            ("gazebo", "eosim.integrations.gazebo", "GazeboConnection", 11345, "Gazebo"),
        ],
    )
    def test_connect(self, invoke, monkeypatch, group, module, cls_name, default_port, label):
        import importlib

        conn = MagicMock()
        conn.connect.return_value = True
        conn.get_status.return_value = {"connected": True}
        cls = MagicMock(return_value=conn)
        monkeypatch.setattr(importlib.import_module(module), cls_name, cls)
        res = invoke("bridge", group, "connect")
        cls.assert_called_once_with(host="127.0.0.1", port=default_port)
        assert f"Connecting to {label} at 127.0.0.1:{default_port}..." in res.output
        assert f"Connected to {label}" in res.output
        conn.disconnect.assert_called_once()
        assert res.exit_code == 0

        conn.connect.return_value = False
        res = invoke("bridge", group, "connect", "--port", "1")
        assert f"Failed to connect to {label}" in res.output
        assert res.exit_code == 1

    def test_openfoam_success(self, invoke, monkeypatch):
        import eosim.integrations.openfoam as of

        runner = MagicMock()
        runner.run.return_value = {"success": True, "converged": True}
        monkeypatch.setattr(of, "OpenFOAMRunner", MagicMock(return_value=runner))
        res = invoke(
            "bridge", "openfoam", "run", "--case-dir", "/cases/cavity", "--solver", "icoFoam"
        )
        runner.set_solver.assert_called_once_with("icoFoam")
        assert "Running OpenFOAM solver 'icoFoam' on case: /cases/cavity" in res.output
        assert "Solver completed successfully\nSolution converged" in res.output
        assert res.exit_code == 0

    def test_openfoam_failure_shows_log_tail(self, invoke, monkeypatch):
        import eosim.integrations.openfoam as of

        runner = MagicMock()
        runner.run.return_value = {"success": False, "log": "z" * 10 + "FOAM FATAL ERROR"}
        monkeypatch.setattr(of, "OpenFOAMRunner", MagicMock(return_value=runner))
        res = invoke("bridge", "openfoam", "run", "--case-dir", "/c")
        assert "Solver failed" in res.output and "FOAM FATAL ERROR" in res.output
        assert res.exit_code == 1


class TestApiCommand:
    @pytest.mark.parametrize(
        "args, url",
        [
            ((), "http://localhost:8080/docs"),
            (("--host", "127.0.0.1", "--port", "9000"), "http://127.0.0.1:9000/docs"),
        ],
    )
    def test_starts_server(self, invoke, monkeypatch, args, url):
        import eosim.api.server as srv

        server = MagicMock()
        cls = MagicMock(return_value=server)
        monkeypatch.setattr(srv, "EoSimAPIServer", cls)
        res = invoke("api", *args)
        assert f"Swagger UI: {url}" in res.output
        server.run.assert_called_once()
        host = args[1] if args else "0.0.0.0"
        port = int(args[3]) if args else 8080
        cls.assert_called_once_with(host=host, port=port)
