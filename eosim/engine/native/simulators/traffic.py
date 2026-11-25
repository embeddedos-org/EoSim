# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""Traffic control simulator.

Pure Python, cross-platform (Linux/Windows/macOS). No OS-specific dependencies.

The simulator publishes an explicit per-approach signal map alongside the phase
name, so a conflict monitor can be developed against it. The invariant it
maintains is the one a signal controller exists to guarantee: no two
conflicting approaches are ever authorised to move at the same time.
"""

import random

#: Aspects that authorise movement. Anything else holds traffic.
GO_ASPECTS = frozenset({"green", "walk"})

GREEN = "green"
YELLOW = "yellow"
RED = "red"
FLASHING_YELLOW = "flashing_yellow"
FLASHING_RED = "flashing_red"
WALK = "walk"
FLASHING_DONT_WALK = "flashing_dont_walk"
DONT_WALK = "dont_walk"


def _signals(ns_aspect, ew_aspect, ped_aspect=DONT_WALK):
    """Build a signal map from the per-ring aspects.

    Approaches inside a ring never conflict with each other, so both legs of a
    ring always show the same aspect.
    """
    return {
        "north": ns_aspect,
        "south": ns_aspect,
        "east": ew_aspect,
        "west": ew_aspect,
        "pedestrian": ped_aspect,
    }


#: The complete set of states the controller can publish. There is deliberately
#: no phase that shows green to both rings: that is the conflicting-green state
#: a signal controller exists to prevent, including under emergency
#: pre-emption, which gives green to exactly one authorised ring and holds
#: every conflicting approach at red.
PHASE_SIGNALS = {
    "green_ns": _signals(GREEN, RED),
    "yellow_ns": _signals(YELLOW, RED),
    "green_ew": _signals(RED, GREEN),
    "yellow_ew": _signals(RED, YELLOW),
    "all_red": _signals(RED, RED),
    "ped_walk": _signals(RED, RED, WALK),
    "ped_clear": _signals(RED, RED, FLASHING_DONT_WALK),
    "flash_yellow": _signals(FLASHING_YELLOW, FLASHING_RED),
    "emergency_ns": _signals(GREEN, RED),
    "emergency_ew": _signals(RED, GREEN),
}


class TrafficSimulator:
    PRODUCT_TYPE = "traffic"
    DISPLAY_NAME = "Traffic Control"
    SCENARIOS = {
        "normal_cycle": {"description": "Standard traffic light cycle"},
        "rush_hour": {"description": "Extended green for main road during rush hour"},
        "emergency_vehicle": {"description": "Emergency vehicle preemption"},
        "pedestrian_crossing": {"description": "Pedestrian push-button crossing request"},
        "fault_mode": {"description": "Flash yellow due to controller fault"},
    }

    #: Vehicle approaches grouped into the two non-conflicting rings of a
    #: standard four-leg intersection.
    RINGS = {"ns": ("north", "south"), "ew": ("east", "west")}
    VEHICLE_APPROACHES = ("north", "south", "east", "west")
    PEDESTRIAN = "pedestrian"

    #: One full cycle: every green is followed by a yellow and an all-red
    #: clearance before the conflicting ring is released.
    CYCLE_STEPS = (
        ("green_ns", "green_time_s"),
        ("yellow_ns", "yellow_time_s"),
        ("all_red", "all_red_time_s"),
        ("green_ew", "red_time_s"),
        ("yellow_ew", "yellow_time_s"),
        ("all_red", "all_red_time_s"),
    )

    def __init__(self, vm):
        self.vm = vm
        self.tick_count = 0
        self.state = {}
        self.scenario = ""
        self._scenario_step = 0
        self._init_controller()

    # ─── controller internals ──────────────────────────────────────────

    def _init_controller(self):
        self._phase = "green_ns"
        self._cycle_index = 0
        self._cycle_tick = 0
        self._ped_request = False
        self._serving_ped = False
        self._ped_tick = 0
        self._emergency_stage = None
        self._emergency_stage_tick = 0
        self._was_override = False
        self._recovery_stage = None
        self._recovery_ring = None
        self._recovery_tick = 0
        self._demand_mean = 20
        self._demand_sigma = 3

    @classmethod
    def conflicting_approaches(cls):
        """Every pair of approaches that must never be authorised together."""
        pairs = []
        for ns in cls.RINGS["ns"]:
            for ew in cls.RINGS["ew"]:
                pairs.append((ns, ew))
        for approach in cls.VEHICLE_APPROACHES:
            pairs.append((approach, cls.PEDESTRIAN))
        return pairs

    @classmethod
    def conflicting_greens(cls, signals):
        """Return the conflicting pairs that are simultaneously authorised.

        An empty list means the signal map is safe. Exposed so a conflict
        monitor under development can be checked against the same rule the
        simulator holds itself to.
        """
        return [
            (a, b)
            for a, b in cls.conflicting_approaches()
            if signals.get(a) in GO_ASPECTS and signals.get(b) in GO_ASPECTS
        ]

    def setup(self):
        from eosim.engine.native.peripherals.composites import WatchdogTimer
        from eosim.engine.native.peripherals.sensors import (
            LightSensor,
            ProximitySensor,
            TemperatureSensor,
        )

        self.vm.add_peripheral("light0", LightSensor("light0", 0x40100500))
        self.vm.add_peripheral("prox0", ProximitySensor("prox0", 0x40100400))
        self.vm.add_peripheral("temp0", TemperatureSensor("temp0", 0x40100010))
        self.vm.add_peripheral("wdt0", WatchdogTimer("wdt0", 0x40500200))
        self._init_controller()
        self.state = {
            "phase": "green_ns",
            "signals": dict(PHASE_SIGNALS["green_ns"]),
            "green_time_s": 30,
            # Duration of the east-west green. Named red_time_s because it is
            # the time north-south is held at red; kept for compatibility.
            "red_time_s": 30,
            "yellow_time_s": 3,
            "all_red_time_s": 2,
            "ped_walk_time_s": 7,
            "ped_clear_time_s": 4,
            "vehicles_per_min": 20,
            "pedestrian_waiting": False,
            "emergency_override": False,
            "emergency_approach": "",
            "fault_active": False,
            "cycle_count": 0,
            "scenario": "",
        }

    def load_scenario(self, name):
        if name in self.SCENARIOS:
            self.scenario = name
            self._scenario_step = 0
            self.state["scenario"] = name

    def request_emergency(self, ring="ns"):
        """Request pre-emption for one ring. Unknown rings are ignored."""
        if ring not in self.RINGS:
            return False
        self.state["emergency_approach"] = ring
        self.state["emergency_override"] = True
        return True

    def clear_emergency(self):
        self.state["emergency_override"] = False
        self.state["emergency_approach"] = ""

    def request_pedestrian(self):
        """Latch a pedestrian push-button request."""
        self._ped_request = True
        self.state["pedestrian_waiting"] = True

    def tick(self):
        self.tick_count += 1
        for name, dev in self.vm.peripherals.items():
            if hasattr(dev, "simulate_tick"):
                dev.simulate_tick()
        # Scenarios set controller *inputs* only. The phase and the traffic
        # volume are outputs owned by the resolver below, so a scenario can no
        # longer be silently overwritten by the tick body that follows it.
        self._apply_scenario()
        self._phase = self._resolve_phase()
        self.state["phase"] = self._phase
        self.state["signals"] = dict(PHASE_SIGNALS[self._phase])
        self.state["vehicles_per_min"] = max(
            0, self._demand_mean + int(random.gauss(0, self._demand_sigma))
        )

    def _apply_scenario(self):
        # Re-established every tick so a scenario's inputs are authoritative
        # and values from a previous scenario cannot leak forward.
        self._demand_mean = 20
        self._demand_sigma = 3
        if not self.scenario:
            return
        if self.scenario == "rush_hour":
            self.state["green_time_s"] = 45
            self._demand_mean = 40
            self._demand_sigma = 5
        elif self.scenario == "emergency_vehicle":
            if self._scenario_step < 20:
                self.request_emergency("ns")
            else:
                self.clear_emergency()
        elif self.scenario == "pedestrian_crossing":
            if self._scenario_step == 0:
                self.request_pedestrian()
        elif self.scenario == "fault_mode":
            self.state["fault_active"] = True
        self._scenario_step += 1

    # ─── phase resolution ──────────────────────────────────────────────

    def _resolve_phase(self):
        """Single owner of the published phase.

        Priority: controller fault, then emergency pre-emption, then the
        normal cycle (which hosts the pedestrian interlude).
        """
        if self.state.get("fault_active"):
            self._was_override = True
            self._emergency_stage = None
            return "flash_yellow"
        if self.state.get("emergency_override"):
            self._was_override = True
            return self._resolve_emergency()
        if self._was_override:
            self._was_override = False
            self._emergency_stage = None
            self._begin_recovery()
        return self._resolve_cycle()

    def _green_ring(self):
        """Which ring, if any, currently holds the green."""
        signals = self.state.get("signals") or {}
        for ring, approaches in self.RINGS.items():
            if any(signals.get(a) == GREEN for a in approaches):
                return ring
        return None

    def _duration(self, key, default=1):
        try:
            return max(1, int(self.state.get(key, default)))
        except (TypeError, ValueError):
            return max(1, int(default))

    def _resolve_emergency(self):
        ring = self.state.get("emergency_approach") or "ns"
        if ring not in self.RINGS:
            ring = "ns"
        conflicting = "ew" if ring == "ns" else "ns"

        if self._emergency_stage is None:
            # Entering pre-emption. Conflicting movements are cleared through
            # yellow and all-red before the authorised ring gets its green.
            if self._green_ring() == conflicting:
                self._emergency_stage = "yellow"
            elif self._phase in ("ped_walk", "ped_clear"):
                self._emergency_stage = "ped_clear"
            else:
                self._emergency_stage = "all_red"
            self._emergency_stage_tick = 0
            self._serving_ped = False
        else:
            self._emergency_stage_tick += 1

        if self._emergency_stage == "yellow":
            if self._emergency_stage_tick < self._duration("yellow_time_s", 3):
                return "yellow_" + conflicting
            self._emergency_stage = "all_red"
            self._emergency_stage_tick = 0
        if self._emergency_stage == "ped_clear":
            if self._emergency_stage_tick < self._duration("ped_clear_time_s", 4):
                return "ped_clear"
            self._emergency_stage = "all_red"
            self._emergency_stage_tick = 0
        if self._emergency_stage == "all_red":
            if self._emergency_stage_tick < self._duration("all_red_time_s", 2):
                return "all_red"
            self._emergency_stage = "green"
            self._emergency_stage_tick = 0
        return "emergency_" + ring

    def _begin_recovery(self):
        """Clear whatever the override was showing before the cycle resumes."""
        ring = self._green_ring()
        self._recovery_ring = ring
        self._recovery_stage = "yellow" if ring else "all_red"
        self._recovery_tick = 0
        self._serving_ped = False
        self._ped_tick = 0

    def _resolve_recovery(self):
        if self._recovery_stage == "yellow":
            if self._recovery_tick < self._duration("yellow_time_s", 3):
                self._recovery_tick += 1
                return "yellow_" + self._recovery_ring
            self._recovery_stage = "all_red"
            self._recovery_tick = 0
        if self._recovery_stage == "all_red":
            if self._recovery_tick < self._duration("all_red_time_s", 2):
                self._recovery_tick += 1
                return "all_red"
        self._recovery_stage = None
        self._recovery_ring = None
        self._cycle_index = 0
        self._cycle_tick = 1
        return self.CYCLE_STEPS[0][0]

    def _advance_cycle_index(self):
        self._cycle_index = (self._cycle_index + 1) % len(self.CYCLE_STEPS)
        if self._cycle_index == 0:
            self.state["cycle_count"] = self.state.get("cycle_count", 0) + 1

    def _resolve_cycle(self):
        if self._recovery_stage is not None:
            return self._resolve_recovery()

        if self._serving_ped:
            walk = self._duration("ped_walk_time_s", 7)
            clear = self._duration("ped_clear_time_s", 4)
            self._ped_tick += 1
            if self._ped_tick <= walk:
                return "ped_walk"
            if self._ped_tick <= walk + clear:
                return "ped_clear"
            # Interlude over. The all-red step it replaced has been served by
            # the pedestrian clearance, which also holds every vehicle at red.
            self._serving_ped = False
            self._ped_tick = 0
            self._advance_cycle_index()
            self._cycle_tick = 0

        phase, duration_key = self.CYCLE_STEPS[self._cycle_index]

        # A pedestrian request ends a running green early: the crossing cannot
        # be served while a conflicting movement is authorised.
        if self._ped_request and phase in ("green_ns", "green_ew"):
            self._advance_cycle_index()
            self._cycle_tick = 0
            phase, duration_key = self.CYCLE_STEPS[self._cycle_index]

        self._cycle_tick += 1
        if self._cycle_tick > self._duration(duration_key):
            self._advance_cycle_index()
            self._cycle_tick = 1
            phase, duration_key = self.CYCLE_STEPS[self._cycle_index]
            if phase == "all_red" and self._ped_request:
                # Serve the crossing from the all-red: every vehicle approach
                # is already at red, so walk conflicts with nothing.
                self._ped_request = False
                self._serving_ped = True
                self._ped_tick = 1
                self.state["pedestrian_waiting"] = False
                return "ped_walk"
        return phase

    def get_state(self) -> dict:
        snapshot = dict(self.state)
        if "signals" in snapshot:
            snapshot["signals"] = dict(snapshot["signals"])
        return snapshot

    def get_peripherals(self) -> dict:
        return dict(self.vm.peripherals)

    def get_status_text(self) -> str:
        scn = f" [{self.scenario}]" if self.scenario else ""
        return f"{self.DISPLAY_NAME} | Tick {self.tick_count}{scn}"

    def reset(self):
        self.tick_count = 0
        self.state = {}
        self.scenario = ""
        self._scenario_step = 0
        self._init_controller()
