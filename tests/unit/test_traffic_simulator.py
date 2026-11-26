# SPDX-License-Identifier: MIT
"""Traffic controller safety invariant and scenario regression tests.

Covers issues #106 (scenarios that never changed anything) and #107
(conflicting greens under emergency override, and a cycle with no east-west
yellow or all-red clearance).
"""

import random

import pytest

from eosim.engine.native.simulators.traffic import (
    GO_ASPECTS,
    PHASE_SIGNALS,
    TrafficSimulator,
)


class FakeVM:
    def __init__(self):
        self.peripherals = {}

    def add_peripheral(self, name, dev):
        self.peripherals[name] = dev


def make_sim(scenario=None):
    sim = TrafficSimulator(FakeVM())
    sim.setup()
    if scenario:
        sim.load_scenario(scenario)
    return sim


def assert_safe(state, context):
    """The invariant: no two conflicting approaches authorised at once."""
    signals = state["signals"]
    conflicts = TrafficSimulator.conflicting_greens(signals)
    assert conflicts == [], (
        f"conflicting greens {conflicts} in phase {state['phase']!r} ({context}); signals={signals}"
    )
    assert state["phase"] != "green_all", (
        f"phase 'green_all' published ({context}): green on every approach at once"
    )


# ─── the declared state space ──────────────────────────────────────────


def test_no_declared_phase_has_conflicting_greens():
    """Exhaustive over every phase the controller can publish."""
    assert PHASE_SIGNALS, "phase table is empty"
    for phase, signals in PHASE_SIGNALS.items():
        conflicts = TrafficSimulator.conflicting_greens(signals)
        assert conflicts == [], f"phase {phase!r} authorises conflicting {conflicts}"


def test_phase_table_has_no_all_green_phase():
    """#107: 'green_all' gave every approach green at once. It must not exist."""
    assert "green_all" not in PHASE_SIGNALS
    for phase, signals in PHASE_SIGNALS.items():
        going = [a for a in TrafficSimulator.VEHICLE_APPROACHES if signals[a] in GO_ASPECTS]
        assert len(going) <= 2, f"phase {phase!r} releases {going}"


def test_conflicting_greens_detects_an_unsafe_map():
    """The checker itself must be able to fail."""
    unsafe = {
        "north": "green",
        "south": "green",
        "east": "green",
        "west": "green",
        "pedestrian": "walk",
    }
    assert TrafficSimulator.conflicting_greens(unsafe) != []


# ─── every scenario, every tick ────────────────────────────────────────

ALL_SCENARIOS = sorted(TrafficSimulator.SCENARIOS)


@pytest.mark.parametrize("scenario", ALL_SCENARIOS)
def test_invariant_holds_for_every_tick_of_every_scenario(scenario):
    """#107: run each scenario and check the invariant on every published state."""
    sim = make_sim(scenario)
    for i in range(300):
        sim.tick()
        assert_safe(sim.get_state(), f"scenario={scenario} tick={i + 1}")


def test_invariant_holds_with_no_scenario_loaded():
    sim = make_sim()
    for i in range(300):
        sim.tick()
        assert_safe(sim.get_state(), f"free-running tick={i + 1}")


def test_invariant_holds_under_randomised_input_fuzz():
    """Drive the controller through arbitrary input combinations."""
    rng = random.Random(20261125)
    sim = make_sim()
    for i in range(4000):
        roll = rng.random()
        if roll < 0.02:
            sim.request_emergency(rng.choice(["ns", "ew"]))
        elif roll < 0.04:
            sim.clear_emergency()
        elif roll < 0.06:
            sim.request_pedestrian()
        elif roll < 0.07:
            sim.state["fault_active"] = True
        elif roll < 0.08:
            sim.state["fault_active"] = False
        sim.tick()
        assert_safe(sim.get_state(), f"fuzz tick={i + 1}")


def _drive(sim, ticks):
    seen = []
    for _ in range(ticks):
        sim.tick()
        state = sim.get_state()
        assert_safe(state, "reachability sweep")
        seen.append(state["phase"])
    return seen


