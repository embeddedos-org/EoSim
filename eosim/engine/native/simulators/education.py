# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""Education / lab equipment simulator.

Pure Python, cross-platform (Linux/Windows/macOS). No OS-specific dependencies.
"""
import random


class EducationSimulator:
    PRODUCT_TYPE = 'education'
    DISPLAY_NAME = 'Education / Lab Equipment'
    SCENARIOS = {
        'lab_experiment': {'description': 'Guided laboratory experiment with data collection'},
        'sensor_calibration': {'description': 'Multi-sensor calibration procedure'},
        'data_collection': {'description': 'Automated data acquisition from sensors'},
        'coding_exercise': {'description': 'Interactive coding exercise on microcontroller'},
        'quiz_mode': {'description': 'Assessment quiz with sensor-based answers'},
    }

    def __init__(self, vm):
        self.vm = vm
        self.tick_count = 0
        self.state = {}
        self.scenario = ''
        self._scenario_step = 0

    def setup(self):
        from eosim.engine.native.peripherals.sensors import (
            TemperatureSensor, LightSensor, ADCChannel,
        )
        from eosim.engine.native.peripherals.composites import WatchdogTimer
        self.vm.add_peripheral('temp0', TemperatureSensor('temp0', 0x40100010))
        self.vm.add_peripheral('light0', LightSensor('light0', 0x40100500))
        self.vm.add_peripheral('adc0', ADCChannel('adc0', 0x40100600))
        self.vm.add_peripheral('wdt0', WatchdogTimer('wdt0', 0x40500200))
        self.state = {
            'experiment_active': False, 'data_points': 0, 'score': 0,
            'timer_s': 0, 'sensor_readings': [], 'calibrated': False,
            'scenario': '',
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
        if self.state['experiment_active']:
            self.state['timer_s'] += 1
            temp = self.vm.peripherals.get('temp0')
            if temp:
                reading = round(temp.temperature, 2)
                self.state['sensor_readings'] = self.state['sensor_readings'][-99:] + [reading]
                self.state['data_points'] += 1

    def _apply_scenario(self):
        if not self.scenario:
            return
        if self.scenario == 'lab_experiment':
            self.state['experiment_active'] = True
        elif self.scenario == 'sensor_calibration':
            if self._scenario_step == 20:
                self.state['calibrated'] = True
        elif self.scenario == 'quiz_mode':
            if self._scenario_step % 30 == 0:
                self.state['score'] += random.choice([0, 1, 1, 1])
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
