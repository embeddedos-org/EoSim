# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""Industrial sensor peripherals for EoSim simulation."""
import random
from eosim.engine.native.peripherals.sensors import SensorBase


class LoadCell(SensorBase):
    """Strain-gauge load cell / force sensor."""
    def __init__(self, name='loadcell0', base_addr=0x40120000, max_kg=1000):
        super().__init__(name, base_addr)
        self.force_kg = 0.0
        self.max_kg = max_kg
    def simulate_tick(self):
        super().simulate_tick()
        self.force_kg += random.gauss(0, 0.1)
        self.force_kg = max(0, min(self.max_kg, self.force_kg))
    def read_reg(self, offset):
        if offset == 0x00: return int(self.force_kg * 100) & 0xFFFFFFFF
        return 0


class FlowSensor(SensorBase):
    """Liquid/gas flow rate sensor."""
    def __init__(self, name='flow0', base_addr=0x40120100):
        super().__init__(name, base_addr)
        self.flow_lpm = 0.0
        self.total_liters = 0.0
    def simulate_tick(self):
        super().simulate_tick()
        self.flow_lpm += random.gauss(0, 0.05)
        self.flow_lpm = max(0, self.flow_lpm)
        self.total_liters += self.flow_lpm / 60 / 100
    def read_reg(self, offset):
        if offset == 0x00: return int(self.flow_lpm * 100) & 0xFFFFFFFF
        if offset == 0x04: return int(self.total_liters * 100) & 0xFFFFFFFF
        return 0


class VibrationSensor(SensorBase):
    """Vibration / accelerometer for predictive maintenance."""
    def __init__(self, name='vib0', base_addr=0x40120200):
        super().__init__(name, base_addr)
        self.rms_g = 0.1
        self.peak_g = 0.5
        self.frequency_hz = 50
    def simulate_tick(self):
        super().simulate_tick()
        self.rms_g += random.gauss(0, 0.01)
        self.rms_g = max(0, min(10, self.rms_g))
        self.peak_g = self.rms_g * (2 + random.gauss(0, 0.3))
    def read_reg(self, offset):
        if offset == 0x00: return int(self.rms_g * 1000) & 0xFFFFFFFF
        if offset == 0x04: return int(self.peak_g * 1000) & 0xFFFFFFFF
        return 0


class TorqueSensor(SensorBase):
    """Rotary torque transducer."""
    def __init__(self, name='torque0', base_addr=0x40120300, max_nm=100):
        super().__init__(name, base_addr)
        self.torque_nm = 0.0
        self.max_nm = max_nm
    def simulate_tick(self):
        super().simulate_tick()
        self.torque_nm += random.gauss(0, 0.1)
        self.torque_nm = max(-self.max_nm, min(self.max_nm, self.torque_nm))
    def read_reg(self, offset):
        if offset == 0x00: return int(self.torque_nm * 100) & 0xFFFFFFFF
        return 0


class StrainGauge(SensorBase):
    """Strain gauge sensor for structural monitoring."""
    def __init__(self, name='strain0', base_addr=0x40120400):
        super().__init__(name, base_addr)
        self.strain_ue = 0.0  # microstrain
    def simulate_tick(self):
        super().simulate_tick()
        self.strain_ue += random.gauss(0, 0.5)
    def read_reg(self, offset):
        if offset == 0x00: return int(self.strain_ue * 100) & 0xFFFFFFFF
        return 0


class LevelSensor(SensorBase):
    """Tank/silo level sensor (radar/ultrasonic)."""
    def __init__(self, name='level0', base_addr=0x40120500, max_m=10):
        super().__init__(name, base_addr)
        self.level_m = 5.0
        self.max_m = max_m
    def simulate_tick(self):
        super().simulate_tick()
        self.level_m += random.gauss(0, 0.01)
        self.level_m = max(0, min(self.max_m, self.level_m))
    def read_reg(self, offset):
        if offset == 0x00: return int(self.level_m * 1000) & 0xFFFFFFFF
        return 0
