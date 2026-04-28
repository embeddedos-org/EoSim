# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""Maritime / ship systems simulator.

Pure Python, cross-platform (Linux/Windows/macOS). No OS-specific dependencies.
"""
import math
import random


class MaritimeSimulator:
    PRODUCT_TYPE = 'maritime'
    DISPLAY_NAME = 'Maritime / Ship Systems'
    SCENARIOS = {
        'autopilot_cruise': {'target_speed_knots': 15, 'description': 'Steady-state autopilot cruise'},
        'port_approach': {'description': 'Slow speed port approach with tug assist'},
        'storm_response': {'wind_knots': 45, 'description': 'Heavy weather response procedures'},
        'ais_broadcast': {'description': 'AIS transponder broadcast and receive'},
        'man_overboard': {'description': 'Man overboard emergency procedure'},
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
        from eosim.engine.native.peripherals.actuators import MotorController
        from eosim.engine.native.peripherals.composites import WatchdogTimer
        self.vm.add_peripheral('gps0', GPSModule('gps0', 0x40100300))
        self.vm.add_peripheral('imu0', IMUSensor('imu0', 0x40100200))
        self.vm.add_peripheral('temp0', TemperatureSensor('temp0', 0x40100010))
        self.vm.add_peripheral('motor0', MotorController('motor0', 0x40200000))
        self.vm.add_peripheral('wdt0', WatchdogTimer('wdt0', 0x40500200))
        self.state = {
            'heading_deg': 0, 'speed_knots': 0, 'rudder_angle': 0,
            'wind_speed_knots': 10, 'wave_height_m': 1.0, 'roll_deg': 0,
            'engine_rpm': 0, 'fuel_pct': 95.0, 'scenario': '',
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
        self.state['roll_deg'] = self.state['wave_height_m'] * 3 * math.sin(self.tick_count * 0.1) + random.gauss(0, 0.5)
        self.state['heading_deg'] = (self.state['heading_deg'] + self.state['rudder_angle'] * 0.05) % 360
        self.state['wind_speed_knots'] += random.gauss(0, 0.3)
        self.state['wind_speed_knots'] = max(0, min(80, self.state['wind_speed_knots']))
        self.state['fuel_pct'] = max(0, self.state['fuel_pct'] - 0.001 * self.state['speed_knots'])
        gps = self.vm.peripherals.get('gps0')
        if gps:
            gps.speed_mps = self.state['speed_knots'] * 0.5144

    def _apply_scenario(self):
        if not self.scenario:
            return
        if self.scenario == 'autopilot_cruise':
            target = self.SCENARIOS['autopilot_cruise']['target_speed_knots']
            err = target - self.state['speed_knots']
            self.state['speed_knots'] += err * 0.1
            self.state['engine_rpm'] = int(self.state['speed_knots'] * 100)
        elif self.scenario == 'port_approach':
            self.state['speed_knots'] = max(2, self.state['speed_knots'] - 0.1)
        elif self.scenario == 'storm_response':
            self.state['wind_speed_knots'] = 45 + random.gauss(0, 5)
            self.state['wave_height_m'] = 4 + random.gauss(0, 0.5)
            self.state['speed_knots'] = max(3, self.state['speed_knots'] - 0.2)
        elif self.scenario == 'man_overboard':
            self.state['speed_knots'] = max(0, self.state['speed_knots'] - 1)
            self.state['rudder_angle'] = 35
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
