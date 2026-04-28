# SPDX-License-Identifier: MIT
"""Unit tests for all new domain simulators."""
import pytest


class FakeVM:
    """Minimal VM mock for simulator testing."""
    def __init__(self):
        self.peripherals = {}
    def add_peripheral(self, name, dev):
        self.peripherals[name] = dev


SIMULATOR_CLASSES = [
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
]


def _get_class(module_path, class_name):
    import importlib
    mod = importlib.import_module(module_path)
    return getattr(mod, class_name)


@pytest.mark.parametrize("module_path,class_name", SIMULATOR_CLASSES)
class TestNewSimulators:

    def test_instantiate_and_setup(self, module_path, class_name):
        cls = _get_class(module_path, class_name)
        vm = FakeVM()
        sim = cls(vm)
        sim.setup()
        assert sim.tick_count == 0
        assert isinstance(sim.state, dict)
        assert len(sim.state) > 0

    def test_tick(self, module_path, class_name):
        cls = _get_class(module_path, class_name)
        vm = FakeVM()
        sim = cls(vm)
        sim.setup()
        sim.tick()
        sim.tick()
        assert sim.tick_count == 2

    def test_get_state(self, module_path, class_name):
        cls = _get_class(module_path, class_name)
        vm = FakeVM()
        sim = cls(vm)
        sim.setup()
        sim.tick()
        state = sim.get_state()
        assert isinstance(state, dict)
        assert len(state) > 0

    def test_get_status_text(self, module_path, class_name):
        cls = _get_class(module_path, class_name)
        vm = FakeVM()
        sim = cls(vm)
        sim.setup()
        text = sim.get_status_text()
        assert isinstance(text, str)
        assert "Tick" in text

    def test_reset(self, module_path, class_name):
        cls = _get_class(module_path, class_name)
        vm = FakeVM()
        sim = cls(vm)
        sim.setup()
        sim.tick()
        sim.tick()
        sim.reset()
        assert sim.tick_count == 0

    def test_scenarios_defined(self, module_path, class_name):
        cls = _get_class(module_path, class_name)
        assert hasattr(cls, 'SCENARIOS')
        assert isinstance(cls.SCENARIOS, dict)
        assert len(cls.SCENARIOS) >= 3

    def test_load_scenario(self, module_path, class_name):
        cls = _get_class(module_path, class_name)
        vm = FakeVM()
        sim = cls(vm)
        sim.setup()
        first_scenario = list(cls.SCENARIOS.keys())[0]
        sim.load_scenario(first_scenario)
        assert sim.scenario == first_scenario
        for _ in range(10):
            sim.tick()
        assert sim.tick_count == 10

    def test_product_type(self, module_path, class_name):
        cls = _get_class(module_path, class_name)
        assert hasattr(cls, 'PRODUCT_TYPE')
        assert isinstance(cls.PRODUCT_TYPE, str)
        assert len(cls.PRODUCT_TYPE) > 0

    def test_display_name(self, module_path, class_name):
        cls = _get_class(module_path, class_name)
        assert hasattr(cls, 'DISPLAY_NAME')
        assert isinstance(cls.DISPLAY_NAME, str)
        assert len(cls.DISPLAY_NAME) > 0


class TestSimulatorFactory:
    def test_factory_creates_new_simulators(self):
        from eosim.engine.native.simulators import SimulatorFactory, SIMULATOR_MAP
        vm = FakeVM()
        # Test a sample of new simulator types
        for ptype in ['telecom', 'railway', 'agriculture', 'nuclear', 'quantum',
                       'logistics', 'ar_vr', 'cybersecurity', 'v2x', 'hvac']:
            assert ptype in SIMULATOR_MAP, f"{ptype} not in SIMULATOR_MAP"
            sim = SimulatorFactory.create(ptype, vm)
            assert sim is not None
            assert sim.tick_count == 0

    def test_list_simulators_expanded(self):
        from eosim.engine.native.simulators import SimulatorFactory
        sims = SimulatorFactory.list_simulators()
        assert len(sims) >= 30  # should have 49 unique types
