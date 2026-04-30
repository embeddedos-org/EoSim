# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""Navigation sensor peripherals for EoSim simulation."""
import random
from eosim.engine.native.peripherals.sensors import SensorBase


class RadarSensor(SensorBase):
    """Radar distance/velocity sensor."""
    def __init__(self, name='radar0', base_addr=0x40130000, max_range_m=200):
        super().__init__(name, base_addr)
        self.distance_m = max_range_m
        self.velocity_mps = 0
        self.max_range_m = max_range_m
        self.target_detected = False
    def simulate_tick(self):
        super().simulate_tick()
        self.distance_m += random.gauss(0, 0.2)
        self.distance_m = max(0, min(self.max_range_m, self.distance_m))
        self.target_detected = self.distance_m < self.max_range_m * 0.9
    def read_reg(self, offset):
        if offset == 0x00: return int(self.distance_m * 100) & 0xFFFFFFFF
        if offset == 0x04: return int(self.velocity_mps * 100) & 0xFFFFFFFF
        if offset == 0x08: return int(self.target_detected)
        return 0


class LidarSensor(SensorBase):
    """LiDAR time-of-flight sensor."""
    def __init__(self, name='lidar0', base_addr=0x40130100, max_range_m=100):
        super().__init__(name, base_addr)
        self.distance_m = 50.0
        self.max_range_m = max_range_m
        self.points_per_sec = 100000
    def simulate_tick(self):
        super().simulate_tick()
        self.distance_m += random.gauss(0, 0.1)
        self.distance_m = max(0.1, min(self.max_range_m, self.distance_m))
    def read_reg(self, offset):
        if offset == 0x00: return int(self.distance_m * 1000) & 0xFFFFFFFF
        return 0


class DepthSounder(SensorBase):
    """Marine depth sounder / echo sounder."""
    def __init__(self, name='depth0', base_addr=0x40130200, max_depth_m=500):
        super().__init__(name, base_addr)
        self.depth_m = 50.0
        self.max_depth_m = max_depth_m
    def simulate_tick(self):
        super().simulate_tick()
        self.depth_m += random.gauss(0, 0.2)
        self.depth_m = max(0.5, min(self.max_depth_m, self.depth_m))
    def read_reg(self, offset):
        if offset == 0x00: return int(self.depth_m * 100) & 0xFFFFFFFF
        return 0


class SonarSensor(SensorBase):
    """Active/passive sonar sensor."""
    def __init__(self, name='sonar0', base_addr=0x40130300, max_range_m=1000):
        super().__init__(name, base_addr)
        self.range_m = 0
        self.bearing_deg = 0
        self.max_range_m = max_range_m
        self.contacts = 0
    def simulate_tick(self):
        super().simulate_tick()
        self.contacts = max(0, int(random.gauss(2, 1)))
    def read_reg(self, offset):
        if offset == 0x00: return int(self.range_m) & 0xFFFFFFFF
        if offset == 0x04: return int(self.bearing_deg * 10) & 0xFFFFFFFF
        if offset == 0x08: return self.contacts
        return 0


class CompassSensor(SensorBase):
    """Digital compass / magnetometer heading sensor."""
    def __init__(self, name='compass0', base_addr=0x40130400):
        super().__init__(name, base_addr)
        self.heading_deg = 0.0
    def simulate_tick(self):
        super().simulate_tick()
        self.heading_deg += random.gauss(0, 0.1)
        self.heading_deg = self.heading_deg % 360
    def read_reg(self, offset):
        if offset == 0x00: return int(self.heading_deg * 10) & 0xFFFFFFFF
        return 0
