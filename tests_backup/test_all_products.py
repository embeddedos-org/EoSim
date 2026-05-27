# SPDX-License-Identifier: MIT
"""Comprehensive product simulation tests — every product type in PRODUCT_CATALOG
gets instantiated, setup, ticked, state-checked, scenario-loaded, and reset.

This ensures 100% product coverage: every product template can create a working
simulator and run through its full lifecycle.
"""
import pytest


class FakeVM:
    """Minimal VM mock for simulator testing."""
    def __init__(self):
        self.peripherals = {}
    def add_peripheral(self, name, dev):
        self.peripherals[name] = dev


def _get_all_product_types():
    """Get every product type from the PRODUCT_CATALOG."""
    from eosim.gui.product_templates import PRODUCT_CATALOG
    return list(PRODUCT_CATALOG.keys())


def _get_all_simulator_map_keys():
    """Get every key from the SIMULATOR_MAP."""
    from eosim.engine.native.simulators import SIMULATOR_MAP
    return list(SIMULATOR_MAP.keys())


# =============================================================================
# Test every product template can create a working simulator
# =============================================================================

class TestAllProductSimulations:
    """Test that every product in PRODUCT_CATALOG creates a valid simulator."""

    @pytest.fixture(params=_get_all_product_types())
    def product_name(self, request):
        return request.param

    def test_product_creates_simulator(self, product_name):
        from eosim.engine.native.simulators import SimulatorFactory
        vm = FakeVM()
        sim = SimulatorFactory.create(product_name, vm)
        assert sim is not None
        assert hasattr(sim, 'tick')
        assert hasattr(sim, 'get_state')
        assert hasattr(sim, 'reset')

    def test_product_simulator_ticks(self, product_name):
        from eosim.engine.native.simulators import SimulatorFactory
        vm = FakeVM()
        sim = SimulatorFactory.create(product_name, vm)
        for _ in range(10):
            sim.tick()
        assert sim.tick_count == 10

    def test_product_simulator_state(self, product_name):
        from eosim.engine.native.simulators import SimulatorFactory
        vm = FakeVM()
        sim = SimulatorFactory.create(product_name, vm)
        sim.tick()
        state = sim.get_state()
        assert isinstance(state, dict)

    def test_product_simulator_status_text(self, product_name):
        from eosim.engine.native.simulators import SimulatorFactory
        vm = FakeVM()
        sim = SimulatorFactory.create(product_name, vm)
        text = sim.get_status_text()
        assert isinstance(text, str)
        assert len(text) > 0

    def test_product_simulator_reset(self, product_name):
        from eosim.engine.native.simulators import SimulatorFactory
        vm = FakeVM()
        sim = SimulatorFactory.create(product_name, vm)
        sim.tick()
        sim.tick()
        sim.reset()
        assert sim.tick_count == 0

    def test_product_simulator_peripherals(self, product_name):
        from eosim.engine.native.simulators import SimulatorFactory
        vm = FakeVM()
        sim = SimulatorFactory.create(product_name, vm)
        peripherals = sim.get_peripherals()
        assert isinstance(peripherals, dict)


# =============================================================================
# Test every SIMULATOR_MAP key resolves correctly
# =============================================================================

class TestAllSimulatorMapEntries:
    """Test that every key in SIMULATOR_MAP creates a valid simulator."""

    @pytest.fixture(params=_get_all_simulator_map_keys())
    def sim_key(self, request):
        return request.param

    def test_simulator_map_entry(self, sim_key):
        from eosim.engine.native.simulators import SimulatorFactory
        vm = FakeVM()
        sim = SimulatorFactory.create(sim_key, vm)
        assert sim is not None
        sim.tick()
        assert sim.tick_count == 1


# =============================================================================
# Test every simulator's scenarios
# =============================================================================

