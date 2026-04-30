# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""Smart grid / power distribution simulator.

Pure Python, cross-platform (Linux/Windows/macOS). No OS-specific dependencies.
"""
import random


class SmartGridSimulator:
    PRODUCT_TYPE = 'smart_grid'
    DISPLAY_NAME = 'Smart Grid / Power Distribution'
    SCENARIOS = {
        'peak_demand': {'description': 'Peak load demand response'},
        'fault_isolation': {'description': 'Fault detection and isolation on feeder'},
        'load_balancing': {'description': 'Multi-feeder load redistribution'},
        'renewable_integration': {'description': 'Solar/wind variability compensation'},
        'blackout_recovery': {'description': 'Black start and grid restoration'},
    }

    def __init__(self, vm):
        self.vm = vm
        self.tick_count = 0
        self.state = {}
        self.scenario = ''
        self._scenario_step = 0

    def setup(self):
        from eosim.engine.native.peripherals.sensors import TemperatureSensor, ADCChannel
        from eosim.engine.native.peripherals.composites import WatchdogTimer
        self.vm.add_peripheral('temp0', TemperatureSensor('temp0', 0x40100010))
        self.vm.add_peripheral('adc0', ADCChannel('adc0', 0x40100600))
        self.vm.add_peripheral('wdt0', WatchdogTimer('wdt0', 0x40500200))
        self.state = {
            'grid_frequency_hz': 60.0, 'voltage_kv': 138.0, 'load_mw': 500,
            'generation_mw': 520, 'power_factor': 0.95, 'line_losses_pct': 3.5,
            'renewable_pct': 25, 'breakers_open': 0, 'scenario': '',
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
        balance = self.state['generation_mw'] - self.state['load_mw']
        self.state['grid_frequency_hz'] = 60.0 + balance * 0.001 + random.gauss(0, 0.005)
        self.state['voltage_kv'] += random.gauss(0, 0.1)
        self.state['voltage_kv'] = max(130, min(145, self.state['voltage_kv']))
        self.state['line_losses_pct'] = 3.5 + self.state['load_mw'] * 0.002 + random.gauss(0, 0.1)

    def _apply_scenario(self):
        if not self.scenario:
            return
        if self.scenario == 'peak_demand':
            self.state['load_mw'] = 800 + random.gauss(0, 20)
            self.state['generation_mw'] = 810 + random.gauss(0, 10)
        elif self.scenario == 'fault_isolation':
            if self._scenario_step == 5:
                self.state['breakers_open'] = 2
                self.state['load_mw'] -= 100
            if self._scenario_step == 20:
                self.state['breakers_open'] = 1
        elif self.scenario == 'renewable_integration':
            self.state['renewable_pct'] = 40 + random.gauss(0, 10)
            self.state['generation_mw'] = self.state['load_mw'] + random.gauss(0, 30)
        elif self.scenario == 'blackout_recovery':
            if self._scenario_step < 20:
                self.state['generation_mw'] = self._scenario_step * 30
                self.state['load_mw'] = self._scenario_step * 25
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
