# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""Network router / switch simulator.

Pure Python, cross-platform (Linux/Windows/macOS). No OS-specific dependencies.
"""
import random


class NetworkSimulator:
    PRODUCT_TYPE = 'network'
    DISPLAY_NAME = 'Network / Router'
    SCENARIOS = {
        'routing_table_update': {'description': 'OSPF/BGP routing table convergence'},
        'ddos_mitigation': {'description': 'DDoS attack detection and mitigation'},
        'failover': {'description': 'Link failover to redundant path'},
        'vlan_config': {'description': 'VLAN configuration and trunk setup'},
        'traffic_shaping': {'description': 'QoS traffic shaping and policing'},
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
        self.vm.add_peripheral('temp0', TemperatureSensor('temp0', 0x40100010, 0, 85))
        self.vm.add_peripheral('wdt0', WatchdogTimer('wdt0', 0x40500200))
        self.state = {
            'interfaces_up': 4, 'packets_per_sec': 0, 'bandwidth_gbps': 10.0,
            'cpu_util_pct': 5.0, 'routing_entries': 250, 'arp_table_size': 50,
            'dropped_packets': 0, 'uptime_s': 0, 'scenario': '',
        }

    def load_scenario(self, name):
        if name in self.SCENARIOS:
            self.scenario = name
            self._scenario_step = 0
            self.state['scenario'] = name

    def tick(self):
        self.tick_count += 1
        self.state['uptime_s'] += 1
        for name, dev in self.vm.peripherals.items():
            if hasattr(dev, 'simulate_tick'):
                dev.simulate_tick()
        self._apply_scenario()
        self.state['packets_per_sec'] = max(0, int(10000 + random.gauss(0, 500)))
        self.state['cpu_util_pct'] += random.gauss(0, 0.5)
        self.state['cpu_util_pct'] = max(1, min(100, self.state['cpu_util_pct']))

    def _apply_scenario(self):
        if not self.scenario:
            return
        if self.scenario == 'routing_table_update':
            if self._scenario_step < 20:
                self.state['routing_entries'] += random.randint(1, 5)
                self.state['cpu_util_pct'] = min(80, self.state['cpu_util_pct'] + 2)
        elif self.scenario == 'ddos_mitigation':
            self.state['packets_per_sec'] = 500000 + int(random.gauss(0, 50000))
            self.state['cpu_util_pct'] = min(98, 70 + random.gauss(0, 5))
            self.state['dropped_packets'] += random.randint(100, 1000)
        elif self.scenario == 'failover':
            if self._scenario_step == 10:
                self.state['interfaces_up'] = 3
            if self._scenario_step == 20:
                self.state['interfaces_up'] = 4
        elif self.scenario == 'traffic_shaping':
            self.state['bandwidth_gbps'] = 8.0 + random.gauss(0, 0.2)
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
