# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""Environmental sensor peripherals for EoSim simulation."""
import random
import logging

logger = logging.getLogger(__name__)

from eosim.engine.native.peripherals.sensors import SensorBase


class HumiditySensor(SensorBase):
    """Dedicated humidity sensor (e.g., DHT22, SHT40)."""
    def __init__(self, name='humidity0', base_addr=0x40110000):
        super().__init__(name, base_addr)
        self.humidity_pct = 50.0
    def simulate_tick(self):
        super().simulate_tick()
        self.humidity_pct += random.gauss(0, 0.1)
        self.humidity_pct = max(0, min(100, self.humidity_pct))
    def read_reg(self, offset):
        if offset == 0x00: return int(self.humidity_pct * 100) & 0xFFFFFFFF
        return 0


class SoilMoistureSensor(SensorBase):
    """Capacitive soil moisture sensor."""
    def __init__(self, name='soil0', base_addr=0x40110100):
        super().__init__(name, base_addr)
        self.moisture_pct = 40.0
    def simulate_tick(self):
        super().simulate_tick()
        self.moisture_pct += random.gauss(0, 0.05)
        self.moisture_pct = max(0, min(100, self.moisture_pct))
    def read_reg(self, offset):
        if offset == 0x00: return int(self.moisture_pct * 100) & 0xFFFFFFFF
        return 0


class PHSensor(SensorBase):
    """pH measurement sensor."""
    def __init__(self, name='ph0', base_addr=0x40110200):
        super().__init__(name, base_addr)
        self.ph_value = 7.0
    def simulate_tick(self):
        super().simulate_tick()
        self.ph_value += random.gauss(0, 0.01)
        self.ph_value = max(0, min(14, self.ph_value))
    def read_reg(self, offset):
        if offset == 0x00: return int(self.ph_value * 1000) & 0xFFFFFFFF
        return 0


class GasSensor(SensorBase):
    """Multi-gas sensor (CO2, O2, CH4, CO)."""
    def __init__(self, name='gas0', base_addr=0x40110300, gas_type='CO2'):
        super().__init__(name, base_addr)
        self.gas_type = gas_type
        self.concentration_ppm = 400 if gas_type == 'CO2' else 0
    def simulate_tick(self):
        super().simulate_tick()
        self.concentration_ppm += random.gauss(0, 1)
        self.concentration_ppm = max(0, self.concentration_ppm)
    def read_reg(self, offset):
        if offset == 0x00: return int(self.concentration_ppm * 100) & 0xFFFFFFFF
        return 0


class WaterLevelSensor(SensorBase):
    """Ultrasonic/capacitive water level sensor."""
    def __init__(self, name='wlevel0', base_addr=0x40110400, max_level_cm=200):
        super().__init__(name, base_addr)
        self.level_cm = 100.0
        self.max_level_cm = max_level_cm
    def simulate_tick(self):
        super().simulate_tick()
        self.level_cm += random.gauss(0, 0.1)
        self.level_cm = max(0, min(self.max_level_cm, self.level_cm))
    def read_reg(self, offset):
        if offset == 0x00: return int(self.level_cm * 10) & 0xFFFFFFFF
        return 0


class UVSensor(SensorBase):
    """UV index sensor."""
    def __init__(self, name='uv0', base_addr=0x40110500):
        super().__init__(name, base_addr)
        self.uv_index = 3.0
    def simulate_tick(self):
        super().simulate_tick()
        self.uv_index += random.gauss(0, 0.1)
        self.uv_index = max(0, min(15, self.uv_index))
    def read_reg(self, offset):
        if offset == 0x00: return int(self.uv_index * 100) & 0xFFFFFFFF
        return 0


class NoiseLevelSensor(SensorBase):
    """Sound pressure level / noise sensor."""
    def __init__(self, name='noise0', base_addr=0x40110600):
        super().__init__(name, base_addr)
        self.level_db = 40.0
    def simulate_tick(self):
        super().simulate_tick()
        self.level_db += random.gauss(0, 0.5)
        self.level_db = max(20, min(140, self.level_db))
    def read_reg(self, offset):
        if offset == 0x00: return int(self.level_db * 100) & 0xFFFFFFFF
        return 0
