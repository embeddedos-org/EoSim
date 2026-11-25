# SPDX-License-Identifier: MIT
"""Tests for the EoSim ROS 2 bridge and the rover topic contract.

All tests run on the loopback transport: CI has no ROS installation,
and the rclpy path is skipped (not failed, not faked) when rclpy is
absent. The loopback bus is process-local, so each test disconnects
its bridges to avoid cross-test delivery.

Tracks: https://github.com/embeddedos-org/EoSim/issues/52
"""

import math

import pytest

from eosim.integrations.ros2 import ROS2Bridge
from eosim.integrations.rover_ros2 import (
    CMD_VEL_TOPIC,
    ODOM_TOPIC,
    RoverTopicAdapter,
    rover_odometry,
    rover_odometry_ros,
)

try:
    import rclpy  # noqa: F401

    HAS_RCLPY = True
except ImportError:
    HAS_RCLPY = False


@pytest.fixture
def bridge():
    b = ROS2Bridge("test_bridge")
    assert b.connect(transport="loopback") is True
    assert b.transport == "loopback"
    yield b
    b.disconnect()


@pytest.fixture
def rover():
    from eosim.engine.native.simulators.rover import RoverSimulator

    class _FakeVM:
        def __init__(self):
            self.peripherals = {}

        def add_peripheral(self, name, dev):
            self.peripherals[name] = dev

    r = RoverSimulator(_FakeVM())
    r.setup()
    return r


def test_bare_connect_without_rclpy_still_returns_false():
    """No silent behaviour change: bare connect() without rclpy is False."""
    if HAS_RCLPY:
        pytest.skip("rclpy is installed; bare-connect behaviour differs")
    b = ROS2Bridge("bare")
    assert b.connect() is False
    assert b.transport is None


def test_forced_rclpy_connect_fails_closed_without_rclpy():
    if HAS_RCLPY:
        pytest.skip("rclpy is installed; forced connect would succeed")
    b = ROS2Bridge("forced")
    assert b.connect(transport="rclpy") is False


@pytest.mark.skipif(not HAS_RCLPY, reason="rclpy not installed")
def test_rclpy_connect_creates_a_node():
    b = ROS2Bridge("real_node")
    assert b.connect(transport="rclpy") is True
    assert b.transport == "rclpy"
    b.disconnect()


def test_connect_rejects_unknown_transport():
    with pytest.raises(ValueError):
        ROS2Bridge("bad").connect(transport="socket")


def test_publish_before_connect_raises():
    b = ROS2Bridge("unconnected")
    with pytest.raises(RuntimeError, match="not connected"):
        b.publish("cmd_vel", "geometry_msgs/msg/Twist", {"linear": {"x": 1.0}})
    with pytest.raises(RuntimeError, match="not connected"):
        b.subscribe("cmd_vel", "geometry_msgs/msg/Twist", lambda *a: None)


def test_loopback_round_trip_in_order(bridge):
    received = []
    bridge.subscribe("chatter", "std_msgs/msg/String", lambda t, m, d: received.append(d))
    bridge.publish("chatter", "std_msgs/msg/String", {"data": "one"})
    bridge.publish("chatter", "std_msgs/msg/String", {"data": "two"})
    assert received == [{"data": "one"}, {"data": "two"}]


def test_publish_validates_inputs(bridge):
    with pytest.raises(ValueError):
        bridge.publish("", "std_msgs/msg/String", {"data": "x"})
    with pytest.raises(ValueError):
        bridge.publish("chatter", "", {"data": "x"})
    with pytest.raises(ValueError):
        bridge.publish("chatter", "std_msgs/msg/String", "not-a-dict")


def test_disconnect_clears_loopback_subscribers(bridge):
    received = []
    bridge.subscribe("chatter", "std_msgs/msg/String", lambda t, m, d: received.append(d))
    bridge.disconnect()
    other = ROS2Bridge("other")
    assert other.connect(transport="loopback") is True
    try:
        other.publish("chatter", "std_msgs/msg/String", {"data": "late"})
    finally:
        other.disconnect()
    assert received == []