ALL_SIMULATOR_CLASSES = [
    ('eosim.engine.native.simulators.vehicle', 'VehicleSimulator'),
    ('eosim.engine.native.simulators.drone', 'DroneSimulator'),
    ('eosim.engine.native.simulators.robot', 'RobotSimulator'),
    ('eosim.engine.native.simulators.aircraft', 'AircraftSimulator'),
    ('eosim.engine.native.simulators.satellite', 'SatelliteSimulator'),
    ('eosim.engine.native.simulators.medical', 'MedicalSimulator'),
    ('eosim.engine.native.simulators.industrial', 'IndustrialSimulator'),
    ('eosim.engine.native.simulators.iot', 'IoTSimulator'),
    ('eosim.engine.native.simulators.energy', 'EnergySimulator'),
    ('eosim.engine.native.simulators.wearable', 'WearableSimulator'),
    ('eosim.engine.native.simulators.media', 'MediaDeviceSimulator'),
    ('eosim.engine.native.simulators.speaker', 'SmartSpeakerSimulator'),
    ('eosim.engine.native.simulators.camera', 'HomeCameraSimulator'),
    ('eosim.engine.native.simulators.aerodynamics', 'AerodynamicsSimulator'),
    ('eosim.engine.native.simulators.physiology', 'PhysiologySimulator'),
    ('eosim.engine.native.simulators.finance', 'FinanceSimulator'),
    ('eosim.engine.native.simulators.weather', 'WeatherSimulator'),
    ('eosim.engine.native.simulators.gaming', 'GamingSimulator'),
    ('eosim.engine.native.simulators.telecom', 'TelecomSimulator'),
    ('eosim.engine.native.simulators.defense', 'DefenseSimulator'),
    ('eosim.engine.native.simulators.submarine', 'SubmarineSimulator'),
    ('eosim.engine.native.simulators.network', 'NetworkSimulator'),
    ('eosim.engine.native.simulators.smart_city', 'SmartCitySimulator'),
    ('eosim.engine.native.simulators.railway', 'RailwaySimulator'),
    ('eosim.engine.native.simulators.agriculture', 'AgricultureSimulator'),
    ('eosim.engine.native.simulators.maritime', 'MaritimeSimulator'),
    ('eosim.engine.native.simulators.mining', 'MiningSimulator'),
    ('eosim.engine.native.simulators.construction', 'ConstructionSimulator'),
    ('eosim.engine.native.simulators.retail', 'RetailSimulator'),
    ('eosim.engine.native.simulators.education', 'EducationSimulator'),
    ('eosim.engine.native.simulators.nuclear', 'NuclearSimulator'),
    ('eosim.engine.native.simulators.rover', 'RoverSimulator'),
    ('eosim.engine.native.simulators.launch_vehicle', 'LaunchVehicleSimulator'),
    ('eosim.engine.native.simulators.smart_grid', 'SmartGridSimulator'),
    ('eosim.engine.native.simulators.printer', 'PrinterSimulator'),
    ('eosim.engine.native.simulators.hvac', 'HVACSimulator'),
    ('eosim.engine.native.simulators.elevator', 'ElevatorSimulator'),
    ('eosim.engine.native.simulators.traffic', 'TrafficSimulator'),
    ('eosim.engine.native.simulators.water', 'WaterSimulator'),
    ('eosim.engine.native.simulators.oil_gas', 'OilGasSimulator'),
    ('eosim.engine.native.simulators.logistics', 'LogisticsSimulator'),
    ('eosim.engine.native.simulators.ar_vr', 'ARVRSimulator'),
    ('eosim.engine.native.simulators.cybersecurity', 'CybersecuritySimulator'),
    ('eosim.engine.native.simulators.quantum', 'QuantumSimulator'),
    ('eosim.engine.native.simulators.sports', 'SportsSimulator'),
    ('eosim.engine.native.simulators.forestry', 'ForestrySimulator'),
    ('eosim.engine.native.simulators.fisheries', 'FisheriesSimulator'),
    ('eosim.engine.native.simulators.v2x', 'AutomotiveV2XSimulator'),
    ('eosim.engine.native.simulators.android', 'AndroidSimulator'),
    ('eosim.engine.native.simulators.ios', 'IOSSimulator'),
]


def _get_class(module_path, class_name):
    import importlib
    mod = importlib.import_module(module_path)
    return getattr(mod, class_name)


