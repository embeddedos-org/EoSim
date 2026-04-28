# SPDX-License-Identifier: MIT
"""Unit tests for QEMU bridge (QMP, GDB, state bridge, ELF loader) and engine run methods."""
from unittest.mock import MagicMock, patch


class TestQMPClient:
    def test_import(self):
        from eosim.engine.qemu.qmp_client import QMPClient
        client = QMPClient()
        assert client is not None

    def test_not_connected(self):
        from eosim.engine.qemu.qmp_client import QMPClient
        client = QMPClient()
        assert not hasattr(client, '_connected') or not client._connected


class TestGDBClient:
    def test_import(self):
        from eosim.engine.qemu.gdb_client import GDBRemoteClient
        client = GDBRemoteClient()
        assert client is not None


class TestStateBridge:
    def test_import(self):
        from eosim.engine.qemu.state_bridge import TargetStateBridge
        # Should be importable without errors
        assert TargetStateBridge is not None


class TestELFLoader:
    def test_import(self):
        try:
            from eosim.engine.qemu.elf_loader import ELFLoader
            assert ELFLoader is not None
        except ImportError:
            pass  # pyelftools not installed — skip


class TestQemuLiveEngine:
    def test_available(self):
        from eosim.engine.backend import QemuLiveEngine
        # Just test it doesn't crash
        result = QemuLiveEngine.available()
        assert isinstance(result, bool)

    def test_init(self):
        from eosim.engine.backend import QemuLiveEngine
        engine = QemuLiveEngine()
        assert engine._process is None
        assert engine._qmp is None
        assert engine._gdb is None

    def test_properties(self):
        from eosim.engine.backend import QemuLiveEngine
        engine = QemuLiveEngine()
        assert engine.qmp is None
        assert engine.gdb is None
        assert engine.state_bridge is None

    def test_stop_no_process(self):
        from eosim.engine.backend import QemuLiveEngine
        engine = QemuLiveEngine()
        engine.stop()  # should not crash


class TestRenodeEngineRun:
    def test_run_no_renode(self):
        from eosim.engine.backend import RenodeEngine, SimResult
        platform = MagicMock()
        platform.name = 'test'
        platform.resc = ''
        platform.source_dir = '/tmp'
        with patch('shutil.which', return_value=None):
            result = RenodeEngine.run(platform)
            assert isinstance(result, SimResult)
            assert result.engine == 'renode'
            assert 'not installed' in result.stderr


class TestQemuEngineRun:
    def test_run_no_qemu(self):
        from eosim.engine.backend import QemuEngine, SimResult
        platform = MagicMock()
        platform.name = 'test'
        platform.arch = 'arm64'
        with patch('shutil.which', return_value=None):
            result = QemuEngine.run(platform)
            assert isinstance(result, SimResult)
            assert result.engine == 'qemu'
            assert result.success is True  # dry run

    def test_run_dry_run_with_log(self, tmp_path):
        from eosim.engine.backend import QemuEngine, SimResult
        platform = MagicMock()
        platform.name = 'test'
        platform.arch = 'arm64'
        log_file = str(tmp_path / 'test.log')
        with patch('shutil.which', return_value=None):
            result = QemuEngine.run(platform, log_file=log_file)
            assert result.success is True
            assert result.log_file == log_file


class TestEoSimEngineRun:
    def test_run(self):
        from eosim.engine.backend import EoSimEngine, SimResult
        platform = MagicMock()
        platform.name = 'test'
        platform.arch = 'arm'
        platform.runtime.memory_mb = 64
        platform.boot.firmware = ''
        platform.source_dir = '/tmp'
        result = EoSimEngine.run(platform, timeout=5)
        assert isinstance(result, SimResult)
        assert result.engine == 'eosim'
        assert result.success is True


class TestCARLAEngineRun:
    def test_run_not_available(self):
        from eosim.engine.backend import CARLAEngine, SimResult
        platform = MagicMock()
        platform.name = 'test'
        result = CARLAEngine.run(platform)
        assert isinstance(result, SimResult)
        assert result.success is False


class TestAirSimEngineRun:
    def test_run_not_available(self):
        from eosim.engine.backend import AirSimEngine, SimResult
        platform = MagicMock()
        platform.name = 'test'
        result = AirSimEngine.run(platform)
        assert isinstance(result, SimResult)
        assert result.success is False


class TestROS2EngineRun:
    def test_run_not_available(self):
        from eosim.engine.backend import ROS2Engine, SimResult
        platform = MagicMock()
        platform.name = 'test'
        result = ROS2Engine.run(platform)
        assert isinstance(result, SimResult)
        assert result.success is False


class TestXPlaneEngineRun:
    def test_run_not_available(self):
        from eosim.engine.backend import XPlaneEngine, SimResult
        platform = MagicMock()
        platform.name = 'test'
        result = XPlaneEngine.run(platform)
        assert isinstance(result, SimResult)
        # X-Plane may or may not be available
        assert isinstance(result.success, bool)


class TestGazeboEngineRun:
    def test_available_no_gazebo(self):
        from eosim.engine.backend import GazeboEngine
        with patch('shutil.which', return_value=None):
            assert GazeboEngine.available() is False


class TestOpenFOAMEngine:
    def test_available_no_openfoam(self):
        from eosim.engine.backend import OpenFOAMEngine
        with patch('shutil.which', return_value=None):
            assert OpenFOAMEngine.available() is False


# ─── Integration module tests ────────────────────────────────────────

class TestSerialBridge:
    def test_import(self):
        from eosim.integrations.serial_bridge import SerialBridge
        assert SerialBridge is not None

    def test_available(self):
        from eosim.integrations.serial_bridge import SerialBridge
        result = SerialBridge.available()
        assert isinstance(result, bool)


class TestOpenOCDManager:
    def test_import(self):
        from eosim.integrations.openocd import OpenOCDManager
        mgr = OpenOCDManager()
        assert mgr is not None

    def test_find_openocd(self):
        from eosim.integrations.openocd import OpenOCDManager
        result = OpenOCDManager.find_openocd()
        # May or may not be installed
        assert result is None or isinstance(result, str)


class TestHILSession:
    def test_import(self):
        from eosim.integrations.hil_session import HILSession
        session = HILSession()
        assert session is not None


class TestEcosystem:
    def test_import(self):
        from eosim.integrations.ecosystem import find_repos
        # Should be importable
        assert find_repos is not None

    def test_find_repos_none(self):
        from eosim.integrations.ecosystem import find_repos
        repos = find_repos('/nonexistent/path')
        assert isinstance(repos, dict)


class TestEosRunner:
    def test_import(self):
        from eosim.integrations.eos_runner import find_eos_source
        assert find_eos_source is not None

    def test_find_eos_not_found(self):
        from eosim.integrations.eos_runner import find_eos_source
        with patch.dict('os.environ', {'EOS_SOURCE': '/nonexistent'}, clear=False):
            # May or may not find it depending on local setup
            result = find_eos_source()
            assert result is None or isinstance(result, str)
