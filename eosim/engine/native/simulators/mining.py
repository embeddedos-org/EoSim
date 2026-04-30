# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""Mining / extraction simulator.

Pure Python, cross-platform (Linux/Windows/macOS). No OS-specific dependencies.
"""
import random


class MiningSimulator:
    PRODUCT_TYPE = 'mining'
    DISPLAY_NAME = 'Mining / Extraction'
    SCENARIOS = {
        'drilling_operation': {'description': 'Rotary drill bit operation at depth'},
        'ventilation_control': {'description': 'Mine ventilation fan speed control'},
        'gas_detection': {'description': 'Methane/CO gas detection and alarm'},
        'conveyor_run': {'speed_mps': 2.5, 'description': 'Ore conveyor belt operation'},
        'blast_sequence': {'description': 'Controlled blasting sequence'},
    }

    def __init__(self, vm):
        self.vm = vm
        self.tick_count = 0
        self.state = {}
        self.scenario = ''
        self._scenario_step = 0

    def setup(self):
        from eosim.engine.native.peripherals.sensors import TemperatureSensor
        from eosim.engine.native.peripherals.actuators import MotorController
        from eosim.engine.native.peripherals.composites import WatchdogTimer
        self.vm.add_peripheral('temp0', TemperatureSensor('temp0', 0x40100010, 10, 60))
        self.vm.add_peripheral('motor0', MotorController('motor0', 0x40200000))
        self.vm.add_peripheral('wdt0', WatchdogTimer('wdt0', 0x40500200))
        self.state = {
            'drill_depth_m': 0, 'drill_rpm': 0, 'gas_level_ppm': 5.0,
            'ventilation_cfm': 5000, 'conveyor_speed_mps': 0, 'temperature_c': 25.0,
            'ore_tons': 0, 'alarm_active': False, 'scenario': '',
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
        self.state['gas_level_ppm'] += random.gauss(0, 0.5)
        self.state['gas_level_ppm'] = max(0, min(100, self.state['gas_level_ppm']))
        self.state['alarm_active'] = self.state['gas_level_ppm'] > 25
        self.state['temperature_c'] += random.gauss(0, 0.1)
        if self.state['conveyor_speed_mps'] > 0:
            self.state['ore_tons'] += self.state['conveyor_speed_mps'] * 0.01

    def _apply_scenario(self):
        if not self.scenario:
            return
        if self.scenario == 'drilling_operation':
            self.state['drill_rpm'] = 120
            self.state['drill_depth_m'] += 0.01
        elif self.scenario == 'ventilation_control':
            self.state['ventilation_cfm'] = 8000 + random.gauss(0, 200)
        elif self.scenario == 'gas_detection':
            self.state['gas_level_ppm'] = 30 + random.gauss(0, 5)
        elif self.scenario == 'conveyor_run':
            self.state['conveyor_speed_mps'] = 2.5
        elif self.scenario == 'blast_sequence':
            if self._scenario_step == 10:
                self.state['gas_level_ppm'] += 20
            self.state['drill_rpm'] = 0
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
