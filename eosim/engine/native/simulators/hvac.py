# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""HVAC / climate control simulator.

Pure Python, cross-platform (Linux/Windows/macOS). No OS-specific dependencies.
"""
import random


class HVACSimulator:
    PRODUCT_TYPE = 'hvac'
    DISPLAY_NAME = 'HVAC / Climate Control'
    SCENARIOS = {
        'heating_cycle': {'target_c': 22, 'description': 'Space heating to setpoint'},
        'cooling_cycle': {'target_c': 22, 'description': 'Air conditioning to setpoint'},
        'ventilation': {'description': 'Fresh air ventilation only mode'},
        'defrost': {'description': 'Heat pump defrost cycle'},
        'energy_saving': {'description': 'Eco mode — wider deadband, lower fan speed'},
    }

    def __init__(self, vm):
        self.vm = vm
        self.tick_count = 0
        self.state = {}
        self.scenario = ''
        self._scenario_step = 0

    def setup(self):
        from eosim.engine.native.peripherals.sensors import TemperatureSensor
        from eosim.engine.native.peripherals.composites import WatchdogTimer
        self.vm.add_peripheral('temp_room', TemperatureSensor('temp_room', 0x40100010, -10, 50))
        self.vm.add_peripheral('temp_outdoor', TemperatureSensor('temp_outdoor', 0x40100020, -40, 50))
        self.vm.add_peripheral('wdt0', WatchdogTimer('wdt0', 0x40500200))
        self.state = {
            'room_temp_c': 18.0, 'target_temp_c': 22.0, 'humidity_pct': 50.0,
            'fan_speed_pct': 0, 'compressor_on': False, 'mode': 'off',
            'energy_kwh': 0.0, 'scenario': '',
        }

    def load_scenario(self, name):
        if name in self.SCENARIOS:
            self.scenario = name
            self._scenario_step = 0
            self.state['scenario'] = name
            cfg = self.SCENARIOS[name]
            if 'target_c' in cfg:
                self.state['target_temp_c'] = cfg['target_c']

    def tick(self):
        self.tick_count += 1
        for name, dev in self.vm.peripherals.items():
            if hasattr(dev, 'simulate_tick'):
                dev.simulate_tick()
        self._apply_scenario()
        target = self.state['target_temp_c']
        room = self.state['room_temp_c']
        if self.state['mode'] == 'heat' and room < target:
            self.state['room_temp_c'] += 0.1
            self.state['compressor_on'] = True
            self.state['fan_speed_pct'] = 60
        elif self.state['mode'] == 'cool' and room > target:
            self.state['room_temp_c'] -= 0.1
            self.state['compressor_on'] = True
            self.state['fan_speed_pct'] = 70
        else:
            self.state['compressor_on'] = False
            self.state['fan_speed_pct'] = max(0, self.state['fan_speed_pct'] - 5)
        self.state['room_temp_c'] += random.gauss(0, 0.02)
        self.state['humidity_pct'] += random.gauss(0, 0.1)
        self.state['humidity_pct'] = max(20, min(90, self.state['humidity_pct']))
        if self.state['compressor_on']:
            self.state['energy_kwh'] += 0.003
        tr = self.vm.peripherals.get('temp_room')
        if tr:
            tr.temperature = self.state['room_temp_c']

    def _apply_scenario(self):
        if not self.scenario:
            return
        if self.scenario == 'heating_cycle':
            self.state['mode'] = 'heat'
        elif self.scenario == 'cooling_cycle':
            self.state['mode'] = 'cool'
        elif self.scenario == 'ventilation':
            self.state['mode'] = 'fan'
            self.state['fan_speed_pct'] = 40
            self.state['compressor_on'] = False
        elif self.scenario == 'defrost':
            self.state['mode'] = 'defrost'
            self.state['compressor_on'] = self._scenario_step % 20 < 10
        elif self.scenario == 'energy_saving':
            self.state['mode'] = 'eco'
            self.state['fan_speed_pct'] = 30
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
