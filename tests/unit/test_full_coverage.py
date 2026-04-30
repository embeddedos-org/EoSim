# SPDX-License-Identifier: MIT
"""Complete test coverage for engine backends, integrations, API, plugins, codegen, network."""
from unittest.mock import MagicMock, patch
import pytest


# =============================================================================
# Engine Backend Tests
# =============================================================================

class TestSimResult:
    def test_defaults(self):
        from eosim.engine.backend import SimResult
        r = SimResult()
        assert r.success is False
        assert r.exit_code == -1
        assert r.artifacts == []
        assert r.engine == ""

    def test_with_values(self):
        from eosim.engine.backend import SimResult
        r = SimResult(success=True, engine='eosim', platform='stm32f4', stdout='boot ok')
        assert r.success is True
        assert r.engine == 'eosim'
        assert r.platform == 'stm32f4'

    def test_boot_detection(self):
        from eosim.engine.backend import SimResult
        r = SimResult(stdout="kernel booted successfully login:")
        r.boot_detected = "login:" in r.stdout
        assert r.boot_detected is True

    def test_no_boot(self):
        from eosim.engine.backend import SimResult
        r = SimResult(stdout="nothing here")
        r.boot_detected = "login:" in r.stdout
        assert r.boot_detected is False


class TestRenodeEngine:
    def test_available_missing(self):
        from eosim.engine.backend import RenodeEngine
        with patch('shutil.which', return_value=None):
            assert RenodeEngine.available() is False

    def test_available_found(self):
        from eosim.engine.backend import RenodeEngine
        with patch('shutil.which', return_value='/usr/bin/renode'):
            assert RenodeEngine.available() is True


class TestQemuEngine:
    def test_available_missing(self):
        from eosim.engine.backend import QemuEngine
        with patch('shutil.which', return_value=None):
            assert QemuEngine.available('arm64') is False

    def test_available_found(self):
        from eosim.engine.backend import QemuEngine
        with patch('shutil.which', return_value='/usr/bin/qemu-system-aarch64'):
            assert QemuEngine.available('arm64') is True

    def test_arch_map(self):
        from eosim.engine.backend import QemuEngine
        assert QemuEngine.ARCH_MAP['arm64'] == 'qemu-system-aarch64'
        assert QemuEngine.ARCH_MAP['arm'] == 'qemu-system-arm'
        assert QemuEngine.ARCH_MAP['riscv64'] == 'qemu-system-riscv64'
        assert QemuEngine.ARCH_MAP['x86_64'] == 'qemu-system-x86_64'


class TestEoSimEngine:
    def test_always_available(self):
        from eosim.engine.backend import EoSimEngine
        assert EoSimEngine.available() is True


class TestCARLAEngine:
    def test_not_available(self):
        from eosim.engine.backend import CARLAEngine
        assert CARLAEngine.available() is False  # no CARLA running locally


class TestAirSimEngine:
    def test_not_available(self):
        from eosim.engine.backend import AirSimEngine
        assert AirSimEngine.available() is False


class TestROS2Engine:
    def test_not_available(self):
        from eosim.engine.backend import ROS2Engine
        assert ROS2Engine.available() is False


class TestGetEngine:
    def test_eosim_engine(self):
        from eosim.engine.backend import get_engine, EoSimEngine
        from unittest.mock import MagicMock
        platform = MagicMock()
        platform.engine = 'eosim'
        platform.arch = 'arm'
        engine = get_engine(platform)
        assert engine is not None
        assert hasattr(engine, 'run')

    def test_fallback_to_qemu(self):
        from eosim.engine.backend import get_engine
        platform = MagicMock()
        platform.engine = 'unknown'
        platform.arch = 'arm'
        engine = get_engine(platform)
        assert engine is not None
        assert hasattr(engine, 'run')


# =============================================================================
# Integration Bridge Tests
# =============================================================================

class TestCARLAConnection:
    def test_init(self):
        from eosim.integrations.carla import CARLAConnection
        conn = CARLAConnection()
        assert conn.host == '127.0.0.1'
        assert conn.port == 2000
        assert conn._connected is False

    def test_disconnect(self):
        from eosim.integrations.carla import CARLAConnection
        conn = CARLAConnection()
        conn.disconnect()
        assert conn._connected is False

    def test_get_world_state_disconnected(self):
        from eosim.integrations.carla import CARLAConnection
        conn = CARLAConnection()
        state = conn.get_world_state()
        assert state == {}

    def test_get_sensor_data(self):
        from eosim.integrations.carla import CARLAConnection
        conn = CARLAConnection()
        data = conn.get_sensor_data()
        assert data == {}


