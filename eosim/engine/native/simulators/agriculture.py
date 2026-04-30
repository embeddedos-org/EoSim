# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""Agriculture / precision farming simulator.

Pure Python, cross-platform (Linux/Windows/macOS). No OS-specific dependencies.
"""
import random


class AgricultureSimulator:
    PRODUCT_TYPE = 'agriculture'
    DISPLAY_NAME = 'Agriculture / Precision Farming'
    SCENARIOS = {
        'irrigation_cycle': {'duration_min': 30, 'description': 'Timed irrigation zone cycle'},
        'soil_monitoring': {'description': 'Continuous soil moisture and pH monitoring'},
        'greenhouse_control': {'target_temp_c': 25, 'description': 'Greenhouse climate management'},
        'crop_spraying': {'description': 'GPS-guided crop spraying operation'},
        'harvest_tracking': {'description': 'Yield monitoring during harvest'},
    }

    def __init__(self, vm):
        self.vm = vm
        self.tick_count = 0
        self.state = {}
        self.scenario = ''
        self._scenario_step = 0

    def setup(self):
        from eosim.engine.native.peripherals.sensors import TemperatureSensor, GPSModule
        from eosim.engine.native.peripherals.composites import WatchdogTimer
        self.vm.add_peripheral('temp0', TemperatureSensor('temp0', 0x40100010, -10, 60))
        self.vm.add_peripheral('gps0', GPSModule('gps0', 0x40100300))
        self.vm.add_peripheral('wdt0', WatchdogTimer('wdt0', 0x40500200))
        self.state = {
            'soil_moisture_pct': 45.0, 'temperature_c': 22.0, 'humidity_pct': 60.0,
            'irrigation_active': False, 'fertilizer_level': 80.0, 'crop_health': 85.0,
            'ph_level': 6.5, 'light_hours': 12, 'scenario': '',
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
        if self.state['irrigation_active']:
            self.state['soil_moisture_pct'] = min(100, self.state['soil_moisture_pct'] + 0.5)
        else:
            self.state['soil_moisture_pct'] = max(0, self.state['soil_moisture_pct'] - 0.05)
        self.state['temperature_c'] += random.gauss(0, 0.1)
        self.state['humidity_pct'] += random.gauss(0, 0.2)
        self.state['humidity_pct'] = max(10, min(100, self.state['humidity_pct']))
        self.state['ph_level'] += random.gauss(0, 0.01)
        self.state['ph_level'] = max(4, min(9, self.state['ph_level']))

    def _apply_scenario(self):
        if not self.scenario:
            return
        if self.scenario == 'irrigation_cycle':
            cycle_ticks = self.SCENARIOS['irrigation_cycle']['duration_min'] * 6
            self.state['irrigation_active'] = self._scenario_step < cycle_ticks
        elif self.scenario == 'greenhouse_control':
            target = self.SCENARIOS['greenhouse_control']['target_temp_c']
            if self.state['temperature_c'] < target - 1:
                self.state['temperature_c'] += 0.2
            elif self.state['temperature_c'] > target + 1:
                self.state['temperature_c'] -= 0.2
        elif self.scenario == 'crop_spraying':
            self.state['fertilizer_level'] = max(0, self.state['fertilizer_level'] - 0.2)
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