def test_sweep_reaches_every_phase_and_stays_safe():
    """Every declared phase is actually reachable, and safe when reached.

    Without this the invariant tests above could pass by never visiting the
    interesting states.
    """
    seen = set()

    # Normal cycle: both greens, both yellows, both all-reds.
    seen.update(_drive(make_sim(), 200))

    # Pedestrian interlude.
    sim = make_sim()
    sim.request_pedestrian()
    seen.update(_drive(sim, 60))

    # Pre-emption for each ring, requested while the conflicting ring is green.
    for ring in ("ns", "ew"):
        sim = make_sim()
        # Park the controller on the ring that conflicts with the request.
        if ring == "ns":
            _drive(
                sim,
                sim.state["green_time_s"]
                + sim.state["yellow_time_s"]
                + sim.state["all_red_time_s"]
                + 1,
            )
        sim.request_emergency(ring)
        seen.update(_drive(sim, 40))
        sim.clear_emergency()
        seen.update(_drive(sim, 40))

    # Controller fault, then recovery.
    sim = make_sim("fault_mode")
    seen.update(_drive(sim, 20))
    sim.scenario = ""
    sim.state["fault_active"] = False
    seen.update(_drive(sim, 40))

    missing = set(PHASE_SIGNALS) - seen
    assert missing == set(), f"phases never reached by the sweep: {sorted(missing)}"


# ─── issue #107: emergency pre-emption ─────────────────────────────────


def test_emergency_override_gives_green_to_exactly_one_ring():
    sim = make_sim("emergency_vehicle")
    greens_seen = set()
    saw_emergency_green = False
    for i in range(30):
        sim.tick()
        state = sim.get_state()
        assert_safe(state, f"emergency tick={i + 1}")
        if state["phase"].startswith("emergency_"):
            saw_emergency_green = True
            released = [
                a for a in TrafficSimulator.VEHICLE_APPROACHES if state["signals"][a] in GO_ASPECTS
            ]
            assert released == ["north", "south"], (
                f"emergency released {released}, expected exactly the authorised ring"
            )
            held = [a for a in ("east", "west") if state["signals"][a] != "red"]
            assert held == [], f"conflicting approaches not at red: {held}"
            assert state["signals"]["pedestrian"] == "dont_walk"
            greens_seen.add(state["phase"])
    assert saw_emergency_green, "emergency override never produced a green"
    assert greens_seen == {"emergency_ns"}


def test_emergency_clears_conflicting_green_through_yellow_then_all_red():
    """Pre-emption must not drop a running green straight to red."""
    sim = make_sim()
    # Advance into the east-west green.
    target = sim.state["green_time_s"] + sim.state["yellow_time_s"] + sim.state["all_red_time_s"]
    for _ in range(target + 1):
        sim.tick()
    assert sim.get_state()["phase"] == "green_ew"

    sim.request_emergency("ns")
    phases = []
    for _ in range(sim.state["yellow_time_s"] + sim.state["all_red_time_s"] + 2):
        sim.tick()
        state = sim.get_state()
        assert_safe(state, "pre-emption clearance")
        phases.append(state["phase"])

    yellow_run = [p for p in phases if p == "yellow_ew"]
    assert len(yellow_run) == sim.state["yellow_time_s"], phases
    assert (
        phases[len(yellow_run) : len(yellow_run) + sim.state["all_red_time_s"]]
        == ["all_red"] * sim.state["all_red_time_s"]
    ), phases
    assert phases[-1] == "emergency_ns", phases


def test_emergency_for_east_west_releases_only_east_west():
    sim = make_sim()
    sim.request_emergency("ew")
    for _ in range(30):
        sim.tick()
        assert_safe(sim.get_state(), "ew pre-emption")
    state = sim.get_state()
    assert state["phase"] == "emergency_ew"
    assert state["signals"]["east"] == "green"
    assert state["signals"]["west"] == "green"
    assert state["signals"]["north"] == "red"
    assert state["signals"]["south"] == "red"


