# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""V2X communication simulator.

Pure Python, cross-platform (Linux/Windows/macOS). No OS-specific dependencies.
"""
import random


class AutomotiveV2XSimulator:
    PRODUCT_TYPE = 'v2x'
    DISPLAY_NAME = 'V2X Communication'
    SCENARIOS = {
        'bsm_broadcast': {'description': 'Basic Safety Message (BSM) periodic broadcast'},
        'intersection_alert': {'description': 'Intersection movement assist (IMA)'},
        'emergency_vehicle': {'description': 'Emergency vehicle approach warning'},
        'platooning': {'description': 'Cooperative adaptive cruise control platoon'},
        'road_hazard': {'description': 'Road hazard warning dissemination'},
    }

    def __init__(self, vm):
        self.vm = vm
        self.tick_count = 0
        self.state = {}
        self.scenario = ''
        self._scenario_step = 0

    def setup(self):
        from eosim.engine.native.peripherals.sensors import GPSModule, TemperatureSensor
        from eosim.engine.native.peripherals.composites import WatchdogTimer
        self.vm.add_peripheral('gps0', GPSModule('gps0', 0x40100300))
        self.vm.add_peripheral('temp0', TemperatureSensor('temp0', 0x40100010))
        self.vm.add_peripheral('wdt0', WatchdogTimer('wdt0', 0x40500200))
        self.state = {
            'vehicle_count': 10, 'message_rate_hz': 10, 'latency_ms': 5,
            'range_m': 300, 'channel_busy_pct': 20, 'collision_warnings': 0,
            'bsm_sent': 0, 'bsm_received': 0, 'scenario': '',
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
        self.state['bsm_sent'] += self.state['message_rate_hz']
        self.state['bsm_received'] += int(self.state['message_rate_hz'] * (1 - self.state['channel_busy_pct'] / 200))
        self.state['latency_ms'] += random.gauss(0, 0.5)
        self.state['latency_ms'] = max(1, min(50, self.state['latency_ms']))
        self.state['channel_busy_pct'] += random.gauss(0, 1)
        self.state['channel_busy_pct'] = max(0, min(100, self.state['channel_busy_pct']))

    def _apply_scenario(self):
        if not self.scenario:
            return
        if self.scenario == 'bsm_broadcast':
            self.state['message_rate_hz'] = 10
        elif self.scenario == 'intersection_alert':
            if random.random() < 0.1:
                self.state['collision_warnings'] += 1
        elif self.scenario == 'emergency_vehicle':
            self.state['message_rate_hz'] = 20
            self.state['range_m'] = 500
        elif self.scenario == 'platooning':
            self.state['message_rate_hz'] = 50
            self.state['latency_ms'] = max(1, 3 + random.gauss(0, 0.5))
        elif self.scenario == 'road_hazard':
            self.state['collision_warnings'] += random.choice([0, 0, 1])
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
