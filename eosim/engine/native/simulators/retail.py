# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""Retail / POS system simulator.

Pure Python, cross-platform (Linux/Windows/macOS). No OS-specific dependencies.
"""
import random


class RetailSimulator:
    PRODUCT_TYPE = 'retail'
    DISPLAY_NAME = 'Retail / POS Systems'
    SCENARIOS = {
        'checkout_transaction': {'description': 'Standard checkout with barcode scanning'},
        'inventory_scan': {'description': 'RFID inventory scanning cycle'},
        'payment_process': {'description': 'EMV chip card payment processing'},
        'self_checkout': {'description': 'Self-service checkout kiosk operation'},
        'loyalty_lookup': {'description': 'Customer loyalty program lookup'},
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
        self.vm.add_peripheral('temp0', TemperatureSensor('temp0', 0x40100010))
        self.vm.add_peripheral('wdt0', WatchdogTimer('wdt0', 0x40500200))
        self.state = {
            'transactions_count': 0, 'items_scanned': 0, 'total_revenue': 0.0,
            'queue_length': 0, 'scanner_active': False, 'payment_pending': False,
            'receipt_printed': False, 'scenario': '',
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
        self.state['queue_length'] = max(0, self.state['queue_length'] + random.randint(-1, 1))

    def _apply_scenario(self):
        if not self.scenario:
            return
        if self.scenario == 'checkout_transaction':
            if self._scenario_step < 10:
                self.state['scanner_active'] = True
                self.state['items_scanned'] += 1
            elif self._scenario_step == 10:
                self.state['scanner_active'] = False
                self.state['payment_pending'] = True
            elif self._scenario_step == 15:
                self.state['payment_pending'] = False
                self.state['total_revenue'] += random.uniform(5, 200)
                self.state['transactions_count'] += 1
                self.state['receipt_printed'] = True
        elif self.scenario == 'inventory_scan':
            self.state['items_scanned'] += random.randint(5, 20)
        elif self.scenario == 'payment_process':
            if self._scenario_step < 5:
                self.state['payment_pending'] = True
            else:
                self.state['payment_pending'] = False
                self.state['transactions_count'] += 1
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
