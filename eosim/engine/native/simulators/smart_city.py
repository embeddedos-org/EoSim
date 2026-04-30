# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""Smart city infrastructure simulator.

Pure Python, cross-platform (Linux/Windows/macOS). No OS-specific dependencies.
"""
import random


class SmartCitySimulator:
    PRODUCT_TYPE = 'smart_city'
    DISPLAY_NAME = 'Smart City'
    SCENARIOS = {
        'traffic_light_cycle': {'description': 'Adaptive traffic light cycle management'},
        'parking_management': {'description': 'Smart parking occupancy tracking'},
        'street_lighting': {'description': 'Adaptive street lighting based on ambient light'},
        'air_quality_monitor': {'description': 'Air quality index monitoring and alerts'},
    }

    def __init__(self, vm):
        self.vm = vm
        self.tick_count = 0
        self.state = {}
        self.scenario = ''
        self._scenario_step = 0

    def setup(self):
        from eosim.engine.native.peripherals.sensors import (
            TemperatureSensor, LightSensor, GPSModule,
        )
        from eosim.engine.native.peripherals.composites import WatchdogTimer
        self.vm.add_peripheral('temp0', TemperatureSensor('temp0', 0x40100010))
        self.vm.add_peripheral('light0', LightSensor('light0', 0x40100500))
        self.vm.add_peripheral('gps0', GPSModule('gps0', 0x40100300))
        self.vm.add_peripheral('wdt0', WatchdogTimer('wdt0', 0x40500200))
        self.state = {
            'traffic_flow': 50, 'parking_occupied': 0, 'parking_total': 200,
            'light_level_pct': 100, 'air_quality_index': 50, 'noise_db': 55.0,
            'pedestrian_count': 0, 'scenario': '',
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
        self.state['noise_db'] += random.gauss(0, 1)
        self.state['noise_db'] = max(30, min(90, self.state['noise_db']))
        self.state['air_quality_index'] += random.gauss(0, 0.5)
        self.state['air_quality_index'] = max(0, min(500, self.state['air_quality_index']))

    def _apply_scenario(self):
        if not self.scenario:
            return
        if self.scenario == 'traffic_light_cycle':
            phase = self._scenario_step % 60
            self.state['traffic_flow'] = 80 if phase < 30 else 20
        elif self.scenario == 'parking_management':
            self.state['parking_occupied'] = min(
                self.state['parking_total'],
                max(0, self.state['parking_occupied'] + random.randint(-2, 3)))
        elif self.scenario == 'street_lighting':
            light = self.vm.peripherals.get('light0')
            if light:
                lux = light.lux
                self.state['light_level_pct'] = max(20, min(100, 100 - int(lux / 10)))
        elif self.scenario == 'air_quality_monitor':
            self.state['air_quality_index'] += random.gauss(1, 2)
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
