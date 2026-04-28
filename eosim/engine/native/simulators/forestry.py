# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""Forestry / fire detection simulator.

Pure Python, cross-platform (Linux/Windows/macOS). No OS-specific dependencies.
"""
import random


class ForestrySimulator:
    PRODUCT_TYPE = 'forestry'
    DISPLAY_NAME = 'Forestry / Fire Detection'
    SCENARIOS = {
        'fire_detection': {'description': 'Smoke and thermal fire detection'},
        'tree_inventory': {'description': 'LiDAR-based tree count and measurement'},
        'weather_monitor': {'description': 'Forest weather station data collection'},
        'wildlife_tracking': {'description': 'Camera trap and GPS collar tracking'},
        'chainsaw_operation': {'description': 'Chainsaw vibration and usage monitoring'},
    }

    def __init__(self, vm):
        self.vm = vm
        self.tick_count = 0
        self.state = {}
        self.scenario = ''
        self._scenario_step = 0

    def setup(self):
        from eosim.engine.native.peripherals.sensors import TemperatureSensor, GPSModule, LightSensor
        from eosim.engine.native.peripherals.composites import WatchdogTimer
        self.vm.add_peripheral('temp0', TemperatureSensor('temp0', 0x40100010))
        self.vm.add_peripheral('gps0', GPSModule('gps0', 0x40100300))
        self.vm.add_peripheral('light0', LightSensor('light0', 0x40100500))
        self.vm.add_peripheral('wdt0', WatchdogTimer('wdt0', 0x40500200))
        self.state = {
            'temperature_c': 20, 'humidity_pct': 65, 'smoke_level_ppm': 0,
            'wind_speed_mps': 5, 'fire_risk_level': 'low', 'area_covered_ha': 0,
            'trees_counted': 0, 'scenario': '',
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
        self.state['temperature_c'] += random.gauss(0, 0.2)
        self.state['humidity_pct'] += random.gauss(0, 0.3)
        self.state['humidity_pct'] = max(10, min(100, self.state['humidity_pct']))
        self.state['wind_speed_mps'] += random.gauss(0, 0.2)
        self.state['wind_speed_mps'] = max(0, min(30, self.state['wind_speed_mps']))
        if self.state['temperature_c'] > 35 and self.state['humidity_pct'] < 30:
            self.state['fire_risk_level'] = 'extreme'
        elif self.state['temperature_c'] > 30:
            self.state['fire_risk_level'] = 'high'
        else:
            self.state['fire_risk_level'] = 'low'

    def _apply_scenario(self):
        if not self.scenario:
            return
        if self.scenario == 'fire_detection':
            self.state['smoke_level_ppm'] = max(0, 50 + random.gauss(0, 10))
            self.state['temperature_c'] = 40 + random.gauss(0, 2)
        elif self.scenario == 'tree_inventory':
            self.state['trees_counted'] += random.randint(1, 5)
            self.state['area_covered_ha'] += 0.01
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
