# SPDX-License-Identifier: MIT
"""Alarm selection in the medical patient-monitor simulator."""

import pytest

from eosim.engine.native.simulators.medical import MedicalSimulator


class FakeVM:
    def __init__(self):
        self.peripherals = {}

    def add_peripheral(self, name, dev):
        self.peripherals[name] = dev


@pytest.fixture
def sim():
    s = MedicalSimulator(FakeVM())
    s.setup()
    return s


def _alarm(sim, occluded=False, **state):
    sim.state.update(state)
    sim.vm.peripherals["pump0"].occlusion = occluded
    sim._evaluate_alarms()
    return sim.state["alarm"], sim.state["alarm_priority"]


def test_critical_spo2_is_not_hidden_by_abnormal_heart_rate(sim):
    assert _alarm(sim, heart_rate=130, spo2=80) == ("SPO2_CRITICAL", 3)


def test_pump_occlusion_is_not_hidden_by_sensor_disconnect(sim):
    assert _alarm(sim, occluded=True, sensor_connected=False) == ("PUMP_OCCLUSION", 3)


@pytest.mark.parametrize(
    "state, occluded, expected",
    [
        ({}, False, ("NONE", 0)),
        ({"heart_rate": 30}, False, ("HR_CRITICAL", 3)),
        ({"heart_rate": 130, "spo2": 88}, False, ("HR_ABNORMAL", 2)),
        ({"spo2": 88}, False, ("LOW_SPO2", 2)),
        ({"temperature": 39.2}, False, ("TEMP_WARNING", 1)),
        ({"heart_rate": 130, "temperature": 40.0}, False, ("HR_ABNORMAL", 2)),
        ({"sensor_connected": False, "heart_rate": 0, "spo2": 0}, False, ("SENSOR_DISCONNECT", 2)),
        ({"sensor_connected": False, "temperature": 40.0}, False, ("SENSOR_DISCONNECT", 2)),
        ({"heart_rate": 30}, True, ("PUMP_OCCLUSION", 3)),
    ],
)
def test_equal_priorities_keep_their_order(sim, state, occluded, expected):
    assert _alarm(sim, occluded=occluded, **state) == expected
