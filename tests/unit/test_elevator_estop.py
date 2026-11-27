# SPDX-License-Identifier: MIT
"""Regression test: emergency_stop must keep the elevator stationary."""
import pytest
from eosim.engine.native.simulators.elevator import ElevatorSimulator


class FakeVM:
    def __init__(self):
        self.peripherals = {}
    def add_peripheral(self, name, dev):
        self.peripherals[name] = dev


def test_emergency_stop_prevents_movement():
    """An elevator mid-travel must stay put after emergency_stop."""
    vm = FakeVM()
    sim = ElevatorSimulator(vm)
    sim.setup()

    # Place the elevator on floor 1 with a target of floor 10
    sim.state["current_floor"] = 1
    sim.state["target_floor"] = 10
    sim.state["door_state"] = "closed"

    # Activate emergency stop
    sim.load_scenario("emergency_stop")

    # Run several ticks — the elevator must not move
    for _ in range(20):
        sim.tick()

    assert sim.state["current_floor"] == 1, (
        f"Elevator moved to floor {sim.state['current_floor']} during emergency stop"
    )
    assert sim.state["speed_mps"] == 0, (
        f"Speed is {sim.state['speed_mps']} during emergency stop"
    )
    assert sim.state["direction"] == "idle", (
        f"Direction is {sim.state['direction']} during emergency stop"
    )
