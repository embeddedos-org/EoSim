# SPDX-License-Identifier: MIT
"""Unit tests for the H4 Thread border-router + Matter commissioning sim."""
import pytest

from eosim.engine.native.peripherals.thread import (
    ROLE_CHILD,
    ROLE_LEADER,
    ROLE_ROUTER,
    MatterCommissioning,
    ThreadBorderRouter,
    ThreadMesh,
    ThreadNode,
)
from eosim.engine.native.peripherals.wireless import BLEModule
from eosim.engine.native.simulators import SimulatorFactory, SIMULATOR_MAP
from eosim.engine.native.simulators.thread import ThreadBorderRouterSimulator


class FakeVM:
    """Minimal VM mock for simulator testing."""

    def __init__(self):
        self.peripherals = {}

    def add_peripheral(self, name, dev):
        self.peripherals[name] = dev


def _mesh_with_leader():
    mesh = ThreadMesh()
    leader = ThreadNode(0x0400, "border-router", "border-router", ROLE_ROUTER)
    mesh.add_node(leader)
    return mesh


class TestThreadMesh:
    def test_first_router_becomes_leader(self):
        mesh = _mesh_with_leader()
        assert mesh.leader().role == ROLE_LEADER
        assert mesh.leader().rloc16 == 0x0400

    def test_duplicate_rloc16_rejected(self):
        mesh = _mesh_with_leader()
        with pytest.raises(ValueError):
            mesh.add_node(ThreadNode(0x0400, "dup", "generic", ROLE_CHILD))

    def test_children_and_routes(self):
        mesh = _mesh_with_leader()
        child = ThreadNode(0x0401, "light", "light", ROLE_CHILD, parent_rloc16=0x0400)
        mesh.add_node(child)
        assert mesh.children_of(0x0400) == [child]
        assert mesh.route_to(0x0401) == ["0x0400", "0x0401"]
        assert mesh.route_to(0x0400) == ["0x0400"]
        assert mesh.route_to(0x9999) == []

    def test_interrogate_snapshot_shape(self):
        mesh = _mesh_with_leader()
        mesh.add_node(ThreadNode(0x0401, "light", "light", ROLE_CHILD, parent_rloc16=0x0400))
        snap = mesh.interrogate()
        assert snap["partition_id"] == 1
        assert snap["leader_rloc16"] == "0x0400"
        assert snap["node_count"] == 2
        assert snap["router_count"] == 1
        assert snap["child_count"] == 1
        assert snap["nodes"][1]["rloc16"] == "0x0401"
        assert snap["nodes"][1]["parent"] == "0x0400"
        assert snap["routes"]["0x0401"] == ["0x0400", "0x0401"]

    def test_remove_leader_promotes_router(self):
        mesh = _mesh_with_leader()
        router = ThreadNode(0x0800, "thermostat", "thermostat", ROLE_ROUTER,
                            parent_rloc16=0x0400)
        mesh.add_node(router)
        mesh.remove_node(0x0400)
        assert mesh.leader().rloc16 == 0x0800
        assert mesh.leader().role == ROLE_LEADER

    def test_remove_node_reparents_children(self):
        mesh = _mesh_with_leader()
        mesh.add_node(ThreadNode(0x0401, "light", "light", ROLE_CHILD, parent_rloc16=0x0400))
        mesh.remove_node(0x0400)
        assert mesh.get_node(0x0401).parent_rloc16 is None


class TestThreadBorderRouter:
    def test_form_network_and_registers(self):
        br = ThreadBorderRouter()
        assert br.read_reg(0x04) == 0
        leader = br.form_network()
        assert br.formed is True
        assert leader.role == ROLE_LEADER
        assert br.read_reg(0x04) == 1
        assert br.read_reg(0x08) == 0x0400

    def test_join_router_and_child_no_collision(self):
        br = ThreadBorderRouter()
        br.form_network()
        router = br.join_node("thermostat", "thermostat", role=ROLE_ROUTER)
        child = br.join_node("light", "light", role=ROLE_CHILD)
        assert router.rloc16 == 0x0800
        assert child.rloc16 == 0x0401
        assert len({n.rloc16 for n in br.mesh.list_nodes()}) == 3

    def test_join_before_form_raises(self):
        br = ThreadBorderRouter()
        with pytest.raises(ValueError):
            br.join_node("light", "light")

    def test_forward_packet_counts_only_when_formed(self):
        br = ThreadBorderRouter()
        br.forward_packet()
        assert br.forwarded_packets == 0
        br.form_network()
        br.forward_packet()
        assert br.read_reg(0x0C) == 1

    def test_write_reg_forms_network(self):
        br = ThreadBorderRouter()
        br.write_reg(0x00, 0x02)
        assert br.formed is True
        assert br.read_reg(0x00) & 0x02


