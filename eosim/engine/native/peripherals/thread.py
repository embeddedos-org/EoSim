# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""Thread mesh + border-router + Matter commissioning models for EoSim.

SIMULATION ONLY — this module models a Thread mesh, a Thread
border router, and the Matter commissioning window at the protocol
level so the eHub-Pro hub's defining network can be exercised before
any hardware exists (growth-backlog H4, eHub-Pro bundle slice).

Port-vs-simulate decision (H4 design time, following eNet #9 / SH1
``SIMULATE``): this is a simulation, NOT a port of OpenThread and NOT
a Thread stack. There is no 802.15.4 radio, no Thread stack, no
Matter stack, no Matter certification claim, and no hardware claim.
The commissioning bearer is decoupled from the eos BLE stack on
purpose: eos has no working BLE link layer (declarations plus failing
stubs, no GATT API — see eNet ``docs/ble-commissioning-audit.md``),
so H4 models the bearer here instead of waiting on a multi-slice eos
BLE program.

What the sim DOES model:
- the Thread mesh as an interrogation API surface (nodes, roles,
  parent links, routes, leader) — the Home Assistant Matter network
  map is the UX bar;
- a border router that forms the mesh, hands out RLOC16 addresses,
  and forwards packets between the mesh and a backbone prefix;
- the Matter commissioning window over BLE: discriminator
  advertising, the PASE exchange as a state machine, and the join
  into the mesh.