class TestAirSimConnection:
    def test_init(self):
        from eosim.integrations.airsim import AirSimConnection
        conn = AirSimConnection()
        assert conn.host == '127.0.0.1'
        assert conn.port == 41451
        assert conn.vehicle_type == 'multirotor'

    def test_disconnect(self):
        from eosim.integrations.airsim import AirSimConnection
        conn = AirSimConnection()
        conn.disconnect()
        assert conn._connected is False

    def test_get_state(self):
        from eosim.integrations.airsim import AirSimConnection
        conn = AirSimConnection()
        state = conn.get_state()
        assert state['connected'] is False

    def test_get_imu_data(self):
        from eosim.integrations.airsim import AirSimConnection
        conn = AirSimConnection()
        data = conn.get_imu_data()
        assert 'angular_velocity' in data

    def test_get_gps_data(self):
        from eosim.integrations.airsim import AirSimConnection
        conn = AirSimConnection()
        data = conn.get_gps_data()
        assert 'latitude' in data


class TestROS2Bridge:
    def test_init(self):
        from eosim.integrations.ros2 import ROS2Bridge
        bridge = ROS2Bridge()
        assert bridge.node_name == 'eosim_bridge'
        assert bridge._connected is False

    def test_disconnect(self):
        from eosim.integrations.ros2 import ROS2Bridge
        bridge = ROS2Bridge()
        bridge.disconnect()
        assert bridge._connected is False


class TestVerilatorBridge:
    def test_init(self):
        from eosim.integrations.verilator import VerilatorBridge
        bridge = VerilatorBridge()
        assert bridge.loaded is False
        assert bridge.signals == {}

    def test_load_missing_file(self):
        from eosim.integrations.verilator import VerilatorBridge
        bridge = VerilatorBridge()
        assert bridge.load_vcd('/nonexistent/path.vcd') is False

    def test_list_signals_empty(self):
        from eosim.integrations.verilator import VerilatorBridge
        bridge = VerilatorBridge()
        assert bridge.list_signals() == []

    def test_get_signal_none(self):
        from eosim.integrations.verilator import VerilatorBridge
        bridge = VerilatorBridge()
        assert bridge.get_signal('clk') is None


class TestMATLABBridge:
    def test_init(self):
        from eosim.integrations.matlab import MATLABBridge
        bridge = MATLABBridge()
        assert bridge._connected is False
        assert bridge._engine is None

    def test_connect_no_matlab(self):
        from eosim.integrations.matlab import MATLABBridge
        bridge = MATLABBridge()
        assert bridge.connect() is False

    def test_eval_disconnected(self):
        from eosim.integrations.matlab import MATLABBridge
        bridge = MATLABBridge()
        assert bridge.eval('1+1') is None

    def test_disconnect(self):
        from eosim.integrations.matlab import MATLABBridge
        bridge = MATLABBridge()
        bridge.disconnect()
        assert bridge._connected is False


class TestNS3Bridge:
    def test_init(self):
        from eosim.integrations.ns3 import NS3Bridge
        bridge = NS3Bridge()
        assert bridge.ns3_dir == ''

    def test_available_no_ns3(self):
        from eosim.integrations.ns3 import NS3Bridge
        bridge = NS3Bridge()
        with patch('shutil.which', return_value=None):
            assert bridge.available() is False


class TestDockerSimRunner:
    def test_init(self):
        from eosim.integrations.docker_sim import DockerSimRunner
        runner = DockerSimRunner()
        assert isinstance(runner._available, bool)

    def test_available(self):
        from eosim.integrations.docker_sim import DockerSimRunner
        runner = DockerSimRunner()
        # May or may not have Docker
        assert isinstance(runner.available(), bool)


# =============================================================================
# API Tests
# =============================================================================

