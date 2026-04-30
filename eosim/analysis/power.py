# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""Power consumption modeling and analysis."""
from dataclasses import dataclass, field


@dataclass
class PowerProfile:
    name: str = ""
    voltage_v: float = 3.3
    current_active_ma: float = 50.0
    current_sleep_ma: float = 0.01
    current_deep_sleep_ua: float = 1.0
    clock_mhz: float = 100.0


class PowerAnalyzer:
    """Analyze power consumption of simulated platforms."""

    def __init__(self):
        self.profiles = {}
        self.measurements = []

    def add_profile(self, name, profile):
        self.profiles[name] = profile

    def measure(self, profile_name, mode='active', duration_s=1.0):
        p = self.profiles.get(profile_name)
        if not p:
            return {}
        if mode == 'active':
            current = p.current_active_ma
        elif mode == 'sleep':
            current = p.current_sleep_ma
        else:
            current = p.current_deep_sleep_ua / 1000
        power_mw = p.voltage_v * current
        energy_mwh = power_mw * duration_s / 3600
        result = {'mode': mode, 'power_mw': power_mw, 'energy_mwh': energy_mwh, 'current_ma': current}
        self.measurements.append(result)
        return result

    def estimate_battery_life(self, profile_name, capacity_mah, duty_cycle_pct=100):
        p = self.profiles.get(profile_name)
        if not p:
            return 0
        avg_current = p.current_active_ma * duty_cycle_pct / 100 + p.current_sleep_ma * (100 - duty_cycle_pct) / 100
        if avg_current <= 0:
            return float('inf')
        return capacity_mah / avg_current
