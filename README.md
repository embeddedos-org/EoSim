# EoSim — World-Class Multi-Architecture Embedded Simulation Platform

[![CI](https://github.com/embeddedos-org/eosim/actions/workflows/ci.yml/badge.svg)](https://github.com/embeddedos-org/eosim/actions/workflows/ci.yml)
[![CodeQL](https://github.com/embeddedos-org/eosim/actions/workflows/codeql.yml/badge.svg)](https://github.com/embeddedos-org/eosim/actions/workflows/codeql.yml)
[![Scorecard](https://github.com/embeddedos-org/eosim/actions/workflows/scorecard.yml/badge.svg)](https://github.com/embeddedos-org/eosim/actions/workflows/scorecard.yml)
[![Nightly](https://github.com/embeddedos-org/eosim/actions/workflows/nightly.yml/badge.svg)](https://github.com/embeddedos-org/eosim/actions/workflows/nightly.yml)
[![Release](https://github.com/embeddedos-org/eosim/actions/workflows/release.yml/badge.svg)](https://github.com/embeddedos-org/eosim/actions/workflows/release.yml)
[![Version](https://img.shields.io/github/v/tag/embeddedos-org/eosim?label=version)](https://github.com/embeddedos-org/eosim/releases/latest)
[![Docs](https://img.shields.io/badge/docs-PDF%20%7C%20HTML-blue)](https://github.com/embeddedos-org/eosim/tree/main/docs)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**The most comprehensive open-source embedded simulation platform — simulate, validate, and test embedded systems across 150+ platforms, 40 domains, and 26 architectures before hardware is ready.**

EoSim rivals industry leaders like Wind River Simics, MATLAB/Simulink, dSPACE, and Vector CANoe — with the flexibility of open source, pure Python implementation, and seamless CI/CD integration.

---

## Key Numbers

| Metric | Count |
|--------|-------|
| Platform Definitions | **150+** |
| Architectures | **26** (ARM, RISC-V, x86, AVR, PIC, MIPS, TriCore, ...) |
| Industry Domains | **40** (automotive, aerospace, medical, nuclear, ...) |
| Domain Simulators | **49** |
| Product Templates | **80+** |
| Peripheral Models | **100+** |
| Engine Backends | **10** (EoSim, QEMU, Renode, CARLA, AirSim, ROS 2, ...) |
| GUI Renderers | **33** domain-specific 3D renderers |

---

## Installation

```bash
# Basic install
pip install git+https://github.com/embeddedos-org/eosim.git

# With all optional dependencies
pip install "eosim[all]"

# Development install
git clone https://github.com/embeddedos-org/eosim.git
cd eosim
pip install -e ".[dev]"

# With REST API support
pip install "eosim[api]"
```

### System Requirements

- Python 3.9+
- No C extensions required — pure Python, cross-platform
- Optional: QEMU, Renode, Matplotlib, FastAPI

---

## Quick Start

```bash
# List all 150+ platforms
eosim list

# Filter by architecture or domain
eosim list --arch arm64
eosim list --domain automotive

# Platform details
eosim info stm32h7

# Run simulation
eosim run stm32f4

# Run validation tests
eosim test arm64-linux

# Open GUI dashboard
eosim gui stm32f4

# Platform statistics
eosim stats

# Search platforms by keyword
eosim search "bluetooth"

# Health check
eosim doctor
```

### Python API

```python
from eosim.engine.native.simulators import SimulatorFactory

# Create a vehicle simulator
class FakeVM:
    peripherals = {}
    def add_peripheral(self, name, dev):
        self.peripherals[name] = dev

vm = FakeVM()
sim = SimulatorFactory.create('automotive_ecu', vm)

# Run simulation
for _ in range(100):
    sim.tick()

print(sim.get_state())
print(sim.get_status_text())
```

### REST API

```python
from eosim.api.server import EoSimAPIServer

server = EoSimAPIServer(host='0.0.0.0', port=8080)
server.run()
# GET  /api/v1/platforms
# GET  /api/v1/domains
# GET  /api/v1/simulators
# POST /api/v1/simulations/{name}/tick
# WS   /ws/simulations/{name}
```

---

## Supported Platforms (150+)

### By Vendor

| Vendor | Platforms | Architectures |
|--------|-----------|---------------|
| STMicroelectronics | stm32f4, stm32h7, stm32l4, stm32mp1 | ARM Cortex-M/A |
| Nordic Semiconductor | nrf52, nrf5340, nrf9160 | ARM Cortex-M |
| Espressif | esp32, esp32s3, esp32c3 | Xtensa, RISC-V |
| Raspberry Pi | raspi2b, raspi3, raspi4, raspi5, raspi-zero2w | ARM Cortex-A |
| NXP | s32k344, lpc55s69, imxrt1060, s32g274a, s32z, k64f | ARM Cortex-M/A/R |
| Texas Instruments | msp430, cc2652, cc3220, am62x, tda4vm, tms320 | MSP430, ARM |
| Renesas | ra4m1, rx65n, rl78, rcar-h3, rcar-s4, rza2m | ARM, RX |
| Microchip | atmega328p, atmega2560, pic32mx, samd21, same70 | AVR, PIC, ARM |
| Silicon Labs | efm32gg, efr32bg22, efr32mg24 | ARM Cortex-M |
| NVIDIA | jetson-nano, jetson-orin | ARM Cortex-A |
| AMD/Xilinx | xilinx-zynq7020, xilinx-versal | ARM, FPGA |
| Intel/Altera | intel-cyclone-v | ARM, FPGA |
| Lattice | lattice-ice40, lattice-ecp5 | RISC-V, FPGA |
| Google | google-coral | Edge TPU |
| Apple | apple-m1, apple-tv | ARM64 |
| Qualcomm | qualcomm-qcs610 | ARM64 |
| StarFive | starfive-jh7110 | RISC-V |
| Allwinner | allwinner-d1 | RISC-V |
| Bouffalo Lab | bl602, bl706 | RISC-V |
| WCH | ch32v307 | RISC-V |

### By Domain

| Domain | Simulator | Example Products |
|--------|-----------|-----------------|
| Automotive | VehicleSimulator | ECU, EV powertrain, ADAS |
| Aerospace | AircraftSimulator, SatelliteSimulator | Fixed-wing, CubeSat |
| Medical | MedicalSimulator | Patient monitor, surgical robot |
| Defense | DefenseSimulator | Tactical radio, radar |
| Robotics | RobotSimulator, DroneSimulator | Industrial robot, UAV |
| Railway | RailwaySimulator | Train control, signaling, PTC |
| Nuclear | NuclearSimulator | Reactor control, radiation monitor |
| Maritime | MaritimeSimulator | Ship autopilot, AIS |
| Agriculture | AgricultureSimulator | Irrigation, tractor ECU, greenhouse |
| Smart City | SmartCitySimulator | Traffic lights, parking, street lighting |
| HVAC | HVACSimulator | Thermostat, climate control |
| Logistics | LogisticsSimulator | Warehouse AGV, conveyor sorting |
| AR/VR | ARVRSimulator | Smart glasses, VR headset |
| Quantum | QuantumSimulator | Quantum processor, error correction |
| Cybersecurity | CybersecuritySimulator | Firewall, HSM, IDS/IPS |
| Oil & Gas | OilGasSimulator | Pipeline SCADA, wellhead |
| Water | WaterSimulator | Treatment, pump station |
| Mining | MiningSimulator | Drill control, gas detection |
| Construction | ConstructionSimulator | Crane controller, excavator |
| Energy | EnergySimulator, SmartGridSimulator | Solar inverter, substation |
| ... | ... | 40 domains total |

---

## Architecture

```
eosim/
├── eosim/
│   ├── cli/                 CLI entry point (click-based)
│   ├── core/                Core: schema, domains, registry, platform, modeling
│   │   ├── schema.py        26 architectures, 40 domains, 20 modeling methods
│   │   ├── domains.py       40 domain profiles with standards & safety levels
│   │   ├── platform.py      Platform loader and YAML parser
│   │   └── registry.py      Platform discovery and filtering
│   ├── engine/
│   │   ├── backend.py       10 engine backends (EoSim, QEMU, Renode, CARLA, ...)
│   │   ├── native/
│   │   │   ├── simulators/  49 domain simulators
│   │   │   ├── peripherals/ 100+ peripheral models (sensors, actuators, buses)
│   │   │   ├── cpu/         CPU core models
│   │   │   ├── memory/      Memory subsystem
│   │   │   └── bus/         Bus interconnect
│   │   └── qemu/            QEMU QMP + GDB bridge
│   ├── gui/
│   │   ├── product_templates.py  80+ product templates
│   │   ├── renderers/       33 domain-specific 3D renderers
│   │   ├── widgets/         CPU, GPIO, UART, memory panels
│   │   └── simulator_app.py GUI application
│   ├── integrations/        External bridges (CARLA, AirSim, ROS 2, Verilator, ...)
│   ├── api/                 REST API server (FastAPI) + WebSocket
│   ├── plugins/             Plugin system (discovery, loading, base class)
│   ├── analysis/            Power, thermal, safety, security, timing analysis
│   ├── digital_twin/        Digital twin engine
│   ├── codegen/             C code generation from simulation models
│   ├── network/             Network topology simulation
│   └── artifacts/           Simulation artifact management
├── platforms/               150+ platform definitions (YAML)
├── tests/                   Unit + integration + scenario tests
├── docs/                    Documentation (Markdown, Doxygen, PDF)
├── examples/                Demo scenarios
└── pyproject.toml           Python package config
```

---

## Simulation Engines

| Engine | Type | Speed | Fidelity | Use Case |
|--------|------|-------|----------|----------|
| **EoSim Native** | Python simulation | Fast | Medium | Rapid prototyping, CI, peripheral logic |
| **QEMU** | Binary emulation | Medium | High | Full firmware on emulated CPU |
| **QEMU Live** | QEMU + QMP/GDB | Medium | High | Interactive debugging, register inspection |
| **Renode** | Deterministic sim | Medium | High | Peripheral-accurate, multi-node |
| **X-Plane** | Flight sim bridge | Real-time | High | Fixed-wing aircraft simulation |
| **Gazebo** | Robot sim bridge | Real-time | High | ROS 2 robot simulation |
| **OpenFOAM** | CFD solver | Slow | Very High | Aerodynamics, fluid dynamics |
| **CARLA** | Driving sim | Real-time | High | Autonomous driving, V2X |
| **AirSim** | Drone/car sim | Real-time | High | UAV, autonomous vehicles |
| **ROS 2** | Robot framework | Real-time | High | ROS 2 node integration |

---

## Analysis & Advanced Features

### Power Analysis
```python
from eosim.analysis.power import PowerAnalyzer, PowerProfile

analyzer = PowerAnalyzer()
analyzer.add_profile('nrf52', PowerProfile(
    voltage_v=3.3, current_active_ma=5.0, current_sleep_ma=0.002))
print(analyzer.estimate_battery_life('nrf52', capacity_mah=250, duty_cycle_pct=1))
# → ~4995 hours
```

### Thermal Modeling
```python
from eosim.analysis.thermal import ThermalModel

model = ThermalModel(ambient_c=25.0, thermal_resistance_cw=15.0)
steady = model.steady_state(power_w=2.0)  # → 55.0°C
```

### Functional Safety (ISO 26262 / IEC 61508)
```python
from eosim.analysis.safety import SafetyAnalyzer, SafetyRequirement

sa = SafetyAnalyzer()
sa.add_requirement(SafetyRequirement(req_id='SWR-001', standard='ISO 26262', level='ASIL-D'))
sa.verify('SWR-001')
print(sa.report())  # coverage, verified/unverified counts
```

### Digital Twin
```python
from eosim.digital_twin.twin import DigitalTwin

twin = DigitalTwin('engine_ecu', simulator)
twin.sync()                    # Mirror current state
states = twin.predict(steps=100)  # Predict future states
twin.export_json('twin_data.json')
```

### Plugin System
```python
from eosim.plugins.base import PluginBase

class MyPlugin(PluginBase):
    NAME = "data-logger"
    VERSION = "1.0.0"
    def on_load(self):
        print("Plugin loaded!")
    def on_tick(self, simulator, state):
        # Log state each tick
        pass
```

---

## Documentation

### Generate PDF Documentation (Doxygen)

```bash
# Install Doxygen
sudo apt install doxygen graphviz

# Generate HTML + PDF
cd docs
doxygen Doxyfile

# Output:
#   docs/output/html/index.html   — HTML documentation
#   docs/output/latex/refman.pdf  — PDF reference manual
```

### Documentation Structure

```
docs/
├── Doxyfile                 Doxygen configuration
├── getting-started.md       Installation and quick start
├── architecture.md          System architecture overview
├── api-reference.md         Python API reference
├── cli-reference.md         CLI command reference
├── platform-authoring.md    How to add new platforms
├── simulator-guide.md       Writing custom simulators
├── peripheral-guide.md      Creating peripheral models
├── domain-guide.md          Adding new industry domains
├── engine-integration.md    Integrating external engines
├── analysis-guide.md        Power, thermal, safety analysis
├── plugin-development.md    Plugin system guide
├── rest-api-guide.md        REST API documentation
├── digital-twin-guide.md    Digital twin usage
├── production-deployment.md Production deployment guide
├── hil-guide.md             Hardware-in-the-loop testing
└── book/                    Academic book source
```

---

## Production Deployment

### Docker

```bash
docker build -t eosim .
docker run -p 8080:8080 eosim python -m eosim.api.server
```

### Docker Compose

```bash
docker-compose up -d
# API: http://localhost:8080
# Docs: http://localhost:8080/docs
```

### CI/CD Integration

```yaml
# GitHub Actions
- name: Run EoSim tests
  run: |
    pip install eosim
    eosim validate --all
    eosim test stm32f4
    python -m pytest tests/ -v
```

---

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=eosim --cov-report=html

# Run only unit tests
python -m pytest tests/unit/ -v

# Run specific test
python -m pytest tests/unit/test_new_simulators.py -v
```

---

## Standards Compliance

| Standard | Coverage |
|----------|----------|
| ISO 26262 (Automotive Safety) | ASIL-A through ASIL-D |
| IEC 61508 (Functional Safety) | SIL-1 through SIL-4 |
| DO-178C (Avionics) | DAL-A through DAL-E |
| IEC 62304 (Medical Devices) | Class A, B, C |
| ISO 21434 (Automotive Cybersecurity) | Security analysis |
| FIPS 140-3 (Cryptographic Modules) | HSM simulation |
| EN 50128 (Railway) | SIL-3, SIL-4 |
| IEC 61513 (Nuclear) | Safety-critical control |

---

## EoS Ecosystem

| Repo | Description |
|------|-------------|
| [eos](https://github.com/embeddedos-org/eos) | Embedded OS — HAL, RTOS kernel, drivers |
| [eboot](https://github.com/embeddedos-org/eboot) | Bootloader — 24 boards, secure boot |
| [ebuild](https://github.com/embeddedos-org/ebuild) | Build system — SDK generator |
| [eipc](https://github.com/embeddedos-org/eipc) | IPC framework — Go + C SDK |
| [eai](https://github.com/embeddedos-org/eai) | AI layer — LLM inference |
| [eApps](https://github.com/embeddedos-org/eApps) | Cross-platform apps — LVGL |
| [EoStudio](https://github.com/embeddedos-org/EoStudio) | Design suite — 10 editors |
| **EoSim** | **Simulation platform (this repo)** |

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines.

## License

MIT License — see [LICENSE](LICENSE) for details.

---

Part of the [EmbeddedOS Organization](https://embeddedos-org.github.io).