class TestAPIServer:
    def test_init(self):
        from eosim.api.server import EoSimAPIServer
        server = EoSimAPIServer(host='127.0.0.1', port=9090)
        assert server.host == '127.0.0.1'
        assert server.port == 9090

    def test_simulations_management(self):
        from eosim.api.server import EoSimAPIServer
        server = EoSimAPIServer()
        server.add_simulation('test', {'state': 'idle'})
        assert server.get_simulation('test') == {'state': 'idle'}
        assert 'test' in server.list_simulations()
        assert server.get_simulation('nonexistent') is None

    def test_list_simulations_empty(self):
        from eosim.api.server import EoSimAPIServer
        server = EoSimAPIServer()
        assert server.list_simulations() == []


# =============================================================================
# Plugin Tests
# =============================================================================

class TestPluginBase:
    def test_get_info(self):
        from eosim.plugins.base import PluginBase

        class TestPlugin(PluginBase):
            NAME = "test-plugin"
            VERSION = "1.0.0"
            DESCRIPTION = "A test plugin"
            def on_load(self):
                pass

        p = TestPlugin()
        info = p.get_info()
        assert info['name'] == 'test-plugin'
        assert info['version'] == '1.0.0'
        assert info['enabled'] is True

    def test_on_tick_default(self):
        from eosim.plugins.base import PluginBase

        class TestPlugin(PluginBase):
            def on_load(self): pass

        p = TestPlugin()
        p.on_tick(None, {})  # should not raise

    def test_on_unload_default(self):
        from eosim.plugins.base import PluginBase

        class TestPlugin(PluginBase):
            def on_load(self): pass

        p = TestPlugin()
        p.on_unload()  # should not raise

    def test_on_scenario_load_default(self):
        from eosim.plugins.base import PluginBase

        class TestPlugin(PluginBase):
            def on_load(self): pass

        p = TestPlugin()
        p.on_scenario_load(None, 'test')  # should not raise


class TestPluginLoader:
    def test_init(self):
        from eosim.plugins.loader import PluginLoader
        loader = PluginLoader()
        assert loader.plugins == {}

    def test_discover_empty(self, tmp_path):
        from eosim.plugins.loader import PluginLoader
        loader = PluginLoader(plugin_dirs=[str(tmp_path)])
        loader.discover()
        assert loader.plugins == {}

    def test_discover_with_plugin(self, tmp_path):
        from eosim.plugins.loader import PluginLoader
        plugin_file = tmp_path / "my_plugin.py"
        plugin_file.write_text("""
from eosim.plugins.base import PluginBase

class MyPlugin(PluginBase):
    NAME = "my-plugin"
    VERSION = "0.1.0"
    DESCRIPTION = "test"
    def on_load(self):
        pass
""")
        loader = PluginLoader(plugin_dirs=[str(tmp_path)])
        loader.discover()
        assert 'my-plugin' in loader.plugins

    def test_load_all(self, tmp_path):
        from eosim.plugins.loader import PluginLoader
        plugin_file = tmp_path / "loadable.py"
        plugin_file.write_text("""
from eosim.plugins.base import PluginBase

class LoadablePlugin(PluginBase):
    NAME = "loadable"
    VERSION = "1.0.0"
    loaded = False
    def on_load(self):
        self.__class__.loaded = True
""")
        loader = PluginLoader(plugin_dirs=[str(tmp_path)])
        loader.discover()
        loader.load_all()
        assert loader.plugins['loadable'].__class__.loaded is True

    def test_list_plugins(self):
        from eosim.plugins.loader import PluginLoader
        loader = PluginLoader()
        info = loader.list_plugins()
        assert isinstance(info, dict)

    def test_get_plugin_missing(self):
        from eosim.plugins.loader import PluginLoader
        loader = PluginLoader()
        assert loader.get_plugin('nonexistent') is None


# =============================================================================
# Code Generation Tests
# =============================================================================

