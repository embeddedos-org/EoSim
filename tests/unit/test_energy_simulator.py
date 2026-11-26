# SPDX-License-Identifier: MIT
"""Battery direction in the energy simulator's charge_discharge scenario."""

import random

import pytest

from eosim.engine.native.simulators.energy import EnergySimulator


class FakeVM:
    def __init__(self):
        self.peripherals = {}

    def add_peripheral(self, name, dev):
        self.peripherals[name] = dev


@pytest.fixture
def sim():
    random.seed(1)
    s = EnergySimulator(FakeVM())
    s.setup()
    return s


def test_charge_half_of_the_cycle_charges_at_night(sim):
    # tick_count 0..99 is simulated midnight to 1 am: no solar, so the
    # load alone would discharge the battery. The scenario's first 200
    # steps are the charge half of its cycle.
    sim.load_scenario("charge_discharge")
    bms = sim.vm.peripherals["bms0"]
    soc_start = bms.soc_percent
    for _ in range(50):
        sim.tick()
    assert bms.charging is True
    assert bms.soc_percent > soc_start


def test_discharge_half_of_the_cycle_discharges_at_noon(sim):
    # Around simulated noon the panel covers the load, so the surplus
    # alone would charge the battery. Steps 200..399 are the discharge
    # half of the cycle.
    sim.tick_count = 1000
    sim.load_scenario("charge_discharge")
    sim._scenario_step = 250
    bms = sim.vm.peripherals["bms0"]
    for _ in range(50):
        sim.tick()
    assert bms.charging is False


def test_without_the_scenario_the_solar_surplus_decides(sim):
    bms = sim.vm.peripherals["bms0"]
    for _ in range(10):
        sim.tick()
    assert bms.charging is False  # night: load > solar
    sim.tick_count = 1100
    for _ in range(10):
        sim.tick()
    assert bms.charging is True  # noon: solar > load
