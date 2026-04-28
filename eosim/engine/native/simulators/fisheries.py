# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""Fisheries / aquaculture simulator.

Pure Python, cross-platform (Linux/Windows/macOS). No OS-specific dependencies.
"""
import random


class FisheriesSimulator:
    PRODUCT_TYPE = 'fisheries'
    DISPLAY_NAME = 'Fisheries / Aquaculture'
    SCENARIOS = {
        'sonar_scan': {'description': 'Fish-finding sonar sweep'},
        'net_deployment': {'description': 'Trawl net deployment and retrieval'},
        'water_quality': {'description': 'Pond water quality monitoring'},
        'feeding_cycle': {'description': 'Automated fish feeding cycle'},
        'harvest': {'description': 'Fish harvest and counting'},
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
        self.vm.add_peripheral('temp_water', TemperatureSensor('temp_water', 0x40100010, 0, 35))
        self.vm.add_peripheral('gps0', GPSModule('gps0', 0x40100300))
        self.vm.add_peripheral('wdt0', WatchdogTimer('wdt0', 0x40500200))
        self.state = {
            'water_temp_c': 18, 'dissolved_oxygen_ppm': 7.0, 'ph_level': 7.2,
            'fish_count': 5000, 'feed_level_pct': 100, 'sonar_depth_m': 0,
            'net_deployed': False, 'scenario': '',
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
        self.state['water_temp_c'] += random.gauss(0, 0.05)
        self.state['dissolved_oxygen_ppm'] += random.gauss(0, 0.1)
        self.state['dissolved_oxygen_ppm'] = max(2, min(14, self.state['dissolved_oxygen_ppm']))
        self.state['ph_level'] += random.gauss(0, 0.01)
        self.state['ph_level'] = max(5, min(9, self.state['ph_level']))

    def _apply_scenario(self):
        if not self.scenario:
            return
        if self.scenario == 'sonar_scan':
            self.state['sonar_depth_m'] = random.uniform(5, 50)
        elif self.scenario == 'net_deployment':
            self.state['net_deployed'] = True
        elif self.scenario == 'feeding_cycle':
            self.state['feed_level_pct'] = max(0, self.state['feed_level_pct'] - 0.5)
        elif self.scenario == 'harvest':
            self.state['fish_count'] = max(0, self.state['fish_count'] - random.randint(10, 50))
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