def test_request_emergency_rejects_unknown_ring():
    sim = make_sim()
    assert sim.request_emergency("up") is False
    assert sim.state["emergency_override"] is False
    assert sim.request_emergency("ew") is True


# ─── issue #107: the cycle itself ──────────────────────────────────────


def test_cycle_has_east_west_yellow_and_all_red_clearance():
    sim = make_sim()
    phases = _drive(sim, 200)
    assert "yellow_ew" in phases, "east-west still goes from green straight to red"
    assert "all_red" in phases, "no all-red clearance between conflicting greens"
    assert "yellow_ns" in phases
    assert {"green_ns", "green_ew"} <= set(phases)


def test_every_green_is_followed_by_yellow_then_all_red():
    """No conflicting green is released without a clearance between them."""
    sim = make_sim()
    phases = _drive(sim, 400)
    ring_of = {"green_ns": "ns", "green_ew": "ew"}
    last_green = None
    for index, phase in enumerate(phases):
        if phase in ring_of:
            if last_green is not None and ring_of[phase] != last_green[0]:
                between = phases[last_green[1] + 1 : index]
                assert "all_red" in between or "ped_clear" in between, (
                    f"no all-red between {last_green[0]} green and {phase}: {between}"
                )
                expected_yellow = "yellow_" + last_green[0]
                assert expected_yellow in between, f"no {expected_yellow} before {phase}: {between}"
            last_green = (ring_of[phase], index)


def test_cycle_count_advances():
    sim = make_sim()
    _drive(sim, 300)
    assert sim.get_state()["cycle_count"] >= 2


# ─── issue #106: scenarios that never changed anything ─────────────────


def test_fault_mode_reaches_the_flashing_fail_safe_state():
    """#106: fault_mode reported a normal green/yellow cycle."""
    sim = make_sim("fault_mode")
    phases = _drive(sim, 40)
    assert set(phases) == {"flash_yellow"}, (
        f"fault_mode did not hold the fail-safe state: {sorted(set(phases))}"
    )
    signals = sim.get_state()["signals"]
    assert signals["north"] == "flashing_yellow"
    assert signals["east"] == "flashing_red"
    assert TrafficSimulator.conflicting_greens(signals) == []


def test_fault_mode_differs_from_the_normal_cycle():
    fault = _drive(make_sim("fault_mode"), 60)
    normal = _drive(make_sim("normal_cycle"), 60)
    assert fault != normal, "fault_mode produced the normal cycle output"


def test_pedestrian_crossing_reaches_the_walk_phase():
    """#106: pedestrian_crossing never published ped_walk."""
    sim = make_sim("pedestrian_crossing")
    phases = _drive(sim, 60)
    assert "ped_walk" in phases, f"ped_walk never published: {sorted(set(phases))}"
    assert "ped_clear" in phases, "walk ended without a clearance interval"
    walk_index = phases.index("ped_walk")
    assert "yellow_ns" in phases[:walk_index], (
        "the green was dropped without a yellow before the walk"
    )


def test_pedestrian_walk_holds_every_vehicle_approach_at_red():
    sim = make_sim("pedestrian_crossing")
    saw_walk = False
    for _ in range(60):
        sim.tick()
        state = sim.get_state()
        assert_safe(state, "pedestrian crossing")
        if state["phase"] == "ped_walk":
            saw_walk = True
            for approach in TrafficSimulator.VEHICLE_APPROACHES:
                assert state["signals"][approach] == "red"
            assert state["signals"]["pedestrian"] == "walk"
    assert saw_walk


def test_pedestrian_waiting_clears_once_the_walk_is_served():
    sim = make_sim("pedestrian_crossing")
    sim.tick()
    assert sim.get_state()["pedestrian_waiting"] is True
    for _ in range(60):
        sim.tick()
        if sim.get_state()["phase"] == "ped_walk":
            break
    assert sim.get_state()["pedestrian_waiting"] is False


def test_pedestrian_crossing_differs_from_the_normal_cycle():
    ped = _drive(make_sim("pedestrian_crossing"), 60)
    normal = _drive(make_sim("normal_cycle"), 60)
    assert ped != normal, "pedestrian_crossing produced the normal cycle output"


