# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""MATLAB Engine API bridge for Simulink co-simulation."""


class MATLABBridge:
    """Bridge to MATLAB via matlab.engine Python API."""

    def __init__(self):
        self._engine = None
        self._connected = False

    def connect(self, timeout=30.0):
        try:
            import matlab.engine
            self._engine = matlab.engine.start_matlab()
            self._connected = True
        except (ImportError, Exception):
            self._connected = False
        return self._connected

    def disconnect(self):
        if self._engine:
            try:
                self._engine.quit()
            except Exception:
                pass
        self._connected = False

    def eval(self, expression):
        if self._engine:
            return self._engine.eval(expression)
        return None

    def load_simulink_model(self, model_name):
        if self._engine:
            self._engine.load_system(model_name)

    def run_simulation(self, model_name, stop_time=10.0):
        if self._engine:
            self._engine.set_param(model_name, 'StopTime', str(stop_time))
            self._engine.sim(model_name)
