# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""Planetary rover simulator.

Pure Python, cross-platform (Linux/Windows/macOS). No OS-specific dependencies.
"""
import math
import random


class RoverSimulator:
    PRODUCT_TYPE = 'rover'
    DISPLAY_NAME = 'Planetary Rover'
    SCENARIOS = {
        'traverse': {'description': 'Autonomous traverse to waypoint'},
        'sample_collection': {'description': 'Soil/rock sample drill and collection'},
        'obstacle_avoidance': {'description': 'Hazard detection and path replanning'},
        'comm_window': {'description': 'Scheduled communication with orbiter'},
        'dust_storm': {'description': 'Dust storm — reduced solar power mode'},
    }

    def __init__(self, vm):
        self.vm = vm
        self.tick_count = 0
        self.state = {}
        self.scenario = ''
        self._scenario_step = 0

    def setup(self):
        from eosim.engine.native.peripherals.sensors import IMUSensor, GPSModule, TemperatureSensor
        from eosim.engine.native.peripherals.actuators import MotorController
        from eosim.engine.native.peripherals.composites import BatteryManagement, WatchdogTimer
        self.vm.add_peripheral('imu0', IMUSensor('imu0', 0x40100200))
        self.vm.add_peripheral('gps0', GPSModule('gps0', 0x40100300))
        self.vm.add_peripheral('temp0', TemperatureSensor('temp0', 0x40100010, -120, 20))
        self.vm.add_peripheral('motor0', MotorController('motor0', 0x40200000))
        self.vm.add_peripheral('bms0', BatteryManagement('bms0', 0x40500000, 24, 5000))
        self.vm.add_peripheral('wdt0', WatchdogTimer('wdt0', 0x40500200))
        self.state = {
            'position_x': 0.0, 'position_y': 0.0, 'heading_deg': 0,
            'speed_mps': 0, 'battery_pct': 95.0, 'solar_power_w': 100,
            'soil_sample_count': 0, 'distance_traveled_m': 0, 'scenario': '',
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
        speed = self.state['speed_mps']
        heading = math.radians(self.state['heading_deg'])
        self.state['position_x'] += speed * math.cos(heading) * 0.01
        self.state['position_y'] += speed * math.sin(heading) * 0.01
        self.state['distance_traveled_m'] += speed * 0.01
        self.state['battery_pct'] += (self.state['solar_power_w'] * 0.001 - speed * 0.01)
        self.state['battery_pct'] = max(0, min(100, self.state['battery_pct']))

    def _apply_scenario(self):
        if not self.scenario:
            return
        if self.scenario == 'traverse':
            self.state['speed_mps'] = 0.04
        elif self.scenario == 'sample_collection':
            self.state['speed_mps'] = 0
            if self._scenario_step == 50:
                self.state['soil_sample_count'] += 1
        elif self.scenario == 'obstacle_avoidance':
            self.state['heading_deg'] = (self.state['heading_deg'] + 15) % 360
            self.state['speed_mps'] = 0.02
        elif self.scenario == 'dust_storm':
            self.state['solar_power_w'] = 20 + random.gauss(0, 5)
            self.state['speed_mps'] = 0
        elif self.scenario == 'comm_window':
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
