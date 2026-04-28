# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""Oil & gas / pipeline SCADA simulator.

Pure Python, cross-platform (Linux/Windows/macOS). No OS-specific dependencies.
"""
import random


class OilGasSimulator:
    PRODUCT_TYPE = 'oil_gas'
    DISPLAY_NAME = 'Oil & Gas / Pipeline'
    SCENARIOS = {
        'pipeline_flow': {'description': 'Steady-state pipeline flow control'},
        'wellhead_control': {'description': 'Wellhead pressure and choke management'},
        'compressor_station': {'description': 'Gas compressor station operation'},
        'pig_run': {'description': 'Pipeline inspection gauge (PIG) run'},
        'emergency_shutdown': {'description': 'Emergency shutdown (ESD) activation'},
    }

    def __init__(self, vm):
        self.vm = vm
        self.tick_count = 0
        self.state = {}
        self.scenario = ''
        self._scenario_step = 0

    def setup(self):
        from eosim.engine.native.peripherals.sensors import PressureSensor, TemperatureSensor
        from eosim.engine.native.peripherals.composites import WatchdogTimer
        self.vm.add_peripheral('pressure0', PressureSensor('pressure0', 0x40100100))
        self.vm.add_peripheral('temp0', TemperatureSensor('temp0', 0x40100010))
        self.vm.add_peripheral('wdt0', WatchdogTimer('wdt0', 0x40500200))
        self.state = {
            'flow_rate_bpd': 5000, 'pressure_psi': 1200, 'temperature_c': 45,
            'valve_position_pct': 80, 'gas_detection_ppm': 0, 'pipeline_integrity': 100,
            'compressor_rpm': 0, 'esd_active': False, 'scenario': '',
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
        self.state['pressure_psi'] += random.gauss(0, 5)
        self.state['pressure_psi'] = max(0, min(3000, self.state['pressure_psi']))
        self.state['temperature_c'] += random.gauss(0, 0.2)
        self.state['flow_rate_bpd'] = self.state['valve_position_pct'] * 62.5 + random.gauss(0, 50)
        self.state['gas_detection_ppm'] = max(0, self.state['gas_detection_ppm'] + random.gauss(0, 0.5))

    def _apply_scenario(self):
        if not self.scenario:
            return
        if self.scenario == 'pipeline_flow':
            self.state['valve_position_pct'] = 80
        elif self.scenario == 'wellhead_control':
            self.state['pressure_psi'] = 2500 + random.gauss(0, 50)
        elif self.scenario == 'compressor_station':
            self.state['compressor_rpm'] = 3600
            self.state['pressure_psi'] = min(3000, self.state['pressure_psi'] + 10)
        elif self.scenario == 'pig_run':
            self.state['pipeline_integrity'] -= 0.01
        elif self.scenario == 'emergency_shutdown':
            self.state['esd_active'] = True
            self.state['valve_position_pct'] = 0
            self.state['compressor_rpm'] = 0
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