class TestCodeGenerator:
    def test_generate_peripheral_driver(self):
        from eosim.codegen.generator import CodeGenerator
        gen = CodeGenerator()

        class FakePeripheral:
            name = 'temp0'
            base = 0x40100000

        result = gen.generate_peripheral_driver(FakePeripheral())
        assert 'header' in result
        assert 'source' in result
        assert 'TEMP0_BASE' in result['header']
        assert '0x40100000' in result['header']
        assert 'temp0_init' in result['source']
        assert 'temp0_read' in result['source']
        assert 'temp0_write' in result['source']

    def test_write_files(self, tmp_path):
        from eosim.codegen.generator import CodeGenerator
        gen = CodeGenerator(output_dir=str(tmp_path / 'gen'))
        written = gen.write_files({'test.h': '// header', 'test.c': '// source'})
        assert len(written) == 2
        assert (tmp_path / 'gen' / 'test.h').exists()
        assert (tmp_path / 'gen' / 'test.c').exists()


# =============================================================================
# Network Topology Tests
# =============================================================================

class TestNetworkNode:
    def test_init(self):
        from eosim.network.topology import NetworkNode
        node = NetworkNode('n1', '10.0.0.1', 'router')
        assert node.name == 'n1'
        assert node.ip == '10.0.0.1'
        assert node.node_type == 'router'
        assert node.packets_sent == 0


class TestNetworkTopology:
    def test_add_nodes_and_links(self):
        from eosim.network.topology import NetworkTopology, NetworkNode
        topo = NetworkTopology()
        topo.add_node(NetworkNode('a', '10.0.0.1'))
        topo.add_node(NetworkNode('b', '10.0.0.2'))
        topo.add_node(NetworkNode('c', '10.0.0.3'))
        topo.add_link('a', 'b', bandwidth_mbps=1000, latency_ms=0.5)
        topo.add_link('b', 'c')

        t = topo.get_topology()
        assert len(t['nodes']) == 3
        assert len(t['links']) == 2
        assert 'b' in topo.nodes['a'].connections

    def test_send_packet(self):
        from eosim.network.topology import NetworkTopology, NetworkNode
        topo = NetworkTopology()
        topo.add_node(NetworkNode('src'))
        topo.add_node(NetworkNode('dst'))
        topo.send_packet('src', 'dst', size_bytes=1500)
        assert topo.nodes['src'].packets_sent == 1
        assert topo.nodes['dst'].packets_received == 1

    def test_send_packet_unknown(self):
        from eosim.network.topology import NetworkTopology
        topo = NetworkTopology()
        topo.send_packet('x', 'y')  # should not raise


# =============================================================================
# Schema Validation Tests
# =============================================================================

class TestSchemaValidation:
    def test_valid_platform(self):
        from eosim.core.schema import validate_platform
        data = {'name': 'test', 'arch': 'arm', 'engine': 'eosim'}
        errors = validate_platform(data)
        assert errors == []

    def test_missing_name(self):
        from eosim.core.schema import validate_platform
        errors = validate_platform({'arch': 'arm', 'engine': 'eosim'})
        assert any('name' in e for e in errors)

    def test_missing_arch(self):
        from eosim.core.schema import validate_platform
        errors = validate_platform({'name': 'x', 'engine': 'eosim'})
        assert any('arch' in e for e in errors)

    def test_missing_engine(self):
        from eosim.core.schema import validate_platform
        errors = validate_platform({'name': 'x', 'arch': 'arm'})
        assert any('engine' in e for e in errors)

    def test_invalid_arch(self):
        from eosim.core.schema import validate_platform
        errors = validate_platform({'name': 'x', 'arch': 'invalid', 'engine': 'eosim'})
        assert any('arch' in e for e in errors)

    def test_invalid_engine(self):
        from eosim.core.schema import validate_platform
        errors = validate_platform({'name': 'x', 'arch': 'arm', 'engine': 'fake'})
        assert any('engine' in e for e in errors)

    def test_invalid_domain(self):
        from eosim.core.schema import validate_platform
        errors = validate_platform({'name': 'x', 'arch': 'arm', 'engine': 'eosim', 'domain': 'xyz'})
        assert any('domain' in e for e in errors)

    def test_invalid_class(self):
        from eosim.core.schema import validate_platform
        errors = validate_platform({'name': 'x', 'arch': 'arm', 'engine': 'eosim', 'class': 'xyz'})
        assert any('class' in e for e in errors)

    def test_invalid_modeling(self):
        from eosim.core.schema import validate_platform
        errors = validate_platform({'name': 'x', 'arch': 'arm', 'engine': 'eosim', 'modeling': 'xyz'})
        assert any('modeling' in e for e in errors)

    def test_all_new_arches_valid(self):
        from eosim.core.schema import VALID_ARCHES, validate_platform
        for arch in VALID_ARCHES:
            errors = validate_platform({'name': 'test', 'arch': arch, 'engine': 'eosim'})
            assert errors == [], f"Arch {arch} failed validation"

    def test_all_new_engines_valid(self):
        from eosim.core.schema import VALID_ENGINES, validate_platform
        for engine in VALID_ENGINES:
            errors = validate_platform({'name': 'test', 'arch': 'arm', 'engine': engine})
            assert errors == [], f"Engine {engine} failed validation"

    def test_all_new_domains_valid(self):
        from eosim.core.schema import VALID_DOMAINS, validate_platform
        for domain in VALID_DOMAINS:
            errors = validate_platform({'name': 'test', 'arch': 'arm', 'engine': 'eosim', 'domain': domain})
            assert errors == [], f"Domain {domain} failed validation"


