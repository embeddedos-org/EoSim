# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""Thermal simulation and analysis."""


class ThermalModel:
    """Simple lumped-parameter thermal model."""

    def __init__(self, ambient_c=25.0, thermal_resistance_cw=10.0, thermal_capacitance_jc=5.0):
        self.ambient_c = ambient_c
        self.r_th = thermal_resistance_cw  # C/W
        self.c_th = thermal_capacitance_jc  # J/C
        self.temperature_c = ambient_c

    def step(self, power_w, dt_s=0.01):
        delta = (power_w - (self.temperature_c - self.ambient_c) / self.r_th) * dt_s / self.c_th
        self.temperature_c += delta
        return self.temperature_c

    def steady_state(self, power_w):
        return self.ambient_c + power_w * self.r_th

    def time_to_limit(self, power_w, limit_c=85.0, dt_s=0.01):
        temp = self.ambient_c
        t = 0.0
        while temp < limit_c:
            delta = (power_w - (temp - self.ambient_c) / self.r_th) * dt_s / self.c_th
            temp += delta
            t += dt_s
            if t > 3600:
                return float('inf')
        return t
