# SPDX-License-Identifier: MIT
"""Scenario state in the wearable simulator."""

import pytest

from eosim.engine.native.simulators.wearable import WearableSimulator


class FakeVM:
    def __init__(self):
        self.peripherals = {}

    def add_peripheral(self, name, dev):
        self.peripherals[name] = dev


@pytest.fixture
def sim():
    s = WearableSimulator(FakeVM())
    s.setup()
    return s


def test_workout_detection_marks_a_running_workout(sim):
    sim.load_scenario("workout_detection")
    state = sim.get_state()
    assert state["workout_active"] is True
    assert state["workout_type"] == "running"
    # The scenario still starts the IMU the way step counting does.
    assert sim.vm.peripherals["imu0"].accel == [0, 0, 12.0]
    for _ in range(5):
        sim.tick()
    assert sim.get_state()["workout_active"] is True


def test_step_counting_is_not_a_workout(sim):
    sim.load_scenario("step_counting")
    state = sim.get_state()
    assert state["workout_active"] is False
    assert state["workout_type"] == ""
    assert sim.vm.peripherals["imu0"].accel == [0, 0, 12.0]
