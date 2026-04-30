# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""Railway / train control simulator.

Pure Python, cross-platform (Linux/Windows/macOS). No OS-specific dependencies.
"""
import random


class RailwaySimulator:
    PRODUCT_TYPE = 'railway'
    DISPLAY_NAME = 'Railway / Train Control'
    SCENARIOS = {
        'departure_sequence': {'description': 'Station departure with door close and signal clear'},
        'emergency_brake': {'description': 'Emergency braking from full speed'},
        'station_approach': {'target_speed_kmh': 30, 'description': 'Deceleration for station stop'},
        'crossing_activation': {'description': 'Level crossing barrier activation'},
        'ptc_test': {'description': 'Positive train control enforcement'},
    }

    def __init__(self, vm):
        self.vm = vm
        self.tick_count = 0
        self.state = {}
        self.scenario = ''
        self._scenario_step = 0

    def setup(self):
        from eosim.engine.native.peripherals.sensors import (
            GPSModule, IMUSensor, TemperatureSensor,
        )
        from eosim.engine.native.peripherals.actuators import MotorController, BrakeActuator
        from eosim.engine.native.peripherals.composites import WatchdogTimer
        self.vm.add_peripheral('gps0', GPSModule('gps0', 0x40100300))
        self.vm.add_peripheral('imu0', IMUSensor('imu0', 0x40100200))
        self.vm.add_peripheral('temp0', TemperatureSensor('temp0', 0x40100010))
        self.vm.add_peripheral('motor0', MotorController('motor0', 0x40200000))
        self.vm.add_peripheral('brake0', BrakeActuator('brake0', 0x40200A00))
        self.vm.add_peripheral('wdt0', WatchdogTimer('wdt0', 0x40500200))
        self.state = {
            'speed_kmh': 0, 'track_section': 1, 'signal_aspect': 'green',
            'brake_pressure_pct': 0, 'doors_open': False, 'passengers': 150,
            'power_kw': 0, 'distance_km': 0, 'scenario': '',
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
        speed = self.state['speed_kmh']
        brake = self.state['brake_pressure_pct']
        if brake > 0:
            speed = max(0, speed - brake * 0.1)
        self.state['speed_kmh'] = round(speed, 1)
        self.state['distance_km'] += speed / 3600 * 0.01
        self.state['power_kw'] = speed * 20 + random.gauss(0, 10)

    def _apply_scenario(self):
        if not self.scenario:
            return
        if self.scenario == 'departure_sequence':
            if self._scenario_step == 5:
                self.state['doors_open'] = False
            if self._scenario_step == 15:
                self.state['signal_aspect'] = 'green'
            if self._scenario_step > 15:
                self.state['speed_kmh'] = min(120, self.state['speed_kmh'] + 2)
        elif self.scenario == 'emergency_brake':
            self.state['brake_pressure_pct'] = 100
            self.state['signal_aspect'] = 'red'
        elif self.scenario == 'station_approach':
            target = self.SCENARIOS['station_approach']['target_speed_kmh']
            if self.state['speed_kmh'] > target:
                self.state['brake_pressure_pct'] = 40
            else:
                self.state['brake_pressure_pct'] = 0
                if self.state['speed_kmh'] < 1:
                    self.state['doors_open'] = True
        elif self.scenario == 'crossing_activation':
            self.state['signal_aspect'] = 'yellow'
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