# =============================================================================
# Domain Catalog Tests
# =============================================================================

class TestDomainCatalog:
    def test_list_domains(self):
        from eosim.core.domains import list_domains
        domains = list_domains()
        assert len(domains) >= 40
        assert 'automotive' in domains
        assert 'nuclear' in domains
        assert 'quantum' in domains
        assert 'ar-vr' in domains

    def test_get_domain(self):
        from eosim.core.domains import get_domain
        d = get_domain('automotive')
        assert d is not None
        assert d.display_name == 'Automotive / Transportation'
        assert 'ISO 26262' in d.standards
        assert 'ASIL-D' in d.safety_levels

    def test_get_domain_none(self):
        from eosim.core.domains import get_domain
        assert get_domain('nonexistent') is None

    def test_all_domains_have_standards(self):
        from eosim.core.domains import DOMAIN_CATALOG
        for name, d in DOMAIN_CATALOG.items():
            assert d.name == name
            assert len(d.display_name) > 0
            assert len(d.description) > 0
            assert isinstance(d.standards, list)
            assert isinstance(d.test_scenarios, list)
            assert len(d.test_scenarios) >= 3, f"Domain {name} has < 3 test scenarios"

    def test_all_domains_have_typical_arches(self):
        from eosim.core.domains import DOMAIN_CATALOG
        from eosim.core.schema import VALID_ARCHES
        for name, d in DOMAIN_CATALOG.items():
            for arch in d.typical_arches:
                assert arch in VALID_ARCHES, f"Domain {name} has invalid arch: {arch}"


# =============================================================================
# Wireless Peripheral Tests
# =============================================================================

class TestWirelessExtended:
    def test_nfc(self):
        from eosim.engine.native.peripherals.wireless_extended import NFCController
        c = NFCController()
        c.simulate_tick()
        assert c.tag_present is False

    def test_uwb(self):
        from eosim.engine.native.peripherals.wireless_extended import UWBController
        c = UWBController()
        c.simulate_tick()

    def test_satellite_comm(self):
        from eosim.engine.native.peripherals.wireless_extended import SatelliteComm
        c = SatelliteComm()
        c.simulate_tick()

    def test_lte_cat_m1(self):
        from eosim.engine.native.peripherals.wireless_extended import LTECatM1
        c = LTECatM1()
        c.simulate_tick()

    def test_nbiot(self):
        from eosim.engine.native.peripherals.wireless_extended import NBIoT
        c = NBIoT()
        c.simulate_tick()

    def test_thread(self):
        from eosim.engine.native.peripherals.wireless_extended import ThreadController
        c = ThreadController()
        assert c.role == 'detached'
        c.simulate_tick()

    def test_matter(self):
        from eosim.engine.native.peripherals.wireless_extended import MatterController
        c = MatterController()
        assert c.commissioned is False
        c.simulate_tick()


# =============================================================================
# Industrial Bus Tests
# =============================================================================

