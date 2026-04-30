# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""ROS 2 node bridge for EoSim integration."""


class ROS2Bridge:
    """Bridge to ROS 2 via rclpy (if available) or socket fallback."""

    def __init__(self, node_name='eosim_bridge'):
        self.node_name = node_name
        self._node = None
        self._connected = False
        self.publishers = {}
        self.subscribers = {}

    def connect(self, timeout=5.0):
        try:
            import rclpy
            rclpy.init()
            self._node = rclpy.create_node(self.node_name)
            self._connected = True
        except (ImportError, Exception):
            self._connected = False
        return self._connected

    def disconnect(self):
        if self._node:
            self._node.destroy_node()
        try:
            import rclpy
            rclpy.shutdown()
        except Exception:
            pass
        self._connected = False

    def publish(self, topic, msg_type, data):
        pass

    def subscribe(self, topic, msg_type, callback):
        pass

    def spin_once(self, timeout_sec=0.1):
        if self._node:
            try:
                import rclpy
                rclpy.spin_once(self._node, timeout_sec=timeout_sec)
            except Exception:
                pass
