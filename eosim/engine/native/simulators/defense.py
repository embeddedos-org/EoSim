# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""Defense / tactical systems simulator.

Pure Python, cross-platform (Linux/Windows/macOS). No OS-specific dependencies.
"""
import random


class DefenseSimulator:
    PRODUCT_TYPE = 'defense'
    DISPLAY_NAME = 'Defense / Tactical'
    SCENARIOS = {
        'secure_boot': {'description': 'Secure boot with crypto verification'},
        'crypto_ops': {'description': 'AES-256/SHA-384 cryptographic operations'},
        'radar_scan': {'range_km': 200, 'description': 'Radar sweep and target detection'},
        'jamming_response': {'description': 'Electronic countermeasure activation'},
        'comms_relay': {'description': 'Tactical radio relay operation'},
    }

    def __init__(self, vm):
        self.vm = vm
        self.tick_count = 0
        self.state = {}
        self.scenario = ''
        self._scenario_step = 0

    def setup(self):
        from eosim.engine.native.peripherals.sensors import TemperatureSensor, IMUSensor, GPSModule
        from eosim.engine.native.peripherals.composites import WatchdogTimer
        self.vm.add_peripheral('imu0', IMUSensor('imu0', 0x40100200))
        self.vm.add_peripheral('gps0', GPSModule('gps0', 0x40100300))
        self.vm.add_peripheral('temp0', TemperatureSensor('temp0', 0x40100010))
        self.vm.add_peripheral('wdt0', WatchdogTimer('wdt0', 0x40500200))
        self.state = {
            'encryption_active': False, 'radar_range_km': 0, 'target_count': 0,
            'threat_level': 'green', 'radio_freq_mhz': 225.0, 'crypto_ops_per_sec': 0,
            'jamming_detected': False, 'scenario': '',
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
        if self.state['encryption_active']:
            self.state['crypto_ops_per_sec'] = 50000 + int(random.gauss(0, 500))
        self.state['radio_freq_mhz'] += random.gauss(0, 0.001)

    def _apply_scenario(self):
        if not self.scenario:
            return
        if self.scenario == 'secure_boot':
            if self._scenario_step == 5:
                self.state['encryption_active'] = True
        elif self.scenario == 'radar_scan':
            self.state['radar_range_km'] = 200
            self.state['target_count'] = max(0, int(3 + random.gauss(0, 1)))
            if self.state['target_count'] > 4:
                self.state['threat_level'] = 'red'
            elif self.state['target_count'] > 2:
                self.state['threat_level'] = 'yellow'
        elif self.scenario == 'jamming_response':
            if self._scenario_step == 10:
                self.state['jamming_detected'] = True
                self.state['threat_level'] = 'red'
            if self._scenario_step == 30:
                self.state['radio_freq_mhz'] += 50  # frequency hop
                self.state['jamming_detected'] = False
        elif self.scenario == 'crypto_ops':
            self.state['encryption_active'] = True
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
