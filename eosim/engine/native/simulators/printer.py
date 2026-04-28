# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""Printer / 3D printer simulator.

Pure Python, cross-platform (Linux/Windows/macOS). No OS-specific dependencies.
"""
import random


class PrinterSimulator:
    PRODUCT_TYPE = 'printer'
    DISPLAY_NAME = 'Printer / 3D Printer'
    SCENARIOS = {
        'print_job': {'layers': 200, 'description': 'Multi-layer 3D print job'},
        'calibration': {'description': 'Nozzle and bed calibration sequence'},
        'filament_change': {'description': 'Mid-print filament change procedure'},
        'bed_leveling': {'description': 'Automatic bed leveling with probe'},
        'nozzle_clean': {'description': 'Nozzle purge and cleaning cycle'},
    }

    def __init__(self, vm):
        self.vm = vm
        self.tick_count = 0
        self.state = {}
        self.scenario = ''
        self._scenario_step = 0

    def setup(self):
        from eosim.engine.native.peripherals.sensors import TemperatureSensor
        from eosim.engine.native.peripherals.actuators import MotorController
        from eosim.engine.native.peripherals.composites import WatchdogTimer
        self.vm.add_peripheral('temp_nozzle', TemperatureSensor('temp_nozzle', 0x40100010, 0, 300))
        self.vm.add_peripheral('temp_bed', TemperatureSensor('temp_bed', 0x40100020, 0, 120))
        self.vm.add_peripheral('motor0', MotorController('motor0', 0x40200000))
        self.vm.add_peripheral('wdt0', WatchdogTimer('wdt0', 0x40500200))
        self.state = {
            'nozzle_temp_c': 25, 'bed_temp_c': 25, 'print_progress_pct': 0,
            'layer_number': 0, 'total_layers': 200, 'filament_remaining_mm': 50000,
            'x_pos': 0, 'y_pos': 0, 'z_pos': 0, 'printing': False, 'scenario': '',
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
        tn = self.vm.peripherals.get('temp_nozzle')
        tb = self.vm.peripherals.get('temp_bed')
        if tn:
            self.state['nozzle_temp_c'] = round(tn.temperature, 1)
        if tb:
            self.state['bed_temp_c'] = round(tb.temperature, 1)
        if self.state['printing']:
            self.state['x_pos'] += random.uniform(-5, 5)
            self.state['y_pos'] += random.uniform(-5, 5)
            self.state['filament_remaining_mm'] = max(0, self.state['filament_remaining_mm'] - 0.5)

    def _apply_scenario(self):
        if not self.scenario:
            return
        tn = self.vm.peripherals.get('temp_nozzle')
        tb = self.vm.peripherals.get('temp_bed')
        if self.scenario == 'print_job':
            if tn and tn.temperature < 210:
                tn.temperature += 2
            if tb and tb.temperature < 60:
                tb.temperature += 1
            if tn and tn.temperature >= 210 and tb and tb.temperature >= 60:
                self.state['printing'] = True
                total = self.SCENARIOS['print_job']['layers']
                if self._scenario_step % 10 == 0 and self.state['layer_number'] < total:
                    self.state['layer_number'] += 1
                    self.state['z_pos'] += 0.2
                    self.state['print_progress_pct'] = round(100 * self.state['layer_number'] / total, 1)
        elif self.scenario == 'calibration':
            self.state['printing'] = False
        elif self.scenario == 'bed_leveling':
            self.state['z_pos'] = 0.1 * (self._scenario_step % 9)
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