class TestIndustrialBuses:
    def test_ethercat(self):
        from eosim.engine.native.peripherals.buses_industrial import EtherCATController
        c = EtherCATController()
        c.state = 'OP'
        c.simulate_tick()
        assert c.pdo_count == 1

    def test_profinet(self):
        from eosim.engine.native.peripherals.buses_industrial import PROFINETController
        c = PROFINETController()
        c.simulate_tick()

    def test_modbus_tcp(self):
        from eosim.engine.native.peripherals.buses_industrial import ModbusTCPController
        c = ModbusTCPController()
        c.write_holding(0, [100, 200, 300])
        assert c.read_holding(0, 3) == [100, 200, 300]

    def test_opcua(self):
        from eosim.engine.native.peripherals.buses_industrial import OPCUAServer
        c = OPCUAServer()
        c.add_node('ns=2;i=1', 42.0)
        assert c.get_node('ns=2;i=1') == 42.0
        assert c.get_node('nonexistent') is None

    def test_hart(self):
        from eosim.engine.native.peripherals.buses_industrial import HARTController
        c = HARTController()
        c.set_current(12.0)
        assert c.current_ma == 12.0
        c.set_current(25.0)
        assert c.current_ma == 20.0  # clamped


# =============================================================================
# Network Bus Tests
# =============================================================================

class TestNetworkBuses:
    def test_ethernet_mac(self):
        from eosim.engine.native.peripherals.buses_network import EthernetMAC
        c = EthernetMAC()
        c.link_up = True
        c.simulate_tick()
        assert c.rx_packets == 1

    def test_usb_controller(self):
        from eosim.engine.native.peripherals.buses_network import USBController
        c = USBController()
        c.simulate_tick()

    def test_pcie_controller(self):
        from eosim.engine.native.peripherals.buses_network import PCIeController
        c = PCIeController()
        assert c.lanes == 4
        c.simulate_tick()

    def test_hdmi_controller(self):
        from eosim.engine.native.peripherals.buses_network import HDMIController
        c = HDMIController()
        assert c.cec_enabled is True
        c.simulate_tick()

    def test_i2s_controller(self):
        from eosim.engine.native.peripherals.buses_network import I2SController
        c = I2SController()
        assert c.sample_rate == 48000
        c.simulate_tick()


# =============================================================================
# GUI Renderer Tests
# =============================================================================

class TestRenderers:
    def test_registry_populated(self):
        from eosim.gui.renderers import list_renderers
        renderers = list_renderers()
        assert len(renderers) >= 20

    def test_get_known_renderer(self):
        from eosim.gui.renderers import get_renderer
        r = get_renderer('automotive')
        assert r.DOMAIN == 'automotive'

    def test_get_fallback_renderer(self):
        from eosim.gui.renderers import get_renderer
        r = get_renderer('nonexistent_domain')
        assert r.DOMAIN == 'generic'

    def test_new_domain_renderers_exist(self):
        from eosim.gui.renderers import get_renderer
        for domain in ['telecom', 'railway', 'agriculture', 'maritime', 'mining',
                        'nuclear', 'hvac', 'traffic', 'logistics', 'ar-vr',
                        'cybersecurity', 'water', 'oil-gas', 'smart-city']:
            r = get_renderer(domain)
            assert r.DOMAIN == domain, f"Renderer for {domain} not found"


# =============================================================================
# Digital Twin Tests (extended)
# =============================================================================

class TestDigitalTwinExtended:
    def _make_twin(self):
        class FakeSim:
            tick_count = 0
            def get_state(self): return {'v': self.tick_count}
            def tick(self): self.tick_count += 1
        from eosim.digital_twin.twin import DigitalTwin
        return DigitalTwin('test', FakeSim())

    def test_sync_multiple(self):
        twin = self._make_twin()
        for _ in range(5):
            twin.sync()
        assert len(twin.history) == 5

    def test_history_limit(self):
        twin = self._make_twin()
        for _ in range(100):
            twin.sync()
        assert len(twin.history) <= 10000

    def test_get_history(self):
        twin = self._make_twin()
        for _ in range(10):
            twin.sync()
        h = twin.get_history(last_n=3)
        assert len(h) == 3

    def test_status(self):
        twin = self._make_twin()
        s = twin.status()
        assert s['name'] == 'test'
        assert s['connected'] is False
        assert s['history_length'] == 0

    def test_export_json(self, tmp_path):
        twin = self._make_twin()
        twin.sync()
        twin.sync()
        path = str(tmp_path / 'twin.json')
        twin.export_json(path)
        import json
        with open(path) as f:
            data = json.load(f)
        assert data['name'] == 'test'
        assert len(data['history']) == 2
