# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""AR/VR headset simulator.

Pure Python, cross-platform (Linux/Windows/macOS). No OS-specific dependencies.
"""
import math
import random


class ARVRSimulator:
    PRODUCT_TYPE = 'ar_vr'
    DISPLAY_NAME = 'AR/VR Headset'
    SCENARIOS = {
        'tracking_calibration': {'description': 'Inside-out tracking calibration'},
        'hand_tracking': {'description': 'Hand and finger tracking session'},
        'room_scan': {'description': 'Room-scale environment mesh scan'},
        'passthrough': {'description': 'Video passthrough AR mode'},
        'high_fidelity_render': {'description': 'High-resolution stereo rendering benchmark'},
    }

    def __init__(self, vm):
        self.vm = vm
        self.tick_count = 0
        self.state = {}
        self.scenario = ''
        self._scenario_step = 0

    def setup(self):
        from eosim.engine.native.peripherals.sensors import IMUSensor, ProximitySensor, TemperatureSensor
        from eosim.engine.native.peripherals.composites import BatteryManagement, WatchdogTimer
        self.vm.add_peripheral('imu0', IMUSensor('imu0', 0x40100200))
        self.vm.add_peripheral('prox0', ProximitySensor('prox0', 0x40100400))
        self.vm.add_peripheral('temp0', TemperatureSensor('temp0', 0x40100010))
        self.vm.add_peripheral('bms0', BatteryManagement('bms0', 0x40500000, 4, 5000))
        self.vm.add_peripheral('wdt0', WatchdogTimer('wdt0', 0x40500200))
        self.state = {
            'head_pos_x': 0.0, 'head_pos_y': 1.7, 'head_pos_z': 0.0,
            'head_rot_x': 0.0, 'head_rot_y': 0.0, 'head_rot_z': 0.0,
            'fps': 90, 'latency_ms': 11.0, 'tracking_quality': 95,
            'battery_pct': 100.0, 'scenario': '',
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
        imu = self.vm.peripherals.get('imu0')
        if imu:
            self.state['head_rot_x'] += imu.gyro[0] * 0.01
            self.state['head_rot_y'] += imu.gyro[1] * 0.01
            self.state['head_rot_z'] += imu.gyro[2] * 0.01
        self.state['fps'] = max(30, 90 + int(random.gauss(0, 2)))
        self.state['latency_ms'] = max(5, 11 + random.gauss(0, 1))
        self.state['battery_pct'] = max(0, self.state['battery_pct'] - 0.005)
        bms = self.vm.peripherals.get('bms0')
        if bms:
            bms.soc_percent = self.state['battery_pct']

    def _apply_scenario(self):
        if not self.scenario:
            return
        if self.scenario == 'tracking_calibration':
            self.state['tracking_quality'] = min(100, self.state['tracking_quality'] + 0.5)
        elif self.scenario == 'hand_tracking':
            self.state['tracking_quality'] = max(70, 90 + int(random.gauss(0, 3)))
        elif self.scenario == 'room_scan':
            self.state['head_rot_y'] += 2
        elif self.scenario == 'high_fidelity_render':
            self.state['fps'] = max(30, 72 + int(random.gauss(0, 5)))
            self.state['latency_ms'] = max(8, 15 + random.gauss(0, 2))
            self.state['battery_pct'] -= 0.01  # extra drain
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
