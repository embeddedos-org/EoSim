# SPDX-License-Identifier: MIT
"""Unit tests for analysis modules."""


class TestPowerAnalyzer:
    def test_measure(self):
        from eosim.analysis.power import PowerAnalyzer, PowerProfile
        pa = PowerAnalyzer()
        pa.add_profile('test', PowerProfile(name='test', voltage_v=3.3, current_active_ma=50))
        r = pa.measure('test', mode='active', duration_s=1.0)
        assert r['power_mw'] > 0
        assert r['current_ma'] == 50.0

    def test_battery_life(self):
        from eosim.analysis.power import PowerAnalyzer, PowerProfile
        pa = PowerAnalyzer()
        pa.add_profile('test', PowerProfile(
            name='test', current_active_ma=10, current_sleep_ma=0.01))
        hours = pa.estimate_battery_life('test', capacity_mah=1000, duty_cycle_pct=10)
        assert hours > 0


class TestThermalModel:
    def test_step(self):
        from eosim.analysis.thermal import ThermalModel
        tm = ThermalModel(ambient_c=25.0)
        t = tm.step(power_w=1.0)
        assert t > 25.0

    def test_steady_state(self):
        from eosim.analysis.thermal import ThermalModel
        tm = ThermalModel(ambient_c=25.0, thermal_resistance_cw=10.0)
        ss = tm.steady_state(power_w=2.0)
        assert ss == 45.0


class TestSafetyAnalyzer:
    def test_coverage(self):
        from eosim.analysis.safety import SafetyAnalyzer, SafetyRequirement
        sa = SafetyAnalyzer()
        sa.add_requirement(SafetyRequirement(req_id='R1', description='test'))
        sa.add_requirement(SafetyRequirement(req_id='R2', description='test2'))
        assert sa.coverage() == 0
        sa.verify('R1')
        assert sa.coverage() == 50.0

    def test_report(self):
        from eosim.analysis.safety import SafetyAnalyzer, SafetyRequirement
        sa = SafetyAnalyzer()
        sa.add_requirement(SafetyRequirement(req_id='R1'))
        r = sa.report()
        assert r['total'] == 1


class TestSecurityAnalyzer:
    def test_risk_score(self):
        from eosim.analysis.security import SecurityAnalyzer, ThreatModel
        sa = SecurityAnalyzer()
        sa.add_threat(ThreatModel(asset='ecu', threat='tampering', impact='high'))
        assert sa.risk_score() > 0
        sa.mitigate('ecu', 'secure boot')
        assert sa.risk_score() == 0

    def test_report(self):
        from eosim.analysis.security import SecurityAnalyzer, ThreatModel
        sa = SecurityAnalyzer()
        sa.add_threat(ThreatModel(asset='a'))
        r = sa.report()
        assert r['total_threats'] == 1


class TestWCETAnalyzer:
    def test_schedulable(self):
        from eosim.analysis.timing import WCETAnalyzer
        wa = WCETAnalyzer(clock_mhz=100)
        wa.add_task('task1', cycles=1000, period_us=100)
        wa.add_task('task2', cycles=2000, period_us=200)
        assert isinstance(wa.schedulable(), bool)

    def test_report(self):
        from eosim.analysis.timing import WCETAnalyzer
        wa = WCETAnalyzer()
        wa.add_task('t1', cycles=500)
        r = wa.report()
        assert 't1' in r['tasks']


class TestDigitalTwin:
    def test_sync(self):
        class FakeSim:
            tick_count = 0
            def get_state(self): return {'value': 42}
            def tick(self): self.tick_count += 1
        from eosim.digital_twin.twin import DigitalTwin
        dt = DigitalTwin('test', FakeSim())
        state = dt.sync()
        assert state['value'] == 42
        assert len(dt.history) == 1

    def test_predict(self):
        class FakeSim:
            tick_count = 0
            def get_state(self): return {'tick': self.tick_count}
            def tick(self): self.tick_count += 1
        from eosim.digital_twin.twin import DigitalTwin
        dt = DigitalTwin('test', FakeSim())
        states = dt.predict(steps=5)
        assert len(states) == 5


class TestNetworkTopology:
    def test_add_node_and_link(self):
        from eosim.network.topology import NetworkTopology, NetworkNode
        topo = NetworkTopology()
        topo.add_node(NetworkNode('n1', '10.0.0.1'))
        topo.add_node(NetworkNode('n2', '10.0.0.2'))
        topo.add_link('n1', 'n2')
        t = topo.get_topology()
        assert len(t['nodes']) == 2
        assert len(t['links']) == 1

    def test_send_packet(self):
        from eosim.network.topology import NetworkTopology, NetworkNode
        topo = NetworkTopology()
        topo.add_node(NetworkNode('a'))
        topo.add_node(NetworkNode('b'))
        topo.send_packet('a', 'b')
        assert topo.nodes['a'].packets_sent == 1
        assert topo.nodes['b'].packets_received == 1
