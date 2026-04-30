# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""Imaging sensor peripherals for EoSim simulation."""
import random
from eosim.engine.native.peripherals.sensors import SensorBase


class CameraModule(SensorBase):
    """Camera module (visible light)."""
    def __init__(self, name='cam0', base_addr=0x40140000, resolution=(1920, 1080)):
        super().__init__(name, base_addr)
        self.resolution = resolution
        self.fps = 30
        self.exposure_us = 10000
        self.frame_count = 0
    def simulate_tick(self):
        super().simulate_tick()
        if self._tick_count % max(1, 100 // self.fps) == 0:
            self.frame_count += 1
    def read_reg(self, offset):
        if offset == 0x00: return self.frame_count & 0xFFFFFFFF
        if offset == 0x04: return self.fps
        return 0


class ThermalCamera(SensorBase):
    """Thermal / infrared imaging camera (FLIR-style)."""
    def __init__(self, name='thcam0', base_addr=0x40140100, resolution=(160, 120)):
        super().__init__(name, base_addr)
        self.resolution = resolution
        self.min_temp_c = 20.0
        self.max_temp_c = 35.0
        self.center_temp_c = 28.0
    def simulate_tick(self):
        super().simulate_tick()
        self.center_temp_c += random.gauss(0, 0.1)
    def read_reg(self, offset):
        if offset == 0x00: return int(self.center_temp_c * 100) & 0xFFFFFFFF
        if offset == 0x04: return int(self.min_temp_c * 100) & 0xFFFFFFFF
        if offset == 0x08: return int(self.max_temp_c * 100) & 0xFFFFFFFF
        return 0


class InfraredSensor(SensorBase):
    """Single-point IR temperature sensor (MLX90614-style)."""
    def __init__(self, name='ir0', base_addr=0x40140200):
        super().__init__(name, base_addr)
        self.object_temp_c = 25.0
        self.ambient_temp_c = 22.0
    def simulate_tick(self):
        super().simulate_tick()
        self.object_temp_c += random.gauss(0, 0.05)
        self.ambient_temp_c += random.gauss(0, 0.02)
    def read_reg(self, offset):
        if offset == 0x00: return int(self.object_temp_c * 100) & 0xFFFFFFFF
        if offset == 0x04: return int(self.ambient_temp_c * 100) & 0xFFFFFFFF
        return 0


class XRaySensor(SensorBase):
    """X-ray detector / imaging sensor."""
    def __init__(self, name='xray0', base_addr=0x40140300):
        super().__init__(name, base_addr)
        self.dose_ugy = 0.0
        self.exposure_active = False
        self.frame_count = 0
    def simulate_tick(self):
        super().simulate_tick()
        if self.exposure_active:
            self.dose_ugy += 0.5
            self.frame_count += 1
    def read_reg(self, offset):
        if offset == 0x00: return int(self.dose_ugy * 100) & 0xFFFFFFFF
        if offset == 0x04: return self.frame_count
        return 0
