# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""Submarine / AUV simulator.

Pure Python, cross-platform (Linux/Windows/macOS). No OS-specific dependencies.
"""
import math
import random


class SubmarineSimulator:
    PRODUCT_TYPE = 'submarine_sim'
    DISPLAY_NAME = 'Submarine / AUV'
    SCENARIOS = {
        'dive_sequence': {'target_depth_m': 100, 'description': 'Controlled dive to target depth'},
        'sonar_sweep': {'description': '360-degree active sonar sweep'},
        'waypoint_nav': {'description': 'Navigate to GPS waypoint underwater'},
        'emergency_surface': {'description': 'Emergency ballast blow and surface'},
        'silent_running': {'description': 'Minimal noise stealth operation'},
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
        from eosim.engine.native.peripherals.actuators import MotorController
        from eosim.engine.native.peripherals.composites import BatteryManagement, WatchdogTimer
        self.vm.add_peripheral('imu0', IMUSensor('imu0', 0x40100200))
        self.vm.add_peripheral('gps0', GPSModule('gps0', 0x40100300))
        self.vm.add_peripheral('pressure0', PressureSensor('pressure0', 0x40100100))
        self.vm.add_peripheral('temp_water', TemperatureSensor('temp_water', 0x40100010, -2, 35))
        self.vm.add_peripheral('motor0', MotorController('motor0', 0x40200000))
        self.vm.add_peripheral('bms0', BatteryManagement('bms0', 0x40500000, 48, 20000))
        self.vm.add_peripheral('wdt0', WatchdogTimer('wdt0', 0x40500200))
        self.state = {
            'depth_m': 0, 'heading_deg': 0, 'speed_knots': 0, 'pitch_deg': 0,
            'sonar_range_m': 500, 'battery_pct': 95.0, 'buoyancy': 0.0,
            'sonar_contacts': 0, 'scenario': '',
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
        depth = self.state['depth_m']
        buoyancy = self.state['buoyancy']
        depth += buoyancy * 0.1
        self.state['depth_m'] = max(0, min(500, depth))
        pressure = self.vm.peripherals.get('pressure0')
        if pressure:
            pressure.set_value(101.325 + depth * 10.1)
        self.state['heading_deg'] = (self.state['heading_deg'] + random.gauss(0, 0.2)) % 360
        self.state['battery_pct'] = max(0, self.state['battery_pct'] - 0.001)
        bms = self.vm.peripherals.get('bms0')
        if bms:
            bms.soc_percent = self.state['battery_pct']

    def _apply_scenario(self):
        if not self.scenario:
            return
        cfg = self.SCENARIOS.get(self.scenario, {})
        if self.scenario == 'dive_sequence':
            target = cfg.get('target_depth_m', 100)
            if self.state['depth_m'] < target:
                self.state['buoyancy'] = 2.0
                self.state['pitch_deg'] = -15
            else:
                self.state['buoyancy'] = 0
                self.state['pitch_deg'] = 0
        elif self.scenario == 'sonar_sweep':
            self.state['sonar_contacts'] = max(0, int(2 + random.gauss(0, 1)))
        elif self.scenario == 'emergency_surface':
            self.state['buoyancy'] = -5.0
            self.state['pitch_deg'] = 30
        elif self.scenario == 'silent_running':
            self.state['speed_knots'] = 3
            self.state['buoyancy'] = 0
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
