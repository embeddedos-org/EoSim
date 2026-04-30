# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""Water treatment / distribution simulator.

Pure Python, cross-platform (Linux/Windows/macOS). No OS-specific dependencies.
"""
import random


class WaterSimulator:
    PRODUCT_TYPE = 'water'
    DISPLAY_NAME = 'Water Treatment / Distribution'
    SCENARIOS = {
        'filtration_cycle': {'description': 'Multi-stage filtration process'},
        'chlorination': {'target_ppm': 1.5, 'description': 'Chlorine dosing control'},
        'pump_station': {'description': 'Variable-speed pump station operation'},
        'leak_detection': {'description': 'Pressure anomaly leak detection'},
        'backwash': {'description': 'Filter backwash cleaning cycle'},
    }

    def __init__(self, vm):
        self.vm = vm
        self.tick_count = 0
        self.state = {}
        self.scenario = ''
        self._scenario_step = 0

    def setup(self):
        from eosim.engine.native.peripherals.sensors import PressureSensor, TemperatureSensor, ADCChannel
        from eosim.engine.native.peripherals.composites import WatchdogTimer
        self.vm.add_peripheral('pressure0', PressureSensor('pressure0', 0x40100100))
        self.vm.add_peripheral('temp0', TemperatureSensor('temp0', 0x40100010))
        self.vm.add_peripheral('adc0', ADCChannel('adc0', 0x40100600))
        self.vm.add_peripheral('wdt0', WatchdogTimer('wdt0', 0x40500200))
        self.state = {
            'flow_rate_lps': 50, 'pressure_bar': 4.0, 'ph_level': 7.0,
            'chlorine_ppm': 1.0, 'turbidity_ntu': 0.5, 'tank_level_pct': 75,
            'pump_speed_pct': 60, 'alarm': False, 'scenario': '',
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
        self.state['ph_level'] += random.gauss(0, 0.02)
        self.state['ph_level'] = max(5, min(9, self.state['ph_level']))
        self.state['turbidity_ntu'] += random.gauss(0, 0.01)
        self.state['turbidity_ntu'] = max(0, min(10, self.state['turbidity_ntu']))
        self.state['pressure_bar'] += random.gauss(0, 0.05)
        self.state['pressure_bar'] = max(0, min(10, self.state['pressure_bar']))
        inflow = self.state['flow_rate_lps'] * 0.001
        outflow = random.uniform(0.03, 0.07)
        self.state['tank_level_pct'] = max(0, min(100, self.state['tank_level_pct'] + inflow - outflow))

    def _apply_scenario(self):
        if not self.scenario:
            return
        if self.scenario == 'chlorination':
            target = self.SCENARIOS['chlorination']['target_ppm']
            err = target - self.state['chlorine_ppm']
            self.state['chlorine_ppm'] += err * 0.05 + random.gauss(0, 0.01)
        elif self.scenario == 'pump_station':
            self.state['pump_speed_pct'] = 60 + 20 * (1 if self.state['tank_level_pct'] < 50 else -0.5)
            self.state['flow_rate_lps'] = self.state['pump_speed_pct'] * 0.8
        elif self.scenario == 'leak_detection':
            if self._scenario_step == 15:
                self.state['pressure_bar'] -= 1.5
                self.state['alarm'] = True
        elif self.scenario == 'backwash':
            self.state['flow_rate_lps'] = -30  # reverse flow
            self.state['turbidity_ntu'] += 0.2
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