def test_rush_hour_actually_raises_traffic_volume():
    """The same overwrite bug silently discarded rush_hour's volume."""
    sim = make_sim("rush_hour")
    volumes = []
    for _ in range(60):
        sim.tick()
        volumes.append(sim.get_state()["vehicles_per_min"])
    mean = sum(volumes) / len(volumes)
    assert mean > 30, f"rush_hour volume was overwritten by the default: mean {mean}"
    assert sim.get_state()["green_time_s"] == 45


def test_normal_cycle_volume_stays_near_the_default():
    sim = make_sim("normal_cycle")
    volumes = []
    for _ in range(60):
        sim.tick()
        volumes.append(sim.get_state()["vehicles_per_min"])
    assert 10 < sum(volumes) / len(volumes) < 30


@pytest.mark.parametrize("scenario", sorted(set(ALL_SCENARIOS) - {"normal_cycle"}))
def test_every_scenario_changes_something_observable(scenario):
    """#106: a scenario that produces the no-scenario output is dead code."""
    baseline_phases = _drive(make_sim(), 60)

    sim = make_sim(scenario)
    phases = []
    volumes = []
    for _ in range(60):
        sim.tick()
        state = sim.get_state()
        phases.append(state["phase"])
        volumes.append(state["vehicles_per_min"])

    changed_phase = phases != baseline_phases
    changed_volume = sum(volumes) / len(volumes) > 30
    assert changed_phase or changed_volume, (
        f"{scenario} produced output identical to no scenario loaded"
    )


def test_normal_cycle_matches_the_free_running_controller():
    assert _drive(make_sim("normal_cycle"), 60) == _drive(make_sim(), 60)


# ─── state contract ────────────────────────────────────────────────────


def test_state_exposes_a_signal_per_approach():
    sim = make_sim()
    sim.tick()
    signals = sim.get_state()["signals"]
    for approach in TrafficSimulator.VEHICLE_APPROACHES:
        assert approach in signals
    assert TrafficSimulator.PEDESTRIAN in signals


def test_get_state_returns_a_detached_copy():
    sim = make_sim()
    sim.tick()
    snapshot = sim.get_state()
    snapshot["signals"]["north"] = "tampered"
    assert sim.get_state()["signals"]["north"] != "tampered"


def test_reset_restores_the_controller():
    sim = make_sim("fault_mode")
    _drive(sim, 20)
    sim.reset()
    assert sim.tick_count == 0
    assert sim.scenario == ""
    sim.setup()
    assert sim.get_state()["phase"] == "green_ns"
    assert sim.get_state()["fault_active"] is False
    phases = _drive(sim, 60)
    assert "flash_yellow" not in phases


def test_clear_emergency_recovers_through_a_clearance():
    sim = make_sim()
    sim.request_emergency("ew")
    _drive(sim, 20)
    assert sim.get_state()["phase"] == "emergency_ew"
    sim.clear_emergency()
    phases = _drive(sim, 20)
    assert phases[0] == "yellow_ew", phases
    assert "all_red" in phases
    assert "green_ns" in phases


# ─── scenario-owned inputs are handed back (CodeRabbit, PR #112) ───────
# A scenario drives controller inputs and nothing used to give them up, so
# the inputs of a scenario that was no longer loaded kept steering the
# controller. Each case below was observed failing before the fix.


def test_leaving_fault_mode_stops_flashing():
    """One tick of fault_mode used to latch flash_yellow forever."""
    sim = make_sim("fault_mode")
    sim.tick()
    assert sim.get_state()["phase"] == "flash_yellow"
    sim.load_scenario("normal_cycle")
    phases = _drive(sim, 30)
    assert "flash_yellow" not in phases, phases
    assert sim.get_state()["fault_active"] is False


def test_leaving_emergency_scenario_early_releases_preemption():
    """emergency_vehicle clears its request at step 20; leaving before that
    used to strand emergency_override and hold pre-emption indefinitely."""
    sim = make_sim("emergency_vehicle")
    _drive(sim, 5)
    assert sim.get_state()["emergency_override"] is True
    sim.load_scenario("normal_cycle")
    phases = _drive(sim, 40)
    assert sim.get_state()["emergency_override"] is False
    assert "emergency_ns" not in phases, phases
    assert "green_ns" in phases


