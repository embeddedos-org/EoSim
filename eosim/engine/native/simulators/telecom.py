# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""Telecom / 5G base station simulator.

Pure Python, cross-platform (Linux/Windows/macOS). No OS-specific dependencies.
"""
import random


class TelecomSimulator:
    PRODUCT_TYPE = 'telecom'
    DISPLAY_NAME = 'Telecom / 5G'
    SCENARIOS = {
        'baseband_init': {'frequency_mhz': 3500, 'description': 'Initialize 5G NR baseband processing'},
        'packet_routing': {'throughput_mbps': 1000, 'description': 'High-throughput packet routing test'},
        'handover': {'description': 'Inter-cell handover procedure'},
        'qos_test': {'target_latency_ms': 1, 'description': 'QoS enforcement and priority queuing'},
        'spectrum_scan': {'description': 'Full spectrum scan for interference detection'},
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
        self.vm.add_peripheral('temp0', TemperatureSensor('temp0', 0x40100010, 0, 105))
        self.vm.add_peripheral('wdt0', WatchdogTimer('wdt0', 0x40500200))
        self.state = {
            'frequency_mhz': 3500, 'bandwidth_mhz': 100, 'connected_ues': 0,
            'throughput_mbps': 0.0, 'latency_ms': 5.0, 'snr_db': 20.0,
            'tx_power_dbm': 43, 'error_rate': 0.0, 'scenario': '',
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
        self.state['snr_db'] += random.gauss(0, 0.3)
        self.state['snr_db'] = max(0, min(40, self.state['snr_db']))
        self.state['latency_ms'] += random.gauss(0, 0.1)
        self.state['latency_ms'] = max(0.5, min(50, self.state['latency_ms']))
        self.state['throughput_mbps'] = max(0, self.state['snr_db'] * 50 + random.gauss(0, 10))
        self.state['error_rate'] = max(0, 0.01 / max(1, self.state['snr_db']))

    def _apply_scenario(self):
        if not self.scenario:
            return
        cfg = self.SCENARIOS.get(self.scenario, {})
        if self.scenario == 'baseband_init':
            if self._scenario_step < 50:
                self.state['connected_ues'] = min(100, self._scenario_step * 2)
        elif self.scenario == 'packet_routing':
            self.state['throughput_mbps'] = cfg.get('throughput_mbps', 1000) + random.gauss(0, 20)
        elif self.scenario == 'handover':
            if self._scenario_step == 20:
                self.state['connected_ues'] = max(0, self.state['connected_ues'] - 1)
                self.state['snr_db'] -= 5
            if self._scenario_step == 30:
                self.state['snr_db'] += 8
        elif self.scenario == 'qos_test':
            self.state['latency_ms'] = max(0.5, cfg.get('target_latency_ms', 1) + random.gauss(0, 0.2))
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
