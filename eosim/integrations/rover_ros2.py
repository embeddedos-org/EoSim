# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""ROS 2 topic contract for the EoSim planetary rover.

This module owns the topic contract; the bridge (``ros2.py``) stays
generic. A developer drives the simulated rover by publishing
``cmd_vel`` and reads ``odom`` — the same two topics a ROS 2 rover
stack uses — whether the bridge underneath is real rclpy or the
loopback test transport.

Topics (ROS conventions, not EoSim inventions):

- ``cmd_vel`` IN — ``geometry_msgs/msg/Twist`` on the rclpy path,
  plain dict on the loopback path:
  ``{"linear": {"x": float}, "angular": {"z": float}}``
  (metres/sec, radians/sec; only ``linear.x`` and ``angular.z``
  are honoured — differential-drive planar rover; other fields are
  ignored and documented as ignored, not silently honoured).
- ``odom`` OUT — ``nav_msgs/msg/Odometry`` on the rclpy path,
  plain dict on the loopback path:
  ``{"position": {"x", "y"}, "heading_deg", "speed_mps", "tick"}``
  built from ``RoverSimulator.get_state()`` + ``tick_count``.

Drive mechanics live in the simulator, not here:
``RoverSimulator.set_cmd_vel()`` stores the command and ``tick()``
applies it (same 10 ms factor as the position advance). An active
scenario refuses drive commands (``ValueError`` naming the
scenario); the adapter records that refusal in ``last_error``
instead of clearing the scenario behind the user's back, and
keeps the previous command.

No speed or turn-rate clamp is applied anywhere here: the motor
limits have no sourced value in this repo yet, so inventing one
would silently change the rover's behaviour. Limits belong in
the motor-controller model when it gains them.

Tracks: https://github.com/embeddedos-org/EoSim/issues/52
"""

import math

CMD_VEL_TOPIC = "cmd_vel"
CMD_VEL_TYPE = "geometry_msgs/msg/Twist"
ODOM_TOPIC = "odom"
ODOM_TYPE = "nav_msgs/msg/Odometry"


def rover_odometry(rover):
    """Loopback-shape odom payload from a rover's current state."""
    state = rover.get_state()
    return {
        "position": {"x": state["position_x"], "y": state["position_y"]},
        "heading_deg": state["heading_deg"],
        "speed_mps": state["speed_mps"],
        "tick": rover.tick_count,
    }


def rover_odometry_ros(rover, angular_z=0.0):
    """nav_msgs/Odometry-shaped payload from a rover's current state.

    The header stamp is SIM time (tick_count * 10 ms), not wall time:
    the rover's tick is the simulation clock. Orientation is the yaw
    quaternion for heading_deg; twist linear.x is the rover's speed.
    """
    state = rover.get_state()
    sim_time = rover.tick_count * 0.01
    yaw = math.radians(state["heading_deg"])
    half = yaw / 2.0
    return {
        "header": {
            "stamp": {"sec": int(sim_time), "nanosec": int((sim_time % 1) * 1e9)},
            "frame_id": "odom",
        },
        "pose": {
            "pose": {
                "position": {
                    "x": state["position_x"],
                    "y": state["position_y"],
                    "z": 0.0,
                },
                "orientation": {
                    "x": 0.0,
                    "y": 0.0,
                    "z": math.sin(half),
                    "w": math.cos(half),
                },
            }
        },
        "twist": {
            "twist": {
                "linear": {"x": state["speed_mps"], "y": 0.0, "z": 0.0},
                "angular": {"x": 0.0, "y": 0.0, "z": angular_z},
            }
        },
    }


class RoverTopicAdapter:
    """Binds a ROS2Bridge to a RoverSimulator over cmd_vel / odom."""

    def __init__(self, bridge, rover):
        self.bridge = bridge
        self.rover = rover
        self.last_error = None
        self._latest_angular_z = 0.0
        self.bridge.subscribe(CMD_VEL_TOPIC, CMD_VEL_TYPE, self._on_cmd_vel)

    def _on_cmd_vel(self, topic, msg_type, data):
        if not isinstance(data, dict):
            self.last_error = "cmd_vel payload must be a dict"
            return
        linear = data.get("linear", {})
        angular = data.get("angular", {})
        if not isinstance(linear, dict) or not isinstance(angular, dict):
            self.last_error = "cmd_vel linear/angular must be dicts"
            return
        try:
            linear_x = float(linear.get("x", 0.0))
            angular_z = float(angular.get("z", 0.0))
        except (TypeError, ValueError):
            # A malformed cmd_vel is ignored, not applied: the rover keeps
            # its previous command instead of stopping or swerving.
            self.last_error = "cmd_vel linear.x/angular.z must be numbers"
            return
        try:
            self.rover.set_cmd_vel(linear_x, angular_z)
        except ValueError as exc:
            # Scenario refusal (or any rover-side refusal) is surfaced
            # here, never swallowed: the previous command stands.
            self.last_error = str(exc)
            return
        self._latest_angular_z = angular_z
        self.last_error = None

    def publish_odometry(self):
        """Publish the rover's current state on odom. Returns the payload."""
        if self.bridge.transport == "rclpy":
            payload = rover_odometry_ros(self.rover, self._latest_angular_z)
        else:
            payload = rover_odometry(self.rover)
        self.bridge.publish(ODOM_TOPIC, ODOM_TYPE, payload)
        return payload
