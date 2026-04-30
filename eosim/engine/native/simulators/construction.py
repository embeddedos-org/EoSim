# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""Construction equipment simulator.

Pure Python, cross-platform (Linux/Windows/macOS). No OS-specific dependencies.
"""
import random


class ConstructionSimulator:
    PRODUCT_TYPE = 'construction'
    DISPLAY_NAME = 'Construction Equipment'
    SCENARIOS = {
        'crane_lift': {'load_kg': 5000, 'description': 'Tower crane heavy lift operation'},
        'excavation': {'description': 'Hydraulic excavator digging cycle'},
        'concrete_pour': {'description': 'Concrete pump and vibrator operation'},
        'pile_driving': {'description': 'Driven pile installation'},
        'grading': {'description': 'Motor grader surface leveling'},
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
        from eosim.engine.native.peripherals.composites import WatchdogTimer
        self.vm.add_peripheral('imu0', IMUSensor('imu0', 0x40100200))
        self.vm.add_peripheral('gps0', GPSModule('gps0', 0x40100300))
        self.vm.add_peripheral('temp0', TemperatureSensor('temp0', 0x40100010))
        self.vm.add_peripheral('motor0', MotorController('motor0', 0x40200000))
        self.vm.add_peripheral('wdt0', WatchdogTimer('wdt0', 0x40500200))
        self.state = {
            'boom_angle_deg': 0, 'load_kg': 0, 'hydraulic_pressure_bar': 200,
            'engine_rpm': 0, 'fuel_level_pct': 90.0, 'bucket_pos_m': 0,
            'slew_angle_deg': 0, 'scenario': '',
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
        self.state['hydraulic_pressure_bar'] += random.gauss(0, 2)
        self.state['hydraulic_pressure_bar'] = max(0, min(350, self.state['hydraulic_pressure_bar']))
        if self.state['engine_rpm'] > 0:
            self.state['fuel_level_pct'] = max(0, self.state['fuel_level_pct'] - 0.005)

    def _apply_scenario(self):
        if not self.scenario:
            return
        if self.scenario == 'crane_lift':
            self.state['load_kg'] = self.SCENARIOS['crane_lift']['load_kg']
            self.state['boom_angle_deg'] = min(80, self.state['boom_angle_deg'] + 0.5)
            self.state['engine_rpm'] = 1800
        elif self.scenario == 'excavation':
            self.state['engine_rpm'] = 2000
            cycle = self._scenario_step % 40
            self.state['bucket_pos_m'] = -3 if cycle < 20 else 2
        elif self.scenario == 'concrete_pour':
            self.state['engine_rpm'] = 1500
            self.state['hydraulic_pressure_bar'] = 280 + random.gauss(0, 5)
        elif self.scenario == 'pile_driving':
            self.state['engine_rpm'] = 2200
            if self._scenario_step % 5 == 0:
                self.state['bucket_pos_m'] -= 0.1
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
