# SPDX-License-Identifier: MIT
"""Return-to-launch in the drone simulator."""

import random

import pytest

from eosim.engine.native.simulators.drone import DroneSimulator

SEEDS = range(20)


class FakeVM:
    def __init__(self):
        self.peripherals = {}

    def add_peripheral(self, name, dev):
        self.peripherals[name] = dev


def make_sim(seed):
    random.seed(seed)
    s = DroneSimulator(FakeVM())
    s.setup()
    return s


def run_until_disarmed(sim, ticks=1000):
    for _ in range(ticks):
        sim.tick()
        if sim.state["flight_mode"] == "DISARMED":
            break


@pytest.mark.parametrize("seed", SEEDS)
def test_rtl_over_home_lands_and_disarms(seed):
    # 15 m above the launch point, then return-to-launch. GPS noise
    # moves the position a little each tick; the landing must still end.
    sim = make_sim(seed)
    sim.state["altitude_m"] = 15.0
    sim.set_flight_mode("RTL")
    run_until_disarmed(sim)
    assert sim.state["flight_mode"] == "DISARMED"
    assert sim.state["altitude_m"] < 0.1
    assert sim.vm.peripherals["esc0"].armed is False


@pytest.mark.parametrize("seed", SEEDS)
def test_low_battery_rtl_over_home_ends_disarmed(seed):
    sim = make_sim(seed)
    sim.load_scenario("hover")
    sim.set_flight_mode("LOITER")
    sim.state["altitude_m"] = 10.0
    sim.load_scenario("low_battery_rtl")
    sim.vm.peripherals["bms0"].soc_percent = 10
    run_until_disarmed(sim)
    assert sim.state["flight_mode"] == "DISARMED"
    assert sim.state["altitude_m"] < 0.1


def test_rtl_away_from_home_flies_home_at_20_m():
    sim = make_sim(1)
    gps = sim.vm.peripherals["gps0"]
    gps.latitude += 0.001  # about 111 m north of home
    sim.set_flight_mode("RTL")
    for _ in range(20):
        sim.tick()
    assert sim.state["flight_mode"] == "RTL"
    assert sim._target_alt >= 20
    assert gps.heading_deg == pytest.approx(180, abs=1)


def test_leaving_rtl_clears_the_landing():
    sim = make_sim(1)
    sim.state["altitude_m"] = 15.0
    sim.set_flight_mode("RTL")
    sim.tick()
    assert sim._rtl_landing is True
    sim.set_flight_mode("LOITER")
    assert sim._rtl_landing is False