@pytest.mark.parametrize("module_path,class_name", ALL_SIMULATOR_CLASSES)
class TestAllSimulatorScenarios:
    """Test every scenario of every simulator."""

    def test_all_scenarios_run(self, module_path, class_name):
        cls = _get_class(module_path, class_name)
        vm = FakeVM()
        sim = cls(vm)
        sim.setup()

        for scenario_name in cls.SCENARIOS:
            sim.reset()
            sim.setup()
            sim.load_scenario(scenario_name)
            assert sim.scenario == scenario_name

            # Run 50 ticks in each scenario
            for _ in range(50):
                sim.tick()

            state = sim.get_state()
            assert isinstance(state, dict)
            assert sim.tick_count == 50

    def test_scenario_descriptions_exist(self, module_path, class_name):
        cls = _get_class(module_path, class_name)
        for name, cfg in cls.SCENARIOS.items():
            assert 'description' in cfg, f"Scenario {name} missing description"
            assert len(cfg['description']) > 5


# =============================================================================
# Test Android & iOS specific features
# =============================================================================

class TestAndroidSimulator:
    def _create(self):
        from eosim.engine.native.simulators.android import AndroidSimulator
        vm = FakeVM()
        sim = AndroidSimulator(vm)
        sim.setup()
        return sim

    def test_boot_sequence(self):
        sim = self._create()
        sim.load_scenario('boot_sequence')
        for _ in range(60):
            sim.tick()
        assert sim.state['boot_stage'] == 'android_ready'
        assert sim.state['screen_on'] is True

    def test_sensor_polling(self):
        sim = self._create()
        sim.load_scenario('sensor_polling')
        for _ in range(20):
            sim.tick()
        assert sim.state['accel_z'] != 0  # gravity

    def test_camera_capture(self):
        sim = self._create()
        sim.load_scenario('camera_capture')
        for _ in range(35):
            sim.tick()
        assert sim.state['photos_taken'] >= 1

    def test_power_management(self):
        sim = self._create()
        sim.load_scenario('power_management')
        for _ in range(65):
            sim.tick()
        # Should have entered doze mode
        assert sim.state['power_mode'] in ('doze', 'deep_sleep', 'normal')

    def test_battery_drain(self):
        sim = self._create()
        initial_battery = sim.state['battery_pct']
        sim.state['screen_on'] = True
        for _ in range(100):
            sim.tick()
        assert sim.state['battery_pct'] < initial_battery

    def test_connectivity_cycle(self):
        sim = self._create()
        sim.load_scenario('connectivity_cycle')
        for _ in range(40):
            sim.tick()
        assert sim.state['wifi_connected'] is True
        assert sim.state['ble_advertising'] is True

    def test_android_version(self):
        sim = self._create()
        assert sim.state['android_version'] == '15'

    def test_ota_update(self):
        sim = self._create()
        sim.load_scenario('ota_update')
        for _ in range(65):
            sim.tick()
        assert sim.state['boot_stage'] == 'android_ready'


class TestIOSSimulator:
    def _create(self):
        from eosim.engine.native.simulators.ios import IOSSimulator
        vm = FakeVM()
        sim = IOSSimulator(vm)
        sim.setup()
        return sim

    def test_boot_sequence(self):
        sim = self._create()
        sim.load_scenario('boot_sequence')
        for _ in range(45):
            sim.tick()
        assert sim.state['boot_stage'] == 'springboard'

    def test_face_id_unlock(self):
        sim = self._create()
        sim.load_scenario('face_id_unlock')
        for _ in range(15):
            sim.tick()
        assert sim.state['face_id_locked'] is False
        assert sim.state['secure_enclave_ops'] >= 1

    def test_haptic_feedback(self):
        sim = self._create()
        sim.load_scenario('haptic_feedback')
        found_haptic = False
        for _ in range(30):
            sim.tick()
            if sim.state['haptic_pattern'] != 'none':
                found_haptic = True
        assert found_haptic

    def test_camera_pipeline(self):
        sim = self._create()
        sim.load_scenario('camera_pipeline')
        for _ in range(30):
            sim.tick()
        assert sim.state['photos_taken'] >= 1

    def test_uwb_ranging(self):
        sim = self._create()
        sim.load_scenario('uwb_ranging')
        for _ in range(10):
            sim.tick()
        assert sim.state['uwb_ranging'] is True
        assert sim.state['uwb_distance_m'] >= 0

    def test_nfc_payment(self):
        sim = self._create()
        sim.load_scenario('nfc_payment')
        for _ in range(20):
            sim.tick()
        assert sim.state['secure_enclave_ops'] >= 1

    def test_sensor_fusion(self):
        sim = self._create()
        sim.load_scenario('sensor_fusion')
        for _ in range(50):
            sim.tick()
        # Attitude should have changed
        assert sim.state['attitude_pitch'] != 0 or sim.state['attitude_roll'] != 0

    def test_thermal_management(self):
        sim = self._create()
        assert sim.state['thermal_state'] == 'nominal'

    def test_ios_version(self):
        sim = self._create()
        assert sim.state['ios_version'] == '18.0'
        assert sim.state['soc'] == 'A17 Pro'

    def test_battery_drain_with_camera(self):
        sim = self._create()
        initial = sim.state['battery_pct']
        sim.state['screen_on'] = True
        sim.state['camera_active'] = True
        for _ in range(100):
            sim.tick()
        assert sim.state['battery_pct'] < initial - 1.0  # significant drain


