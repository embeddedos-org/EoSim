# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""Elevator / lift control simulator.

Pure Python, cross-platform (Linux/Windows/macOS). No OS-specific dependencies.
"""
import random


class ElevatorSimulator:
    PRODUCT_TYPE = 'elevator'
    DISPLAY_NAME = 'Elevator / Lift Control'
    SCENARIOS = {
        'normal_operation': {'description': 'Standard floor-to-floor passenger service'},
        'emergency_stop': {'description': 'Emergency stop between floors'},
        'fire_mode': {'description': 'Fire service mode — return to lobby'},
        'maintenance': {'description': 'Maintenance mode — manual jog'},
        'overload': {'description': 'Overload detection and door hold'},
    }

    def __init__(self, vm):
        self.vm = vm
        self.tick_count = 0
        self.state = {}
        self.scenario = ''
        self._scenario_step = 0

    def setup(self):
        from eosim.engine.native.peripherals.sensors import ProximitySensor, TemperatureSensor
        from eosim.engine.native.peripherals.actuators import MotorController
        from eosim.engine.native.peripherals.composites import WatchdogTimer
        self.vm.add_peripheral('prox0', ProximitySensor('prox0', 0x40100400))
        self.vm.add_peripheral('temp0', TemperatureSensor('temp0', 0x40100010))
        self.vm.add_peripheral('motor0', MotorController('motor0', 0x40200000))
        self.vm.add_peripheral('wdt0', WatchdogTimer('wdt0', 0x40500200))
        self.state = {
            'current_floor': 1, 'target_floor': 1, 'direction': 'idle',
            'door_state': 'closed', 'speed_mps': 0, 'load_kg': 0,
            'passengers': 0, 'total_floors': 20, 'scenario': '',
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
        cur = self.state['current_floor']
        tgt = self.state['target_floor']
        if cur < tgt and self.state['door_state'] == 'closed':
            self.state['direction'] = 'up'
            self.state['speed_mps'] = 2.5
            self.state['current_floor'] = min(tgt, cur + 1) if self._scenario_step % 5 == 0 else cur
        elif cur > tgt and self.state['door_state'] == 'closed':
            self.state['direction'] = 'down'
            self.state['speed_mps'] = 2.5
            self.state['current_floor'] = max(tgt, cur - 1) if self._scenario_step % 5 == 0 else cur
        elif cur == tgt:
            self.state['direction'] = 'idle'
            self.state['speed_mps'] = 0

    def _apply_scenario(self):
        if not self.scenario:
            return
        if self.scenario == 'normal_operation':
            if self._scenario_step == 0:
                self.state['target_floor'] = random.randint(1, self.state['total_floors'])
                self.state['passengers'] = random.randint(1, 8)
                self.state['load_kg'] = self.state['passengers'] * 75
            if self.state['current_floor'] == self.state['target_floor']:
                self.state['door_state'] = 'open'
        elif self.scenario == 'emergency_stop':
            self.state['speed_mps'] = 0
            self.state['direction'] = 'idle'
        elif self.scenario == 'fire_mode':
            self.state['target_floor'] = 1
            self.state['door_state'] = 'closed'
        elif self.scenario == 'overload':
            self.state['load_kg'] = 1500
            self.state['door_state'] = 'open'
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
