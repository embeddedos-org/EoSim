# Thread border-router + Matter commissioning simulation (H4)

> Status: simulation slice, 2026-11-10 (growth-backlog H4, eHub-Pro
> bundle). Home: EoSim. Refs: growth-backlog H4; eNet #9 (SH1 SIMULATE).

## Why this exists

The eHub-Pro hub's defining network is a Thread mesh behind a border
router, joined over BLE Matter commissioning. That network cannot be
exercised before hardware exists — Seam 5 (waiting for hardware) +
debugging. This sim lets a developer commission a device, watch it
join the mesh, and interrogate the mesh (nodes, roles, parents,
routes) with no hardware on the bench.

## Port-vs-simulate decision (H4 design time)

| Option | Verdict | Reason |
|---|---|---|
| Port OpenThread into EoSim / eos, then build H4 on it | **Rejected for H4** | Needs a real Thread stack plus a working BLE link layer. eos has neither: no Thread/802.15.4 presence at all, and its BLE surface is declarations plus failing stubs with no GATT API (eNet `docs/ble-commissioning-audit.md`, SH1). A port is a multi-slice eos program, not a prerequisite H4 can wait on. |
| Simulate the mesh + border router + commissioning bearer in EoSim, decoupled from eos BLE | **Chosen** | The mesh, the border router, and the commissioning window are modelled at protocol level in the sim, using the existing `BLEModule` peripheral pattern as the attachment point. No eos BLE code is on the H4 critical path. |

A real OpenThread port remains a separate, later prerequisite for
hardware bring-up; it is not gated by this sim and this sim is not a
step toward it beyond the interrogation API shape.

## What the sim models

- **Mesh interrogation API first** (`ThreadMesh` in
  `eosim/engine/native/peripherals/thread.py`): `list_nodes()`,
  `get_node()`, `leader()`, `routers()`, `children_of()`,
  `route_to()`, `interrogate()`. `interrogate()` returns a
  Home-Assistant-network-map-shaped snapshot: partition, leader,
  per-node rows (RLOC16, extended address, role, link quality,
  parent), and a route per node from the leader down. MCP tools for
  mesh interrogation wrap this API later, under eSec Controls 7–9.
- **Border router** (`ThreadBorderRouter`, same module): forms the
  mesh (itself the leader at RLOC16 `0x0400`), allocates RLOC16
  addresses deterministically (routers on `0x0400` boundaries,
  children under their parent router), tracks the backbone IPv6
  prefix and forwarded-packet count, and exposes the usual
  register interface at base `0x40400500`.
- **Matter commissioning flow** (`MatterCommissioning`, same module):
  state machine `idle -> advertising -> pase_in_progress ->
  commissioned | failed`. `open_window(discriminator, passcode)`
  advertises the discriminator over the sim's `BLEModule` and
  records a simulated commissioning service; `pase_exchange()`
  joins the device into the mesh on a matching passcode; the window
  expires after `window_ticks` sim ticks with no PASE attempt.

## What it does NOT claim

- **No Thread stack, no 802.15.4 radio, no Matter stack.** The radio
  is not simulated; the router models mesh-facing behavior only.
- **No Matter certification claim** and no conformance claim of any
  kind.
- **No PASE cryptography.** The passcode comparison is a sim
  placeholder, not a security mechanism. Do not cite this sim as
  evidence about real PASE behavior.
- **No attestation / DAC behavior.** Device identity provisioning is
  the eSec CY1 co-design, still pending; the sim invents none of it.
- **No hardware claim.** Seeded nodes (thermostat, light, doorbell)
  are eHub-Pro device-family labels, not devices.
- **No key material is ever stored.** The border router records only
  whether a network key has been set.

## The product simulator

`ThreadBorderRouterSimulator`
(`eosim/engine/native/simulators/thread.py`, product type
`thread_border_router`, alias `thread_br`):

```python
from eosim.engine.native.simulators import SimulatorFactory
sim = SimulatorFactory.create("thread_border_router", vm)
sim.load_scenario("commission_device")  # or "mesh_map", "commission_timeout"
sim.tick()
sim.get_state()["mesh_snapshot"]  # interrogation snapshot
```

Scenarios:

| Scenario | What happens |
|---|---|
| `commission_device` | Opens the commissioning window (discriminator 3840, setup code 20202021), runs PASE, joins a `door-lock` node to the mesh. |
| `mesh_map` | No commissioning; the seeded mesh is interrogated each tick. |
| `commission_timeout` | Opens the window and never attempts PASE; the window expires and the device never joins. |

Setup seeds the mesh with a leader (the border router) plus one
router (`thermostat`) and two end devices (`light`, `doorbell`),
so `mesh_map` has something to interrogate from tick zero.

## Follow-ons (not v1)

- **NFC commissioning** as a second bearer (documented here, not
  implemented): same `MatterCommissioning` state machine driven by
  an NFC tap instead of BLE advertising.
- **CY1 DAC co-design** with eSec: attestation behavior once the
  provisioning contract exists.
- **OpenThread port** as a separate hardware-bring-up prerequisite
  (see the decision table above).
