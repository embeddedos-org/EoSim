# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""Verilator VCD/FST trace reader for RTL co-simulation."""
import os


class VerilatorBridge:
    """Read Verilator VCD/FST waveform traces."""

    def __init__(self):
        self.signals = {}
        self.time_unit = 'ns'
        self.loaded = False

    def load_vcd(self, path):
        if not os.path.exists(path):
            return False
        self.signals = {}
        try:
            with open(path, 'r') as f:
                for line in f:
                    if line.startswith('$var'):
                        parts = line.split()
                        if len(parts) >= 5:
                            self.signals[parts[4]] = {'type': parts[1], 'width': int(parts[2])}
            self.loaded = True
        except Exception:
            self.loaded = False
        return self.loaded

    def get_signal(self, name):
        return self.signals.get(name)

    def list_signals(self):
        return list(self.signals.keys())