What it does NOT model: PASE cryptography (the passcode comparison
is a sim placeholder, not a security mechanism), device attestation
or DAC provisioning (eSec CY1 co-design, pending), and NFC
commissioning (documented follow-on, not v1). No key material is
ever stored: the border router records only whether a network key
has been set, never the key itself.
"""

from eosim.engine.native.peripherals.wireless import BLEModule, WirelessBase

# RLOC16 layout (deterministic sim allocation, Thread-shaped):
# routers sit on 0x0400 boundaries (router id in the top 6 bits),
# children take their parent router's base plus a child id 1..511.
ROUTER_STEP = 0x0400
MAX_ROUTERS = 32
MAX_CHILDREN_PER_ROUTER = 511

ROLE_LEADER = "leader"
ROLE_ROUTER = "router"
ROLE_CHILD = "child"
ROLE_END_DEVICE = "end-device"

COMMISSIONING_WINDOW_TICKS = 300


class ThreadNode:
    """One node in the simulated Thread mesh."""

    def __init__(
        self,
        rloc16: int,
        label: str,
        device_type: str = "generic",
        role: str = ROLE_END_DEVICE,
        link_quality: int = 3,
        parent_rloc16=None,
    ):
        self.rloc16 = rloc16
        # Deterministic extended address derived from the RLOC16, so
        # mesh snapshots are reproducible across runs.
        self.ext_addr = f"02:00:00:00:{rloc16 >> 8:02x}:{rloc16 & 0xFF:02x}:00:01"
        self.label = label
        self.device_type = device_type
        self.role = role
        self.link_quality = max(0, min(3, link_quality))
        self.parent_rloc16 = parent_rloc16

    def as_dict(self) -> dict:
        return {
            "rloc16": f"0x{self.rloc16:04x}",
            "ext_addr": self.ext_addr,
            "label": self.label,
            "device_type": self.device_type,
            "role": self.role,
            "link_quality": self.link_quality,
            "parent": (f"0x{self.parent_rloc16:04x}" if self.parent_rloc16 is not None else None),
        }


class ThreadMesh:
    """The mesh interrogation API surface.

    This is the FIRST surface H4 builds: everything a developer or
    an agent needs to ask about the mesh — who is on it, who leads
    it, who parents whom, how to reach a node — before any packet
    flows. MCP tools for mesh interrogation wrap this API later,
    under eSec Controls 7-9.
    """

    def __init__(self, partition_id: int = 1):
        self.partition_id = partition_id
        self.nodes: dict = {}
        self._next_router_id = 1
        self._next_child_id: dict = {}

    def add_node(self, node: ThreadNode) -> ThreadNode:
        if node.rloc16 in self.nodes:
            raise ValueError(f"RLOC16 0x{node.rloc16:04x} already in mesh")
        self.nodes[node.rloc16] = node
        # First router on an leaderless mesh becomes the leader.
        if node.role == ROLE_ROUTER and self.leader() is None:
            node.role = ROLE_LEADER
        return node

    def remove_node(self, rloc16: int):
        node = self.nodes.pop(rloc16, None)
        if node is None:
            return
        for other in self.nodes.values():
            if other.parent_rloc16 == rloc16:
                other.parent_rloc16 = None
        if node.role == ROLE_LEADER:
            routers = self.routers()
            if routers:
                routers[0].role = ROLE_LEADER

    def get_node(self, rloc16: int):
        return self.nodes.get(rloc16)

    def list_nodes(self, role=None) -> list:
        nodes = sorted(self.nodes.values(), key=lambda n: n.rloc16)
        if role is not None:
            nodes = [n for n in nodes if n.role == role]
        return nodes

    def leader(self):
        for node in self.nodes.values():
            if node.role == ROLE_LEADER:
                return node
        return None

    def routers(self) -> list:
        return [n for n in self.list_nodes() if n.role in (ROLE_LEADER, ROLE_ROUTER)]

    def children_of(self, rloc16: int) -> list:
        return [n for n in self.list_nodes() if n.parent_rloc16 == rloc16]

    def route_to(self, rloc16: int) -> list:
        """RLOC16 path from the leader down to ``rloc16`` via parents.

        Returns a list of hex RLOC16 strings, leader first. Empty
        when the node is unknown or has no path to the leader.
        """
        node = self.get_node(rloc16)
        if node is None:
            return []
        path = []
        seen = set()
        current = node
        while current is not None and current.rloc16 not in seen:
            seen.add(current.rloc16)
            path.append(f"0x{current.rloc16:04x}")
            if current.role == ROLE_LEADER:
                return list(reversed(path))
            current = self.get_node(current.parent_rloc16) if current.parent_rloc16 else None
        return []

    def next_router_rloc16(self) -> int:
        if self._next_router_id > MAX_ROUTERS:
            raise ValueError("mesh router table full (sim limit)")
        rloc16 = ROUTER_STEP * self._next_router_id
        self._next_router_id += 1
        return rloc16

    def next_child_rloc16(self, parent_rloc16: int) -> int:
        child_id = self._next_child_id.get(parent_rloc16, 0) + 1
        if child_id > MAX_CHILDREN_PER_ROUTER:
            raise ValueError("router child table full (sim limit)")
        self._next_child_id[parent_rloc16] = child_id
        return parent_rloc16 | child_id

    def interrogate(self) -> dict:
        """Home-Assistant-network-map-shaped snapshot of the mesh."""
        leader = self.leader()
        return {
            "partition_id": self.partition_id,
            "leader_rloc16": f"0x{leader.rloc16:04x}" if leader else None,
            "node_count": len(self.nodes),
            "router_count": len(self.routers()),
            "child_count": len(
                [n for n in self.nodes.values() if n.role in (ROLE_CHILD, ROLE_END_DEVICE)]
            ),
            "nodes": [n.as_dict() for n in self.list_nodes()],
            "routes": {f"0x{n.rloc16:04x}": self.route_to(n.rloc16) for n in self.list_nodes()},
        }


class ThreadBorderRouter(WirelessBase):
    """Simulated Thread border router (hub-side 802.15.4 + backbone).

    Forms the mesh, allocates RLOC16 addresses, and forwards packets
    between the mesh and the backbone IPv6 prefix. The radio itself
    is NOT simulated — there is no 802.15.4 PHY here; the router
    models the mesh-facing behavior a hub developer debugs against.
    """

    def __init__(self, name: str = "thread_br0", base_addr: int = 0x40400500):
        super().__init__(name, base_addr)
        self.mesh = ThreadMesh()
        self.formed = False
        self.channel = 15
        self.pan_id = 0x1234
        self.prefix = "fd00:db8::/64"
        self.backbone_connected = False
        self.forwarded_packets = 0
        self.network_key_set = False

    def form_network(
        self, channel: int = 15, pan_id: int = 0x1234, prefix: str = "fd00:db8::/64"
    ) -> ThreadNode:
        """Form the mesh. The border router itself is the leader."""
        if self.formed:
            return self.mesh.leader()
        self.channel = max(11, min(26, channel))
        self.pan_id = pan_id
        self.prefix = prefix
        self.formed = True
        self.network_key_set = True
        leader = ThreadNode(
            ROUTER_STEP,
            label="border-router",
            device_type="border-router",
            role=ROLE_ROUTER,
        )
        self.mesh.add_node(leader)  # promoted to leader: first router
        # The leader consumed router id 1; the allocator starts at 2.
        self.mesh._next_router_id = 2
        return leader

    def join_node(
        self, label: str, device_type: str = "generic", role: str = ROLE_CHILD
    ) -> ThreadNode:
        """Allocate an address and attach a node to the mesh."""
        if not self.formed:
            raise ValueError("border router has not formed a network yet")
        leader = self.mesh.leader()
        if role == ROLE_ROUTER:
            rloc16 = self.mesh.next_router_rloc16()
            node = ThreadNode(
                rloc16, label, device_type, role=ROLE_ROUTER, parent_rloc16=leader.rloc16
            )
        else:
            rloc16 = self.mesh.next_child_rloc16(leader.rloc16)
            node = ThreadNode(rloc16, label, device_type, role=role, parent_rloc16=leader.rloc16)
        return self.mesh.add_node(node)

    def connect_backbone(self):
        self.backbone_connected = True

    def forward_packet(self):
        if not self.formed:
            return
        self.forwarded_packets += 1

    def simulate_tick(self):
        pass

    def read_reg(self, offset: int) -> int:
        if offset == 0x00:
            return int(self.enabled) | (int(self.formed) << 1) | (int(self.backbone_connected) << 2)
        elif offset == 0x04:
            return len(self.mesh.nodes)
        elif offset == 0x08:
            leader = self.mesh.leader()
            return leader.rloc16 if leader else 0
        elif offset == 0x0C:
            return self.forwarded_packets
        return 0

    def write_reg(self, offset: int, val: int):
        if offset == 0x00:
            self.enabled = bool(val & 1)
            if val & 2 and not self.formed:
                self.form_network()
            if val & 4:
                self.connect_backbone()


class MatterCommissioning:
    """Matter commissioning window over a simulated BLE bearer.

    State machine: idle -> advertising -> pase_in_progress ->
    commissioned | failed. The bearer is the sim's own BLEModule
    (the attachment point named by the SH1 SIMULATE decision), not
    the eos BLE HAL: the sim models the commissioning window at
    protocol level — discriminator advertising, the PASE exchange as
    ordered state transitions, and the join into the mesh.

    Deliberately NOT modelled: PASE cryptography, device attestation,
    DAC provisioning (CY1 co-design, pending). The passcode check
    below is a sim placeholder, not a security mechanism; do not
    cite this class as evidence about real PASE behavior.
    """

    STATES = ("idle", "advertising", "pase_in_progress", "commissioned", "failed")

    def __init__(
        self,
        ble: BLEModule,
        border_router: ThreadBorderRouter,
        window_ticks: int = COMMISSIONING_WINDOW_TICKS,
    ):
        self.ble = ble
        self.border_router = border_router
        self.window_ticks = window_ticks
        self.state = "idle"
        self.discriminator = None
        self.passcode = None
        self.label = None
        self.device_type = None
        self.ticks_remaining = 0
        self.last_error = ""
        self.commissioned_node = None

    def open_window(
        self,
        discriminator: int,
        passcode: int,
        label: str = "matter-device",
        device_type: str = "light",
    ) -> dict:
        """Open the commissioning window: advertise the discriminator."""
        if self.state not in ("idle", "failed"):
            raise ValueError(f"commissioning window already {self.state}")
        if not 0 <= discriminator <= 4095:
            raise ValueError("discriminator must be a 12-bit value (0..4095)")
        if not 1 <= passcode <= 99999998:
            raise ValueError("passcode must be an 8-digit setup code (1..99999998)")
        self.discriminator = discriminator
        self.passcode = passcode
        self.label = label
        self.device_type = device_type
        self.ticks_remaining = self.window_ticks
        self.last_error = ""
        self.commissioned_node = None
        self.ble.start_advertising()
        self.ble.services.append(
            {
                "name": "matter-commissioning (simulated)",
                "discriminator": discriminator,
            }
        )
        self.state = "advertising"
        return self.status()

    def pase_exchange(self, passcode_attempt: int) -> dict:
        """Run the PASE exchange step (sim placeholder, no crypto)."""
        if self.state != "advertising":
            raise ValueError(f"PASE exchange requires advertising state, not {self.state}")
        self.state = "pase_in_progress"
        if passcode_attempt != self.passcode:
            self.last_error = "PASE failed: passcode mismatch (simulated)"
            self._fail()
            return self.status()
        node = self.border_router.join_node(self.label, self.device_type)
        self.commissioned_node = node
        self.ble.connect_peer()
        self.border_router.forward_packet()
        self.state = "commissioned"
        self._close_ble_window()
        return self.status()

    def tick(self):
        if self.state in ("advertising", "pase_in_progress"):
            self.ticks_remaining -= 1
            if self.ticks_remaining <= 0:
                self.last_error = "commissioning window expired (simulated)"
                self._fail()

    def close_window(self):
        self._close_ble_window()
        self.state = "idle"
        self.ticks_remaining = 0

    def _fail(self):
        self._close_ble_window()
        self.state = "failed"

    def _close_ble_window(self):
        self.ble.advertising = False
        self.ble.services = [
            s
            for s in self.ble.services
            if not (isinstance(s, dict) and s.get("name") == "matter-commissioning (simulated)")
        ]

    def status(self) -> dict:
        return {
            "state": self.state,
            "discriminator": self.discriminator,
            "label": self.label,
            "device_type": self.device_type,
            "ticks_remaining": self.ticks_remaining,
            "last_error": self.last_error,
            "commissioned_rloc16": (
                f"0x{self.commissioned_node.rloc16:04x}"
                if self.commissioned_node is not None
                else None
            ),
        }
