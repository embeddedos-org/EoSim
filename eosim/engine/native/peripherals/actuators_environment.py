# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""Environmental actuator peripherals for EoSim simulation."""
import random
from eosim.engine.native.peripherals.actuators import ActuatorBase


class IrrigationValve(ActuatorBase):
    """Solenoid irrigation valve controller."""
    def __init__(self, name='valve0', base_addr=0x40220000):
        super().__init__(name, base_addr)
        self.open = False
        self.flow_lpm = 0.0
    def simulate_tick(self):
        super().simulate_tick()
        self.flow_lpm = 10.0 + random.gauss(0, 0.5) if self.open else 0.0


class FanController(ActuatorBase):
    """Variable-speed fan controller (PWM)."""
    def __init__(self, name='fan0', base_addr=0x40220100):
        super().__init__(name, base_addr)
        self.speed_pct = 0
        self.rpm = 0
    def simulate_tick(self):
        super().simulate_tick()
        self.rpm = int(self.speed_pct * 30 + random.gauss(0, 10))


class HeaterElement(ActuatorBase):
    """Resistive heater element controller."""
    def __init__(self, name='heater0', base_addr=0x40220200):
        super().__init__(name, base_addr)
        self.power_pct = 0
        self.temperature_c = 25.0
        self.max_temp_c = 300.0
    def simulate_tick(self):
        super().simulate_tick()
        self.temperature_c += self.power_pct * 0.02 - 0.5
        self.temperature_c = max(15, min(self.max_temp_c, self.temperature_c))


class Compressor(ActuatorBase):
    """Refrigerant/air compressor controller."""
    def __init__(self, name='compressor0', base_addr=0x40220300):
        super().__init__(name, base_addr)
        self.running = False
        self.pressure_bar = 0.0
        self.rpm = 0
    def simulate_tick(self):
        super().simulate_tick()
        if self.running:
            self.pressure_bar += 0.1
            self.rpm = 3000 + int(random.gauss(0, 50))
        else:
            self.pressure_bar = max(0, self.pressure_bar - 0.05)
            self.rpm = 0


class Damper(ActuatorBase):
    """HVAC damper / louver actuator."""
    def __init__(self, name='damper0', base_addr=0x40220400):
        super().__init__(name, base_addr)
        self.position_pct = 0  # 0=closed, 100=open
        self.target_pct = 0
    def simulate_tick(self):
        super().simulate_tick()
        err = self.target_pct - self.position_pct
        self.position_pct += err * 0.1
