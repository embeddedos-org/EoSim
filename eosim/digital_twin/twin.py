# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""Digital twin engine for real-time hardware mirroring."""
import time
import json


class DigitalTwin:
    """Digital twin that mirrors a physical device's state."""

    def __init__(self, name, simulator):
        self.name = name
        self.simulator = simulator
        self.history = []
        self.sync_interval_s = 1.0
        self._last_sync = 0
        self.connected = False

    def sync(self):
        state = self.simulator.get_state()
        state['timestamp'] = time.time()
        self.history.append(state)
        if len(self.history) > 10000:
            self.history = self.history[-5000:]
        self._last_sync = time.time()
        return state

    def get_history(self, last_n=100):
        return self.history[-last_n:]

    def predict(self, steps=10):
        states = []
        for _ in range(steps):
            self.simulator.tick()
            states.append(self.simulator.get_state())
        return states

    def export_json(self, path):
        with open(path, 'w') as f:
            json.dump({'name': self.name, 'history': self.history[-1000:]}, f, indent=2)

    def status(self):
        return {
            'name': self.name,
            'connected': self.connected,
            'history_length': len(self.history),
            'last_sync': self._last_sync,
        }