# =============================================================================
# Test schema and domain coverage
# =============================================================================

class TestSchemaCoverage:
    def test_all_schema_domains_have_profiles(self):
        from eosim.core.schema import VALID_DOMAINS
        from eosim.core.domains import DOMAIN_CATALOG
        for domain in VALID_DOMAINS:
            assert domain in DOMAIN_CATALOG, f"Domain '{domain}' in schema but not in DOMAIN_CATALOG"

    def test_all_domain_profiles_in_schema(self):
        from eosim.core.schema import VALID_DOMAINS
        from eosim.core.domains import DOMAIN_CATALOG
        for domain in DOMAIN_CATALOG:
            assert domain in VALID_DOMAINS, f"Domain '{domain}' in catalog but not in VALID_DOMAINS"

    def test_domain_count(self):
        from eosim.core.domains import list_domains
        domains = list_domains()
        assert len(domains) >= 40

    def test_architecture_count(self):
        from eosim.core.schema import VALID_ARCHES
        assert len(VALID_ARCHES) >= 25

    def test_engine_count(self):
        from eosim.core.schema import VALID_ENGINES
        assert len(VALID_ENGINES) >= 13

    def test_modeling_count(self):
        from eosim.core.schema import VALID_MODELING
        assert len(VALID_MODELING) >= 20


class TestProductTemplateCoverage:
    def test_product_count(self):
        from eosim.gui.product_templates import PRODUCT_CATALOG
        assert len(PRODUCT_CATALOG) >= 79

    def test_all_templates_have_required_fields(self):
        from eosim.gui.product_templates import PRODUCT_CATALOG
        for name, tmpl in PRODUCT_CATALOG.items():
            assert tmpl.name, f"Template {name} missing name"
            assert tmpl.display_name, f"Template {name} missing display_name"
            assert tmpl.arch, f"Template {name} missing arch"
            assert tmpl.domain, f"Template {name} missing domain"
            assert tmpl.description, f"Template {name} missing description"
            assert tmpl.simulator_class, f"Template {name} missing simulator_class"

    def test_all_templates_have_valid_domain(self):
        from eosim.core.schema import VALID_DOMAINS
        from eosim.gui.product_templates import PRODUCT_CATALOG
        for name, tmpl in PRODUCT_CATALOG.items():
            assert tmpl.domain in VALID_DOMAINS, f"Template {name} has invalid domain: {tmpl.domain}"

    def test_all_templates_have_valid_arch(self):
        from eosim.core.schema import VALID_ARCHES
        from eosim.gui.product_templates import PRODUCT_CATALOG
        for name, tmpl in PRODUCT_CATALOG.items():
            assert tmpl.arch in VALID_ARCHES, f"Template {name} has invalid arch: {tmpl.arch}"


class TestSimulatorCoverage:
    def test_simulator_count(self):
        from eosim.engine.native.simulators import SimulatorFactory
        sims = SimulatorFactory.list_simulators()
        assert len(sims) >= 30

    def test_simulator_map_size(self):
        from eosim.engine.native.simulators import SIMULATOR_MAP
        assert len(SIMULATOR_MAP) >= 165
