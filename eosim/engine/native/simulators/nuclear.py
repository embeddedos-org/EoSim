# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""Nuclear reactor control simulator.

Pure Python, cross-platform (Linux/Windows/macOS). No OS-specific dependencies.
"""
import random


class NuclearSimulator:
    PRODUCT_TYPE = 'nuclear'
    DISPLAY_NAME = 'Nuclear / Reactor Control'
    SCENARIOS = {
        'startup_sequence': {'description': 'Controlled reactor startup to criticality'},
        'steady_state': {'power_pct': 100, 'description': 'Full power steady-state operation'},
        'scram': {'description': 'Emergency reactor shutdown (SCRAM)'},
        'refueling': {'description': 'Reactor shutdown for fuel rod replacement'},
        'coolant_loss': {'description': 'Loss of coolant accident (LOCA) response'},
    }

    def __init__(self, vm):
        self.vm = vm
        self.tick_count = 0
        self.state = {}
        self.scenario = ''
        self._scenario_step = 0

    def setup(self):
        from eosim.engine.native.peripherals.sensors import TemperatureSensor, PressureSensor
        from eosim.engine.native.peripherals.composites import WatchdogTimer
        self.vm.add_peripheral('temp_coolant', TemperatureSensor('temp_coolant', 0x40100010, 20, 350))
        self.vm.add_peripheral('pressure0', PressureSensor('pressure0', 0x40100100, 20000))
        self.vm.add_peripheral('wdt0', WatchdogTimer('wdt0', 0x40500200))
        self.state = {
            'reactor_power_pct': 0, 'coolant_temp_c': 30, 'pressure_mpa': 15.5,
            'control_rod_pct': 100, 'radiation_usv': 0.1, 'neutron_flux': 0,
            'scram_active': False, 'scenario': '',
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
        rod = self.state['control_rod_pct']
        self.state['reactor_power_pct'] = max(0, min(110, 100 - rod + random.gauss(0, 0.5)))
        self.state['neutron_flux'] = self.state['reactor_power_pct'] * 1e13
        self.state['coolant_temp_c'] = 30 + self.state['reactor_power_pct'] * 2.8 + random.gauss(0, 0.5)
        self.state['radiation_usv'] = 0.1 + self.state['reactor_power_pct'] * 0.001
        tc = self.vm.peripherals.get('temp_coolant')
        if tc:
            tc.temperature = self.state['coolant_temp_c']

    def _apply_scenario(self):
        if not self.scenario:
            return
        if self.scenario == 'startup_sequence':
            self.state['control_rod_pct'] = max(0, self.state['control_rod_pct'] - 0.5)
        elif self.scenario == 'scram':
            self.state['control_rod_pct'] = 100
            self.state['scram_active'] = True
        elif self.scenario == 'coolant_loss':
            self.state['pressure_mpa'] = max(0, self.state['pressure_mpa'] - 0.5)
            if self.state['pressure_mpa'] < 10:
                self.state['control_rod_pct'] = 100
                self.state['scram_active'] = True
        elif self.scenario == 'refueling':
            self.state['control_rod_pct'] = 100
            self.state['reactor_power_pct'] = 0
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