class TestMatterCommissioning:
    def _commissioning(self):
        ble = BLEModule()
        br = ThreadBorderRouter()
        br.form_network()
        return ble, br, MatterCommissioning(ble, br, window_ticks=10)

    def test_happy_path_joins_mesh(self):
        ble, br, comm = self._commissioning()
        status = comm.open_window(3840, 20202021, "door-lock", "door-lock")
        assert status["state"] == "advertising"
        assert ble.advertising is True
        assert any(
            isinstance(s, dict) and s.get("discriminator") == 3840 for s in ble.services
        )
        status = comm.pase_exchange(20202021)
        assert status["state"] == "commissioned"
        assert status["commissioned_rloc16"] is not None
        assert br.mesh.get_node(int(status["commissioned_rloc16"], 16)) is not None
        assert ble.connected is True
        assert ble.advertising is False
        # Commissioning service entry is removed once the window closes.
        assert not any(
            isinstance(s, dict) and "matter-commissioning" in str(s.get("name", ""))
            for s in ble.services
        )

    def test_wrong_passcode_fails_without_join(self):
        ble, br, comm = self._commissioning()
        before = len(br.mesh.nodes)
        comm.open_window(3840, 20202021, "door-lock", "door-lock")
        status = comm.pase_exchange(11111111)
        assert status["state"] == "failed"
        assert "mismatch" in status["last_error"]
        assert len(br.mesh.nodes) == before
        assert ble.connected is False

    def test_window_expiry_fails(self):
        _, _, comm = self._commissioning()
        comm.open_window(3840, 20202021, "thermostat", "thermostat")
        for _ in range(10):
            comm.tick()
        assert comm.state == "failed"
        assert "expired" in comm.last_error

    def test_invalid_discriminator_and_passcode_rejected(self):
        _, _, comm = self._commissioning()
        with pytest.raises(ValueError):
            comm.open_window(4096, 20202021)
        with pytest.raises(ValueError):
            comm.open_window(3840, 0)
        with pytest.raises(ValueError):
            comm.open_window(3840, 100000000)

    def test_pase_without_window_raises(self):
        _, _, comm = self._commissioning()
        with pytest.raises(ValueError):
            comm.pase_exchange(20202021)

    def test_double_open_raises(self):
        _, _, comm = self._commissioning()
        comm.open_window(3840, 20202021)
        with pytest.raises(ValueError):
            comm.open_window(1, 20202021)


class TestThreadBorderRouterSimulator:
    def _sim(self):
        return ThreadBorderRouterSimulator(FakeVM())

    def test_factory_registration(self):
        assert "thread_border_router" in SIMULATOR_MAP
        assert "thread_br" in SIMULATOR_MAP
        sim = SimulatorFactory.create("thread_border_router", FakeVM())
        assert isinstance(sim, ThreadBorderRouterSimulator)

    def test_setup_seeds_mesh(self):
        sim = self._sim()
        sim.setup()
        assert sim.state["border_router_formed"] is True
        assert sim.state["backbone_connected"] is True
        assert sim.state["node_count"] == 4  # leader + 3 seeded nodes
        assert sim.state["leader_rloc16"] == "0x0400"
        assert sim.state["commissioning_state"] == "idle"
        snap = sim.state["mesh_snapshot"]
        assert snap["node_count"] == 4
        assert snap["leader_rloc16"] == "0x0400"

    def test_commission_device_scenario(self):
        sim = self._sim()
        sim.setup()
        sim.load_scenario("commission_device")
        for _ in range(10):
            sim.tick()
        assert sim.state["commissioning_state"] == "commissioned"
        assert sim.state["last_commissioned"] is not None
        assert sim.state["node_count"] == 5
        assert sim.state["tx_count"] >= 1

    def test_mesh_map_scenario(self):
        sim = self._sim()
        sim.setup()
        sim.load_scenario("mesh_map")
        for _ in range(3):
            sim.tick()
        snap = sim.state["mesh_snapshot"]
        assert snap["node_count"] == 4
        assert all("0x0400" in route[0] for route in snap["routes"].values() if route)

    def test_commission_timeout_scenario(self):
        sim = self._sim()
        sim.setup()
        sim.load_scenario("commission_timeout")
        for _ in range(70):
            sim.tick()
        assert sim.state["commissioning_state"] == "failed"
        assert sim.state["node_count"] == 4  # nobody joined

    def test_reset_restores_seeded_mesh(self):
        sim = self._sim()
        sim.setup()
        sim.load_scenario("commission_device")
        for _ in range(10):
            sim.tick()
        assert sim.state["node_count"] == 5
        sim.reset()
        assert sim.tick_count == 0
        assert sim.state["node_count"] == 4
        assert sim.state["commissioning_state"] == "idle"

    def test_status_text(self):
        sim = self._sim()
        sim.setup()
        assert "Thread Border Router" in sim.get_status_text()
        assert "Tick" in sim.get_status_text()
