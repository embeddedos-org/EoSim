# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""Worst-case execution time (WCET) analysis."""


class WCETAnalyzer:
    """Static WCET estimation for embedded tasks."""

    def __init__(self, clock_mhz=100):
        self.clock_mhz = clock_mhz
        self.tasks = {}

    def add_task(self, name, cycles, period_us=0, deadline_us=0):
        self.tasks[name] = {
            'cycles': cycles,
            'wcet_us': cycles / self.clock_mhz,
            'period_us': period_us or cycles / self.clock_mhz * 2,
            'deadline_us': deadline_us or cycles / self.clock_mhz * 2,
        }

    def utilization(self):
        total = 0
        for t in self.tasks.values():
            if t['period_us'] > 0:
                total += t['wcet_us'] / t['period_us']
        return total

    def schedulable(self):
        n = len(self.tasks)
        if n == 0:
            return True
        bound = n * (2 ** (1/n) - 1)
        return self.utilization() <= bound

    def report(self):
        return {
            'tasks': self.tasks,
            'utilization': self.utilization(),
            'schedulable': self.schedulable(),
            'clock_mhz': self.clock_mhz,
        }
