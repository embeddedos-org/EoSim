# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""AirSim drone/car simulator API bridge."""
import socket
import json


class AirSimConnection:
    """Bridge to AirSim via msgpack-rpc API."""

    def __init__(self, host='127.0.0.1', port=41451):
        self.host = host
        self.port = port
        self._connected = False
        self.vehicle_type = 'multirotor'

    def connect(self, timeout=5.0):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            s.connect((self.host, self.port))
            s.close()
            self._connected = True
        except OSError:
            self._connected = False
        return self._connected

    def disconnect(self):
        self._connected = False

    def arm(self):
        if not self._connected:
            raise RuntimeError("AirSimConnection.arm: not connected")
        raise NotImplementedError(
            "AirSimConnection.arm is not yet implemented \u2014 contributions welcome"
        )

    def takeoff(self, altitude_m=3.0):
        if not self._connected:
            raise RuntimeError("AirSimConnection.takeoff: not connected")
        raise NotImplementedError(
            "AirSimConnection.takeoff is not yet implemented \u2014 contributions welcome"
        )

    def move_to(self, x, y, z, velocity=5.0):
        if not self._connected:
            raise RuntimeError("AirSimConnection.move_to: not connected")
        raise NotImplementedError(
            "AirSimConnection.move_to is not yet implemented \u2014 contributions welcome"
        )

    def get_state(self):
        return {'connected': self._connected, 'vehicle': self.vehicle_type}

    def get_imu_data(self):
        return {'angular_velocity': [0,0,0], 'linear_acceleration': [0,0,9.81]}

    def get_gps_data(self):
        return {'latitude': 0, 'longitude': 0, 'altitude': 0}

    def land(self):
        if not self._connected:
            raise RuntimeError("AirSimConnection.land: not connected")
        raise NotImplementedError(
            "AirSimConnection.land is not yet implemented \u2014 contributions welcome"
        )
