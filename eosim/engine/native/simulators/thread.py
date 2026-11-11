# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""Thread border-router + Matter commissioning simulator. Pure Python, cross-platform.

Growth-backlog H4 (eHub-Pro bundle slice): the hub's defining network
— a Thread mesh behind a border router, joined over BLE Matter
commissioning — exercised in simulation before hardware exists.
Simulation only: no Thread stack, no 802.15.4 radio, no Matter stack,
no certification claim. See docs/thread-border-router.md and
eosim/engine/native/peripherals/thread.py for the port-vs-simulate
decision and the fidelity limits.
"""


class ThreadBorderRouterSimulator:
    PRODUCT_TYPE = "thread_border_router"
    DISPLAY_NAME = "Thread Border Router"

    SCENARIOS = {
        "commission_device": {
            "discriminator": 3840,
            "passcode": 20202021,
            "label": "door-lock",
            "device_type": "door-lock",
            "description": "Commission a Matter device over BLE, then join the mesh",
        },
        "mesh_map": {
            "description": "Interrogate the mesh: nodes, roles, parents, routes",
        },
        "commission_timeout": {
            "discriminator": 3840,
            "passcode": 20202021,
            "label": "thermostat",
            "device_type": "thermostat",
            "description": "Commissioning window expires with no PASE attempt",
        },
    }

    # Seeded mesh members (eHub-Pro device family, H2 spec): one
    # router plus two end devices, already commissioned before the
    # scenario starts, so mesh_map has something to interrogate.
    SEED_NODES = (
        ("thermostat", "thermostat", "router"),
        ("light", "light", "child"),
        ("doorbell", "doorbell", "child"),
    )

    def __init__(self, vm):
        self.vm = vm
        self.tick_count = 0
        self.state = {}
        self.scenario = ""
        self._scenario_step = 0
        self.commissioning = None

    def setup(self):
        from eosim.engine.native.peripherals.thread import (
            MatterCommissioning,
            ThreadBorderRouter,
        )
        from eosim.engine.native.peripherals.wireless import BLEModule

        self.vm.add_peripheral("ble0", BLEModule("ble0", 0x40400100))
        br = ThreadBorderRouter("thread_br0", 0x40400500)
        self.vm.add_peripheral("thread_br0", br)
        br.form_network()
        br.connect_backbone()
        for label, device_type, role in self.SEED_NODES:
            br.join_node(label, device_type, role=role)
        self.commissioning = MatterCommissioning(self.vm.peripherals["ble0"], br, window_ticks=60)
        self.state = {
            "border_router_formed": True,
            "backbone_connected": True,
            "node_count": len(br.mesh.nodes),
            "leader_rloc16": "0x0400",
            "commissioning_state": "idle",
            "last_commissioned": None,
            "mesh_snapshot": br.mesh.interrogate(),
            "tx_count": 0,
            "scenario": "",
        }

    def load_scenario(self, name: str):
        if name not in self.SCENARIOS:
            return
        self.scenario = name
        self._scenario_step = 0
        self.state["scenario"] = name
        if name == "commission_device":
            cfg = self.SCENARIOS[name]
            self.commissioning.open_window(
                cfg["discriminator"], cfg["passcode"], cfg["label"], cfg["device_type"]
            )
        elif name == "commission_timeout":
            cfg = self.SCENARIOS[name]
            self.commissioning.open_window(
                cfg["discriminator"], cfg["passcode"], cfg["label"], cfg["device_type"]
            )

    def tick(self):
        self.tick_count += 1
        for name, dev in self.vm.peripherals.items():
            if hasattr(dev, "simulate_tick"):
                dev.simulate_tick()
        if self.commissioning is not None:
            self.commissioning.tick()
        self._apply_scenario()
        self._refresh_state()
        self._scenario_step += 1

    def _apply_scenario(self):
        if not self.scenario:
            return
        if self.scenario == "commission_device":
            if self._scenario_step == 5 and self.commissioning.state == "advertising":
                self.commissioning.pase_exchange(self.SCENARIOS["commission_device"]["passcode"])
        elif self.scenario == "mesh_map":
            pass
        elif self.scenario == "commission_timeout":
            pass

    def _refresh_state(self):
        br = self.vm.peripherals.get("thread_br0")
        if br is None:
            return
        leader = br.mesh.leader()
        self.state["node_count"] = len(br.mesh.nodes)
        self.state["leader_rloc16"] = f"0x{leader.rloc16:04x}" if leader else None
        self.state["border_router_formed"] = br.formed
        self.state["backbone_connected"] = br.backbone_connected
        self.state["tx_count"] = br.forwarded_packets
        self.state["mesh_snapshot"] = br.mesh.interrogate()
        if self.commissioning is not None:
            status = self.commissioning.status()
            self.state["commissioning_state"] = status["state"]
            if status["commissioned_rloc16"] is not None:
                self.state["last_commissioned"] = status["commissioned_rloc16"]

    def get_state(self) -> dict:
        return dict(self.state)

    def get_peripherals(self) -> dict:
        return dict(self.vm.peripherals)

    def get_status_text(self) -> str:
        return (
            f"{self.DISPLAY_NAME} | Nodes {self.state.get('node_count', 0)} "
            f"| Commissioning {self.state.get('commissioning_state', 'idle')} "
            f"| Tick {self.tick_count}"
        )

    def reset(self):
        self.tick_count = 0
        self.state = {}
        self.scenario = ""
        self._scenario_step = 0
        self.commissioning = None
        self.setup()
        self.tick_count = 0
