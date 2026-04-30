# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""Cybersecurity / HSM simulator.

Pure Python, cross-platform (Linux/Windows/macOS). No OS-specific dependencies.
"""
import random


class CybersecuritySimulator:
    PRODUCT_TYPE = 'cybersecurity'
    DISPLAY_NAME = 'Cybersecurity / HSM'
    SCENARIOS = {
        'intrusion_detection': {'description': 'IDS signature and anomaly detection'},
        'firewall_test': {'description': 'Firewall rule evaluation stress test'},
        'key_generation': {'description': 'RSA/ECC key pair generation'},
        'cert_validation': {'description': 'X.509 certificate chain validation'},
        'penetration_test': {'description': 'Simulated penetration test responses'},
    }

    def __init__(self, vm):
        self.vm = vm
        self.tick_count = 0
        self.state = {}
        self.scenario = ''
        self._scenario_step = 0

    def setup(self):
        from eosim.engine.native.peripherals.sensors import TemperatureSensor
        from eosim.engine.native.peripherals.composites import WatchdogTimer
        self.vm.add_peripheral('temp0', TemperatureSensor('temp0', 0x40100010))
        self.vm.add_peripheral('wdt0', WatchdogTimer('wdt0', 0x40500200))
        self.state = {
            'threats_detected': 0, 'packets_inspected': 0, 'rules_active': 500,
            'cpu_load_pct': 15, 'connections': 200, 'blocked_count': 0,
            'keys_generated': 0, 'certs_validated': 0, 'scenario': '',
        }

    def load_scenario(self, name):
        if name in self.SCENARIOS:
            self.scenario = name
            self._scenario_step = 0
            self.state['scenario'] = name

    def tick(self):
        self.tick_count += 1
        for name, dev in self.vm.peripherals.items():
            if hasattr(dev, 'simulate_tick'):
                dev.simulate_tick()
        self._apply_scenario()
        self.state['packets_inspected'] += random.randint(100, 500)
        self.state['cpu_load_pct'] += random.gauss(0, 1)
        self.state['cpu_load_pct'] = max(5, min(100, self.state['cpu_load_pct']))
        self.state['connections'] += random.randint(-5, 5)
        self.state['connections'] = max(0, self.state['connections'])

    def _apply_scenario(self):
        if not self.scenario:
            return
        if self.scenario == 'intrusion_detection':
            if random.random() < 0.1:
                self.state['threats_detected'] += 1
                self.state['blocked_count'] += 1
        elif self.scenario == 'firewall_test':
            self.state['cpu_load_pct'] = min(95, self.state['cpu_load_pct'] + 2)
            self.state['blocked_count'] += random.randint(5, 20)
        elif self.scenario == 'key_generation':
            if self._scenario_step % 10 == 0:
                self.state['keys_generated'] += 1
                self.state['cpu_load_pct'] = min(90, self.state['cpu_load_pct'] + 10)
        elif self.scenario == 'cert_validation':
            self.state['certs_validated'] += 1
        elif self.scenario == 'penetration_test':
            self.state['threats_detected'] += random.choice([0, 0, 1])
        self._scenario_step += 1

    def get_state(self) -> dict:
        return dict(self.state)

    def get_peripherals(self) -> dict:
        return dict(self.vm.peripherals)

    def get_status_text(self) -> str:
        scn = f" [{self.scenario}]" if self.scenario else ""
        return f"{self.DISPLAY_NAME} | Tick {self.tick_count}{scn}"

    def reset(self):
        self.tick_count = 0
        self.state = {}
        self.scenario = ''
        self._scenario_step = 0
