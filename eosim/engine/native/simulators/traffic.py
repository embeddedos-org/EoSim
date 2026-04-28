# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""Traffic control simulator.

Pure Python, cross-platform (Linux/Windows/macOS). No OS-specific dependencies.
"""
import random


class TrafficSimulator:
    PRODUCT_TYPE = 'traffic'
    DISPLAY_NAME = 'Traffic Control'
    SCENARIOS = {
        'normal_cycle': {'description': 'Standard traffic light cycle'},
        'rush_hour': {'description': 'Extended green for main road during rush hour'},
        'emergency_vehicle': {'description': 'Emergency vehicle preemption'},
        'pedestrian_crossing': {'description': 'Pedestrian push-button crossing request'},
        'fault_mode': {'description': 'Flash yellow due to controller fault'},
    }

    def __init__(self, vm):
        self.vm = vm
        self.tick_count = 0
        self.state = {}
        self.scenario = ''
        self._scenario_step = 0

    def setup(self):
        from eosim.engine.native.peripherals.sensors import LightSensor, ProximitySensor, TemperatureSensor
        from eosim.engine.native.peripherals.composites import WatchdogTimer
        self.vm.add_peripheral('light0', LightSensor('light0', 0x40100500))
        self.vm.add_peripheral('prox0', ProximitySensor('prox0', 0x40100400))
        self.vm.add_peripheral('temp0', TemperatureSensor('temp0', 0x40100010))
        self.vm.add_peripheral('wdt0', WatchdogTimer('wdt0', 0x40500200))
        self.state = {
            'phase': 'green_ns', 'green_time_s': 30, 'red_time_s': 30,
            'vehicles_per_min': 20, 'pedestrian_waiting': False,
            'emergency_override': False, 'cycle_count': 0, 'scenario': '',
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
        cycle = self.state['green_time_s'] + self.state['red_time_s']
        pos = self.tick_count % cycle
        if self.state['emergency_override']:
            self.state['phase'] = 'green_all'
        elif pos < self.state['green_time_s']:
            self.state['phase'] = 'green_ns'
        elif pos < self.state['green_time_s'] + 3:
            self.state['phase'] = 'yellow_ns'
        else:
            self.state['phase'] = 'green_ew'
        self.state['vehicles_per_min'] = max(0, 20 + int(random.gauss(0, 3)))

    def _apply_scenario(self):
        if not self.scenario:
            return
        if self.scenario == 'rush_hour':
            self.state['green_time_s'] = 45
            self.state['vehicles_per_min'] = 40 + int(random.gauss(0, 5))
        elif self.scenario == 'emergency_vehicle':
            self.state['emergency_override'] = self._scenario_step < 20
        elif self.scenario == 'pedestrian_crossing':
            self.state['pedestrian_waiting'] = True
            if self._scenario_step == 10:
                self.state['phase'] = 'ped_walk'
            if self._scenario_step == 20:
                self.state['pedestrian_waiting'] = False
        elif self.scenario == 'fault_mode':
            self.state['phase'] = 'flash_yellow'
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
