# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""Logistics / warehouse simulator.

Pure Python, cross-platform (Linux/Windows/macOS). No OS-specific dependencies.
"""
import random


class LogisticsSimulator:
    PRODUCT_TYPE = 'logistics'
    DISPLAY_NAME = 'Logistics / Warehouse'
    SCENARIOS = {
        'pick_and_place': {'description': 'AGV pick-and-place operation'},
        'sorting': {'description': 'Automated package sorting on conveyor'},
        'conveyor_routing': {'description': 'Multi-path conveyor routing'},
        'inventory_count': {'description': 'RFID-based inventory count cycle'},
        'dock_loading': {'description': 'Truck dock loading/unloading'},
    }

    def __init__(self, vm):
        self.vm = vm
        self.tick_count = 0
        self.state = {}
        self.scenario = ''
        self._scenario_step = 0

    def setup(self):
        from eosim.engine.native.peripherals.sensors import ProximitySensor, IMUSensor
        from eosim.engine.native.peripherals.actuators import MotorController
        from eosim.engine.native.peripherals.composites import WatchdogTimer
        self.vm.add_peripheral('prox0', ProximitySensor('prox0', 0x40100400))
        self.vm.add_peripheral('imu0', IMUSensor('imu0', 0x40100200))
        self.vm.add_peripheral('motor0', MotorController('motor0', 0x40200000))
        self.vm.add_peripheral('wdt0', WatchdogTimer('wdt0', 0x40500200))
        self.state = {
            'items_processed': 0, 'conveyor_speed_mps': 0, 'robot_position_x': 0,
            'robot_position_y': 0, 'queue_length': 0, 'throughput_per_hour': 0,
            'inventory_count': 10000, 'scenario': '',
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
        if self.state['conveyor_speed_mps'] > 0:
            if self.tick_count % 5 == 0:
                self.state['items_processed'] += 1
                self.state['queue_length'] = max(0, self.state['queue_length'] - 1)
        self.state['queue_length'] += random.choice([0, 0, 1])
        self.state['throughput_per_hour'] = self.state['items_processed'] * 3600 / max(1, self.tick_count)

    def _apply_scenario(self):
        if not self.scenario:
            return
        if self.scenario == 'pick_and_place':
            cycle = self._scenario_step % 20
            if cycle < 10:
                self.state['robot_position_x'] += 0.1
            else:
                self.state['robot_position_x'] -= 0.1
            if cycle == 10:
                self.state['items_processed'] += 1
        elif self.scenario == 'sorting':
            self.state['conveyor_speed_mps'] = 1.5
        elif self.scenario == 'conveyor_routing':
            self.state['conveyor_speed_mps'] = 2.0
        elif self.scenario == 'inventory_count':
            self.state['inventory_count'] += random.randint(-1, 1)
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
