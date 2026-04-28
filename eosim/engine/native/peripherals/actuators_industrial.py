# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""Industrial actuator peripherals for EoSim simulation."""
import random
from eosim.engine.native.peripherals.actuators import ActuatorBase


class ConveyorBelt(ActuatorBase):
    """Variable-speed conveyor belt controller."""
    def __init__(self, name='conveyor0', base_addr=0x40210000):
        super().__init__(name, base_addr)
        self.speed_mps = 0.0
        self.target_speed = 0.0
        self.running = False
    def simulate_tick(self):
        super().simulate_tick()
        if self.running:
            err = self.target_speed - self.speed_mps
            self.speed_mps += err * 0.1
        else:
            self.speed_mps *= 0.9


class CraneController(ActuatorBase):
    """Overhead/tower crane hoist controller."""
    def __init__(self, name='crane0', base_addr=0x40210100):
        super().__init__(name, base_addr)
        self.hoist_position_m = 0.0
        self.load_kg = 0.0
        self.slew_deg = 0.0
        self.trolley_m = 0.0
    def simulate_tick(self):
        super().simulate_tick()
        self.hoist_position_m += random.gauss(0, 0.001)


class DrillMotor(ActuatorBase):
    """Rotary drill motor controller."""
    def __init__(self, name='drill0', base_addr=0x40210200):
        super().__init__(name, base_addr)
        self.rpm = 0
        self.torque_nm = 0.0
        self.depth_m = 0.0
    def simulate_tick(self):
        super().simulate_tick()
        if self.rpm > 0:
            self.depth_m += 0.001
            self.torque_nm = self.rpm * 0.1 + random.gauss(0, 1)


class PrintHead(ActuatorBase):
    """Inkjet/3D printer print head controller."""
    def __init__(self, name='printhead0', base_addr=0x40210300):
        super().__init__(name, base_addr)
        self.x_pos = 0.0
        self.y_pos = 0.0
        self.temperature_c = 25.0
        self.flow_rate = 0.0
    def simulate_tick(self):
        super().simulate_tick()
        if self.flow_rate > 0:
            self.temperature_c += random.gauss(0, 0.1)


class Extruder(ActuatorBase):
    """3D printer / plastic extruder controller."""
    def __init__(self, name='extruder0', base_addr=0x40210400):
        super().__init__(name, base_addr)
        self.temperature_c = 25.0
        self.target_temp_c = 200.0
        self.feed_rate_mm_s = 0.0
        self.filament_used_mm = 0.0
    def simulate_tick(self):
        super().simulate_tick()
        err = self.target_temp_c - self.temperature_c
        self.temperature_c += err * 0.02 + random.gauss(0, 0.1)
        if self.feed_rate_mm_s > 0:
            self.filament_used_mm += self.feed_rate_mm_s * 0.01
