# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""Launch vehicle / rocket simulator.

Pure Python, cross-platform (Linux/Windows/macOS). No OS-specific dependencies.
"""
import math
import random


class LaunchVehicleSimulator:
    PRODUCT_TYPE = 'launch_vehicle'
    DISPLAY_NAME = 'Launch Vehicle / Rocket'
    SCENARIOS = {
        'countdown': {'description': 'T-minus countdown and systems check'},
        'liftoff': {'description': 'Main engine ignition and liftoff'},
        'stage_separation': {'description': 'First stage separation and second stage ignition'},
        'orbit_insertion': {'target_altitude_km': 400, 'description': 'Orbit insertion burn'},
        'abort_sequence': {'description': 'Launch abort — engine cutoff and escape'},
    }

    def __init__(self, vm):
        self.vm = vm
        self.tick_count = 0
        self.state = {}
        self.scenario = ''
        self._scenario_step = 0

    def setup(self):
        from eosim.engine.native.peripherals.sensors import (
            IMUSensor, GPSModule, PressureSensor, TemperatureSensor,
        )
        from eosim.engine.native.peripherals.composites import WatchdogTimer
        self.vm.add_peripheral('imu0', IMUSensor('imu0', 0x40100200))
        self.vm.add_peripheral('gps0', GPSModule('gps0', 0x40100300))
        self.vm.add_peripheral('pressure0', PressureSensor('pressure0', 0x40100100))
        self.vm.add_peripheral('temp_engine', TemperatureSensor('temp_engine', 0x40100010, -50, 3000))
        self.vm.add_peripheral('wdt0', WatchdogTimer('wdt0', 0x40500200))
        self.state = {
            'altitude_km': 0, 'velocity_mps': 0, 'acceleration_g': 0,
            'fuel_pct': 100, 'stage': 1, 'thrust_kn': 0,
            'trajectory_angle_deg': 90, 'max_q': False, 'scenario': '',
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
        thrust = self.state['thrust_kn']
        if thrust > 0 and self.state['fuel_pct'] > 0:
            mass = 500000 * (0.1 + 0.9 * self.state['fuel_pct'] / 100)
            accel = thrust * 1000 / mass - 9.81
            self.state['acceleration_g'] = round(accel / 9.81, 2)
            self.state['velocity_mps'] += accel * 0.1
            angle = math.radians(self.state['trajectory_angle_deg'])
            self.state['altitude_km'] += self.state['velocity_mps'] * math.sin(angle) * 0.0001
            self.state['altitude_km'] = max(0, self.state['altitude_km'])
            self.state['fuel_pct'] = max(0, self.state['fuel_pct'] - 0.05)
        pressure = self.vm.peripherals.get('pressure0')
        if pressure:
            alt_m = self.state['altitude_km'] * 1000
            pressure.set_altitude(alt_m)
        self.state['max_q'] = 10 < self.state['altitude_km'] < 15

    def _apply_scenario(self):
        if not self.scenario:
            return
        if self.scenario == 'countdown':
            self.state['thrust_kn'] = 0
        elif self.scenario == 'liftoff':
            self.state['thrust_kn'] = 7600
            self.state['trajectory_angle_deg'] = max(45, 90 - self._scenario_step * 0.5)
        elif self.scenario == 'stage_separation':
            if self._scenario_step == 0:
                self.state['stage'] = 2
                self.state['fuel_pct'] = 100
                self.state['thrust_kn'] = 1000
        elif self.scenario == 'orbit_insertion':
            self.state['thrust_kn'] = 500
            self.state['trajectory_angle_deg'] = 0
        elif self.scenario == 'abort_sequence':
            self.state['thrust_kn'] = 0
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
