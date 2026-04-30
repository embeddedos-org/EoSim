# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""Quantum computing simulator.

Pure Python, cross-platform (Linux/Windows/macOS). No OS-specific dependencies.
"""
import random


class QuantumSimulator:
    PRODUCT_TYPE = 'quantum'
    DISPLAY_NAME = 'Quantum Computing'
    SCENARIOS = {
        'qubit_init': {'description': 'Qubit initialization and readout calibration'},
        'gate_sequence': {'description': 'Single and two-qubit gate sequence'},
        'error_correction': {'description': 'Surface code error correction cycle'},
        'entanglement': {'description': 'Bell state preparation and measurement'},
        'measurement': {'description': 'Qubit state measurement and collapse'},
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
        self.vm.add_peripheral('temp_cryo', TemperatureSensor('temp_cryo', 0x40100010, 0, 1))
        self.vm.add_peripheral('wdt0', WatchdogTimer('wdt0', 0x40500200))
        self.state = {
            'qubit_count': 127, 'coherence_time_us': 100, 'gate_fidelity_pct': 99.5,
            'error_rate': 0.005, 'temperature_mk': 15, 'circuit_depth': 0,
            'measurements': 0, 'scenario': '',
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
        self.state['temperature_mk'] += random.gauss(0, 0.1)
        self.state['temperature_mk'] = max(10, min(30, self.state['temperature_mk']))
        self.state['coherence_time_us'] = max(10, 100 - (self.state['temperature_mk'] - 15) * 3 + random.gauss(0, 1))
        self.state['gate_fidelity_pct'] = max(90, 99.5 - self.state['circuit_depth'] * 0.01 + random.gauss(0, 0.05))
        self.state['error_rate'] = 1 - self.state['gate_fidelity_pct'] / 100

    def _apply_scenario(self):
        if not self.scenario:
            return
        if self.scenario == 'gate_sequence':
            self.state['circuit_depth'] += 1
        elif self.scenario == 'error_correction':
            self.state['error_rate'] = max(0.0001, self.state['error_rate'] * 0.9)
        elif self.scenario == 'measurement':
            self.state['measurements'] += 1
            self.state['circuit_depth'] = 0
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
