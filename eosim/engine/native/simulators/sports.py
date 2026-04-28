# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""Sports / performance tracking simulator.

Pure Python, cross-platform (Linux/Windows/macOS). No OS-specific dependencies.
"""
import random


class SportsSimulator:
    PRODUCT_TYPE = 'sports'
    DISPLAY_NAME = 'Sports / Performance'
    SCENARIOS = {
        'sprint_tracking': {'description': 'Sprint speed and acceleration tracking'},
        'endurance_test': {'duration_min': 60, 'description': 'Long-duration endurance monitoring'},
        'impact_detection': {'description': 'Impact/collision detection and logging'},
        'biometric_monitor': {'description': 'Heart rate and SpO2 continuous monitor'},
        'replay_analysis': {'description': 'Performance data replay and analysis'},
    }

    def __init__(self, vm):
        self.vm = vm
        self.tick_count = 0
        self.state = {}
        self.scenario = ''
        self._scenario_step = 0

    def setup(self):
        from eosim.engine.native.peripherals.sensors import IMUSensor, GPSModule, TemperatureSensor
        from eosim.engine.native.peripherals.composites import WatchdogTimer
        self.vm.add_peripheral('imu0', IMUSensor('imu0', 0x40100200))
        self.vm.add_peripheral('gps0', GPSModule('gps0', 0x40100300))
        self.vm.add_peripheral('temp0', TemperatureSensor('temp0', 0x40100010))
        self.vm.add_peripheral('wdt0', WatchdogTimer('wdt0', 0x40500200))
        self.state = {
            'speed_mps': 0, 'heart_rate_bpm': 70, 'distance_m': 0,
            'calories': 0, 'impact_g': 0, 'cadence_rpm': 0,
            'steps': 0, 'scenario': '',
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
        self.state['distance_m'] += self.state['speed_mps'] * 0.01
        self.state['calories'] += self.state['heart_rate_bpm'] * 0.0001
        self.state['heart_rate_bpm'] += random.gauss(0, 0.5)
        self.state['heart_rate_bpm'] = max(50, min(220, self.state['heart_rate_bpm']))
        if self.state['speed_mps'] > 0:
            self.state['steps'] += 1
            self.state['cadence_rpm'] = int(self.state['speed_mps'] * 30)

    def _apply_scenario(self):
        if not self.scenario:
            return
        if self.scenario == 'sprint_tracking':
            self.state['speed_mps'] = 9 + random.gauss(0, 0.5)
            self.state['heart_rate_bpm'] = min(200, self.state['heart_rate_bpm'] + 1)
        elif self.scenario == 'endurance_test':
            self.state['speed_mps'] = 3 + random.gauss(0, 0.3)
            self.state['heart_rate_bpm'] = 140 + random.gauss(0, 3)
        elif self.scenario == 'impact_detection':
            if random.random() < 0.05:
                self.state['impact_g'] = random.uniform(5, 50)
            else:
                self.state['impact_g'] = 0
        elif self.scenario == 'biometric_monitor':
            self.state['speed_mps'] = 0
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