def test_leaving_rush_hour_restores_the_configured_green():
    sim = make_sim("rush_hour")
    sim.tick()
    assert sim.get_state()["green_time_s"] == 45
    sim.load_scenario("normal_cycle")
    sim.tick()
    assert sim.get_state()["green_time_s"] == 30


def test_scenario_change_keeps_inputs_a_caller_set_independently():
    """Only keys the scenario actually wrote are handed back."""
    sim = make_sim()
    sim.request_emergency("ew")
    sim.load_scenario("fault_mode")
    sim.tick()
    sim.load_scenario("normal_cycle")
    # fault_mode never wrote emergency_override, so the caller's request stands.
    assert sim.get_state()["emergency_override"] is True
    assert sim.get_state()["emergency_approach"] == "ew"


# ─── clearance intervals are never skipped or shortened ────────────────


def test_changing_the_emergency_target_clears_the_authorised_ring_first():
    """Re-targeting pre-emption used to put the new ring straight to green
    while the old one dropped from green to red with no clearance."""
    sim = make_sim()
    sim.request_emergency("ew")
    _drive(sim, 12)
    assert sim.get_state()["phase"] == "emergency_ew"
    sim.request_emergency("ns")
    phases = _drive(sim, 12)
    assert phases[0] == "yellow_ew", phases
    assert phases.index("all_red") < phases.index("emergency_ns"), phases
    assert phases.count("yellow_ew") == sim.get_state()["yellow_time_s"], phases


def test_repeating_the_same_emergency_request_preserves_progress():
    sim = make_sim()
    sim.request_emergency("ew")
    _drive(sim, 2)
    stage_before = sim._emergency_stage
    tick_before = sim._emergency_stage_tick
    sim.request_emergency("ew")
    sim.tick()
    assert sim._emergency_stage == stage_before
    assert sim._emergency_stage_tick == tick_before + 1


def test_preemption_during_a_normal_yellow_finishes_that_yellow():
    """Pre-emption used to jump to all-red, cutting the running yellow short."""
    sim = make_sim()
    while sim.get_state()["phase"] != "yellow_ns":
        sim.tick()
    served = sim._cycle_tick
    yellow = sim.get_state()["yellow_time_s"]
    sim.request_emergency("ew")
    phases = _drive(sim, 12)
    assert phases.count("yellow_ns") == yellow - served, phases
    assert "all_red" in phases
    assert phases.index("all_red") < phases.index("emergency_ew"), phases


def test_cancelling_preemption_during_its_yellow_finishes_that_yellow():
    """Clearing the request mid-clearance used to drop the rest of the yellow."""
    sim = make_sim()
    while sim.get_state()["phase"] != "green_ns":
        sim.tick()
    sim.tick()
    sim.request_emergency("ew")
    sim.tick()
    assert sim.get_state()["phase"] == "yellow_ns"
    yellow = sim.get_state()["yellow_time_s"]
    sim.clear_emergency()
    phases = _drive(sim, 12)
    assert phases.count("yellow_ns") == yellow - 1, phases
    assert "all_red" in phases
    assert phases.index("all_red") < phases.index("green_ns"), phases


def test_scenario_churn_never_authorises_conflicting_approaches():
    """Fuzz the scenario switching itself, which is what the leaks broke."""
    rng = random.Random(20261126)
    names = list(TrafficSimulator.SCENARIOS) + ["normal_cycle"]
    sim = make_sim()
    for _ in range(400):
        if rng.random() < 0.15:
            sim.load_scenario(rng.choice(names))
        if rng.random() < 0.08:
            sim.request_emergency(rng.choice(["ns", "ew"]))
        if rng.random() < 0.08:
            sim.clear_emergency()
        if rng.random() < 0.08:
            sim.request_pedestrian()
        sim.tick()
        assert_safe(sim.get_state(), "scenario churn fuzz")