def test_unsubscribe_stops_delivery(bridge):
    received = []
    cb = lambda t, m, d: received.append(d)  # noqa: E731
    bridge.subscribe("chatter", "std_msgs/msg/String", cb)
    bridge.publish("chatter", "std_msgs/msg/String", {"data": "one"})
    bridge.unsubscribe("chatter", cb)
    bridge.publish("chatter", "std_msgs/msg/String", {"data": "two"})
    assert received == [{"data": "one"}]


def test_cmd_vel_moves_rover_forward(bridge, rover):
    adapter = RoverTopicAdapter(bridge, rover)
    bridge.publish(
        CMD_VEL_TOPIC,
        "geometry_msgs/msg/Twist",
        {"linear": {"x": 0.5}, "angular": {"z": 0.0}},
    )
    rover.tick()
    rover.tick()
    assert rover.state["speed_mps"] == 0.5
    assert rover.state["heading_deg"] == 0
    assert rover.state["position_x"] == pytest.approx(0.5 * 0.01 * 2)
    assert rover.state["position_y"] == pytest.approx(0.0)
    assert adapter.last_error is None


def test_cmd_vel_turns_rover(bridge, rover):
    RoverTopicAdapter(bridge, rover)
    bridge.publish(
        CMD_VEL_TOPIC,
        "geometry_msgs/msg/Twist",
        {"linear": {"x": 0.0}, "angular": {"z": 1.0}},
    )
    rover.tick()
    assert rover.state["heading_deg"] == pytest.approx(math.degrees(1.0) * 0.01)


def test_odometry_matches_state_after_driven_ticks(bridge, rover):
    adapter = RoverTopicAdapter(bridge, rover)
    bridge.publish(
        CMD_VEL_TOPIC,
        "geometry_msgs/msg/Twist",
        {"linear": {"x": 0.5}, "angular": {"z": 0.0}},
    )
    rover.tick()
    rover.tick()
    seen = []
    bridge.subscribe(ODOM_TOPIC, "nav_msgs/msg/Odometry", lambda t, m, d: seen.append(d))
    payload = adapter.publish_odometry()
    assert seen == [payload]
    assert payload == rover_odometry(rover)
    assert payload["position"]["x"] == pytest.approx(rover.state["position_x"])
    assert payload["heading_deg"] == rover.state["heading_deg"]
    assert payload["speed_mps"] == 0.5
    assert payload["tick"] == rover.tick_count == 2


def test_rover_odometry_ros_shape(rover):
    payload = rover_odometry_ros(rover, angular_z=0.25)
    assert payload["header"]["frame_id"] == "odom"
    assert payload["pose"]["pose"]["position"] == {"x": 0.0, "y": 0.0, "z": 0.0}
    assert payload["twist"]["twist"]["linear"]["x"] == 0
    assert payload["twist"]["twist"]["angular"]["z"] == 0.25


def test_set_cmd_vel_refused_under_scenario(rover):
    rover.load_scenario("traverse")
    with pytest.raises(ValueError, match="traverse"):
        rover.set_cmd_vel(0.5, 0.0)
    rover.reset()
    rover.setup()
    rover.set_cmd_vel(0.5, 0.0)
    rover.tick()
    assert rover.state["speed_mps"] == 0.5


def test_adapter_surfaces_scenario_refusal(bridge, rover):
    adapter = RoverTopicAdapter(bridge, rover)
    rover.load_scenario("traverse")
    bridge.publish(
        CMD_VEL_TOPIC,
        "geometry_msgs/msg/Twist",
        {"linear": {"x": 0.5}, "angular": {"z": 0.0}},
    )
    assert adapter.last_error is not None
    assert "traverse" in adapter.last_error
    rover.tick()
    assert rover.state["speed_mps"] == 0.04  # scenario owns speed, not cmd_vel


def test_adapter_ignores_malformed_cmd_vel(bridge, rover):
    adapter = RoverTopicAdapter(bridge, rover)
    bridge.publish(
        CMD_VEL_TOPIC,
        "geometry_msgs/msg/Twist",
        {"linear": {"x": "fast"}, "angular": {"z": 0.0}},
    )
    rover.tick()
    assert rover.state["speed_mps"] == 0
    assert adapter.last_error is not None
