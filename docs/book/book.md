---
title: "EoSim — World-Class Embedded Simulation Platform"
subtitle: "Official Reference Guide — 150+ Platforms, 40 Domains, 26 Architectures"
author: "Srikanth Patchava & EmbeddedOS Contributors"
date: "April 2026"
version: "v2.0.0"
bibliography: references.bib
csl: ieee.csl
titlepage: true
titlepage-background: "cover.png"
toc: true
toc-depth: 3
numbersections: true
geometry: margin=1in
fontsize: 11pt
---

\newpage

# Preface

EoSim v2.0 represents a generational leap in embedded simulation capability. What began as a 52-platform simulation tool has evolved into the **most comprehensive open-source embedded simulation platform in the world** — rivaling commercial tools from Wind River, MathWorks, dSPACE, and Vector.

This edition covers **150+ platforms** across **26 architectures** and **40 industry domains**, from tiny ATtiny85 microcontrollers to Apple M1 application processors, from automotive ECUs to nuclear reactor controllers, from Arduino boards to quantum computing systems.

**What's new in v2.0:**

- 87 new platform definitions (Microchip, TI, Silicon Labs, Renesas, NXP, FPGA, AI accelerators)
- 25 new industry domains (nuclear, railway, maritime, agriculture, quantum, AR/VR, ...)
- 30 new domain simulators with physics-based modeling
- 60 new peripheral models (sensors, actuators, buses, wireless)
- REST API with FastAPI and WebSocket support
- Plugin system for extensibility
- Power, thermal, safety, security, and WCET analysis modules
- Digital twin engine for real-time hardware mirroring
- Android and iOS embedded subsystem simulation
- CARLA, AirSim, ROS 2, Verilator, MATLAB engine integrations
- Docker production deployment with Kubernetes support
- Comprehensive CI/CD pipeline (GitHub Actions)

— *Srikanth Patchava, April 2026*

\newpage

# Part I: Fundamentals

## Chapter 1: Introduction

### 1.1 What is EoSim?

EoSim is a multi-architecture embedded simulation platform that enables developers to simulate, validate, and test embedded systems before hardware is ready. It supports 150+ platforms across 26 CPU architectures and 40 industry domains.

### 1.2 Key Metrics

| Metric | v1.0 | v2.0 |
|--------|------|------|
| Platform Definitions | 52 | **150+** |
| CPU Architectures | 12 | **26** |
| Industry Domains | 15 | **40** |
| Domain Simulators | 19 | **51** |
| Product Templates | 31 | **87+** |
| Peripheral Models | 40 | **100+** |
| Engine Backends | 4 | **10** |
| GUI Renderers | 13 | **33** |
| Modeling Methods | 10 | **20** |

### 1.3 Comparison with Industry Tools

| Feature | EoSim | Simics | Simulink | dSPACE | CANoe |
|---------|-------|--------|----------|--------|-------|
| Open Source | Yes | No | No | No | No |
| Platforms | 150+ | ~50 | N/A | ~20 | ~10 |
| Architectures | 26 | ~15 | N/A | ARM | CAN |
| Domains | 40 | ~5 | ~10 | Auto | Auto |
| Python API | Yes | No | MATLAB | No | CAPL |
| REST API | Yes | No | No | No | No |
| CI/CD Native | Yes | Limited | No | No | No |
| Plugin System | Yes | No | Blocksets | No | No |
| Digital Twin | Yes | No | Yes | Yes | No |
| Price | Free | $$$$$ | $$$$$ | $$$$$ | $$$$ |

### 1.4 Architecture Overview

```
                    ┌─────────────────────────────────────┐
                    │          CLI / REST API / GUI         │
                    └─────────────┬───────────────────────┘
                                  │
            ┌─────────────────────┼─────────────────────┐
            │              Core Engine                    │
            │  Schema │ Domains │ Registry │ Platforms    │
            │  40 domains, 26 arches, 150+ platforms      │
            └─────────────────────┼─────────────────────┘
                                  │
    ┌─────────────────────────────┼─────────────────────────┐
    │                    Simulators (51)                      │
    │  Vehicle │ Drone │ Medical │ Nuclear │ Railway │ ...    │
    │  Android │ iOS │ Quantum │ AR/VR │ Maritime │ ...      │
    └─────────────────────────────┼─────────────────────────┘
                                  │
    ┌─────────────────────────────┼─────────────────────────┐
    │              Peripherals (100+)                        │
    │  Sensors │ Actuators │ Buses │ Wireless │ Composites   │
    └─────────────────────────────┼─────────────────────────┘
                                  │
    ┌─────────────────────────────┼─────────────────────────┐
    │              Engine Backends (10)                       │
    │  EoSim │ QEMU │ Renode │ CARLA │ AirSim │ ROS2 │ ... │
    └───────────────────────────────────────────────────────┘
```

\newpage

## Chapter 2: Installation & Quick Start

### 2.1 Installation

```bash
# Basic install
pip install git+https://github.com/embeddedos-org/eosim.git

# With all optional dependencies (API, visualization, HIL)
pip install "eosim[all]"

# Development install
git clone https://github.com/embeddedos-org/eosim.git
cd eosim && pip install -e ".[dev]"

# Docker
docker pull ghcr.io/embeddedos-org/eosim:v2.0.0
```

### 2.2 Quick Start

```bash
eosim list                          # 150+ platforms
eosim list --domain automotive      # Filter by domain
eosim info stm32h7                  # Platform details
eosim run stm32f4                   # Run simulation
eosim test arm64-linux              # Validation tests
eosim gui stm32f4                   # GUI dashboard
eosim stats                         # Registry statistics
eosim doctor                        # Health check
```

### 2.3 Python API Quick Start

```python
from eosim.engine.native.simulators import SimulatorFactory

class VM:
    peripherals = {}
    def add_peripheral(self, name, dev):
        self.peripherals[name] = dev

vm = VM()
sim = SimulatorFactory.create('automotive_ecu', vm)
sim.load_scenario('highway_cruise')

for _ in range(1000):
    sim.tick()

state = sim.get_state()
print(f"Speed: {state['speed_kmh']} km/h")
print(f"RPM: {state['rpm']}")
print(f"Battery: {state['soc_pct']}%")
```

\newpage

# Part II: Platforms & Architectures

## Chapter 3: Supported Architectures (26)

| Architecture | Bits | Vendors | Platforms |
|-------------|------|---------|-----------|
| ARM (Cortex-M/A/R) | 32/64 | STM, NXP, Nordic, TI, Renesas | 50+ |
| RISC-V | 32/64 | SiFive, Espressif, StarFive, Allwinner | 15+ |
| x86_64 | 64 | Intel, AMD | 5 |
| Xtensa | 32 | Espressif | 3 |
| AVR | 8 | Microchip | 3 |
| MIPS/MIPSEL | 32/64 | MediaTek, Microchip, Cavium | 4 |
| TriCore | 32 | Infineon | 2 |
| PowerPC | 32/64 | NXP | 1 |
| PIC | 8/16 | Microchip | 1 |
| MSP430 | 16 | Texas Instruments | 1 |
| RX | 32 | Renesas | 2 |
| MicroBlaze | 32 | AMD/Xilinx | 1 |
| ARC | 32 | Synopsys | 1 |

## Chapter 4: Platform Catalog (150+)

### 4.1 Microchip/Atmel (8 platforms)
ATmega328P, ATmega2560, PIC32MX, SAMD21, SAME70, PIC18F, ATtiny85, SAML21

### 4.2 Texas Instruments (8 platforms)
MSP430, CC2652, CC3220, AM62x, TDA4VM, TMS320, OMAP-L138, MSP432

### 4.3 STMicroelectronics (5 platforms)
STM32F4, STM32H7, STM32L4, STM32MP1, STM32H743

### 4.4 Nordic Semiconductor (3 platforms)
nRF52840, nRF5340, nRF9160

### 4.5 Espressif (3 platforms)
ESP32, ESP32-S3, ESP32-C3

### 4.6 NXP (8 platforms)
S32K344, LPC55S69, i.MX RT1060, S32G274A, LPC4088, MCXN947, S32Z, K64F

### 4.7 Renesas (8 platforms)
RA4M1, RX65N, RL78, R-Car H3, R-Car S4, RZ/A2M, RA6M5, RH850

### 4.8 Silicon Labs (4 platforms)
EFM32GG, EFR32BG22, EFR32MG24, Si7021

### 4.9 FPGA (6 platforms)
Lattice iCE40, Xilinx Zynq-7020, Intel Cyclone V, Xilinx Versal, Lattice ECP5, Gowin GW1N

### 4.10 AI Accelerators (6 platforms)
Google Coral, Intel Movidius, Hailo-8, Mythic AMP, ARM Ethos-U55, Kneron KL520

### 4.11 Application Processors (8 platforms)
Apple M1, Qualcomm QCS610, MediaTek MT7688, Samsung Exynos Auto V9, Allwinner D1, Milk-V Duo, StarFive JH7110, Canaan K510

### 4.12 Automotive (8 platforms)
NXP S32G, Renesas R-Car S4, TI TDA4VM, Xilinx Versal Auto, Infineon TC4xx, AURIX TC3xx, Renesas RH850, onsemi RSL10

### 4.13 Raspberry Pi (5 platforms)
Pi 2B, Pi 3, Pi 4, Pi 5, Pi Zero 2W

### 4.14 Consumer/Gaming (6 platforms)
Roku TV, Amazon Fire TV, Apple TV, PS5, Nintendo Switch, Steam Deck

### 4.15 Network/Telecom (6 platforms)
MikroTik RouterBOARD, Ubiquiti EdgeRouter, Cisco Catalyst, Nokia AirScale, Ericsson Baseband, Huawei Kunpeng

### 4.16 RISC-V (7 platforms)
SiFive FU740, GD32VF103, Kendryte K210, BL602, BL706, CH32V307, StarFive JH7110

### 4.17 Specialty Simulators (13 platforms)
Agriculture, Maritime, Mining, Railway, Smart City, Nuclear, Construction, Logistics, Aerodynamics, Finance, Gaming, Physiology, Weather

\newpage

# Part III: Industry Domains

## Chapter 5: Domain Catalog (40 Domains)

### 5.1 Safety-Critical Domains

| Domain | Standard | Safety Level |
|--------|----------|-------------|
| Automotive | ISO 26262 | ASIL-A to ASIL-D |
| Aerospace | DO-178C | DAL-A to DAL-E |
| Nuclear | IEC 61513 | SIL-3 to SIL-4 |
| Railway | EN 50128/50129 | SIL-3 to SIL-4 |
| Medical | IEC 62304 | Class A to Class C |
| Industrial | IEC 61508 | SIL-1 to SIL-4 |
| Oil & Gas | API 1164 | SIL-2 to SIL-3 |
| Elevator | EN 81-20 | SIL-3 |
| Defense | MIL-STD-810 | SIL-3 to SIL-4 |

### 5.2 Consumer & IoT Domains
Consumer, IoT, Smart City, HVAC, Retail, Education, Sports, AR/VR, Gaming

### 5.3 Industrial Domains
Mining, Construction, Agriculture, Maritime, Forestry, Fisheries, Logistics, Water, Printing, Traffic

### 5.4 Technology Domains
Telecom (5G), Cybersecurity, Quantum, Photonics, Neuromorphic, Energy, Space

## Chapter 6: Domain Simulators (51)

Each simulator provides:
- `PRODUCT_TYPE` — unique identifier
- `DISPLAY_NAME` — human-readable name
- `SCENARIOS` — 3-8 named test scenarios
- `setup()` — peripheral initialization
- `tick()` — physics-based state update
- `load_scenario()` — load a named scenario
- `get_state()` — return current state dict

### 6.1 Simulator List

| # | Simulator | Domain | Key State Variables |
|---|-----------|--------|-------------------|
| 1 | VehicleSimulator | automotive | speed, rpm, steering, soc |
| 2 | DroneSimulator | robotics | altitude, attitude, battery |
| 3 | RobotSimulator | robotics | joints, torque, position |
| 4 | AircraftSimulator | aerospace | altitude, airspeed, attitude |
| 5 | SatelliteSimulator | aerospace | orbit, attitude, power |
| 6 | MedicalSimulator | medical | heart rate, SpO2, alarms |
| 7 | IndustrialSimulator | industrial | PLC state, modbus, safety |
| 8 | IoTSimulator | iot | sensors, MQTT, battery |
| 9 | EnergySimulator | energy | solar, battery, grid |
| 10 | WearableSimulator | consumer | steps, heart rate, BLE |
| 11-19 | Media/Speaker/Camera/Aero/Physio/Finance/Weather/Gaming | various | domain-specific |
| 20 | TelecomSimulator | telecom | frequency, throughput, SNR |
| 21 | DefenseSimulator | defense | radar, encryption, threat |
| 22 | SubmarineSimulator | defense | depth, sonar, buoyancy |
| 23 | NetworkSimulator | telecom | packets/sec, routing, CPU |
| 24 | SmartCitySimulator | smart-city | traffic, parking, air quality |
| 25 | RailwaySimulator | railway | speed, signal, doors |
| 26 | AgricultureSimulator | agriculture | soil moisture, irrigation, pH |
| 27 | MaritimeSimulator | maritime | heading, speed, wave height |
| 28 | MiningSimulator | mining | drill depth, gas, conveyor |
| 29 | ConstructionSimulator | construction | boom angle, load, hydraulics |
| 30 | RetailSimulator | retail | transactions, items, revenue |
| 31 | EducationSimulator | education | experiment, data points, score |
| 32 | NuclearSimulator | nuclear | reactor power, coolant temp, neutron flux |
| 33 | RoverSimulator | space | position, battery, solar power |
| 34 | LaunchVehicleSimulator | space | altitude, velocity, fuel, thrust |
| 35 | SmartGridSimulator | energy | frequency, voltage, load |
| 36 | PrinterSimulator | printing | nozzle temp, layer, progress |
| 37 | HVACSimulator | hvac | room temp, target, fan speed |
| 38 | ElevatorSimulator | elevator | floor, direction, doors, load |
| 39 | TrafficSimulator | traffic | phase, green time, vehicles/min |
| 40 | WaterSimulator | water | flow rate, pH, chlorine, tank |
| 41 | OilGasSimulator | oil-gas | flow, pressure, valve, ESD |
| 42 | LogisticsSimulator | logistics | items, conveyor speed, throughput |
| 43 | ARVRSimulator | ar-vr | head position/rotation, FPS, tracking |
| 44 | CybersecuritySimulator | cybersecurity | threats, packets, rules, CPU |
| 45 | QuantumSimulator | quantum | qubits, coherence, gate fidelity |
| 46 | SportsSimulator | sports | speed, heart rate, distance |
| 47 | ForestrySimulator | forestry | temperature, smoke, fire risk |
| 48 | FisheriesSimulator | fisheries | water temp, oxygen, fish count |
| 49 | V2XSimulator | automotive | message rate, latency, range |
| 50 | AndroidSimulator | consumer | sensors, battery, camera, connectivity |
| 51 | IOSSimulator | consumer | CoreMotion, Face ID, Taptic, UWB |

\newpage

# Part IV: Peripherals

## Chapter 7: Peripheral Models (100+)

### 7.1 Sensors (35+)

**Core sensors**: Temperature, Pressure, IMU, GPS, Proximity, Light, ADC, Current, ECG, SpO2

**Environment sensors**: Humidity, SoilMoisture, pH, Gas (CO2/O2/CH4), WaterLevel, UV, NoiseLevel

**Industrial sensors**: LoadCell, FlowSensor, VibrationSensor, TorqueSensor, StrainGauge, LevelSensor

**Navigation sensors**: Radar, LiDAR, DepthSounder, Sonar, Compass

**Imaging sensors**: Camera, ThermalCamera, InfraredSensor, XRaySensor

### 7.2 Actuators (15+)

**Motion**: MotorController, SteeringActuator, ServoController, ESCController, ThrottleActuator, BrakeActuator

**Industrial**: ConveyorBelt, CraneController, DrillMotor, PrintHead, Extruder

**Environment**: IrrigationValve, FanController, HeaterElement, Compressor, Damper

### 7.3 Buses (20+)

**Automotive**: CAN, LIN, FlexRay, ARINC 429

**Industrial**: EtherCAT, PROFINET, Modbus TCP, OPC UA, HART

**Network**: Ethernet MAC, USB, PCIe, HDMI, I2S

### 7.4 Wireless (15+)

**Short Range**: BLE, WiFi, Zigbee, NFC, UWB, Thread, Matter

**Long Range**: LoRa, LTE Cat-M1, NB-IoT, Satellite

### 7.5 Composites (10+)

BatteryManagement, WatchdogTimer, NPUAccelerator, GPUCompute, FPGAFabric, SecureElement, TPMModule, PowerManager

\newpage

# Part V: Engines & Integrations

## Chapter 8: Simulation Engines (10)

| Engine | Protocol | External Tool | Use Case |
|--------|----------|---------------|----------|
| EoSim Native | Internal | — | Fast CI, prototyping |
| QEMU | QMP + GDB | QEMU | Binary emulation |
| QEMU Live | QMP + GDB | QEMU | Interactive debugging |
| Renode | Telnet | Renode | Deterministic sim |
| X-Plane | UDP | X-Plane | Flight simulation |
| Gazebo | TCP | Gazebo | Robot simulation |
| OpenFOAM | subprocess | OpenFOAM | CFD |
| CARLA | TCP | CARLA | Autonomous driving |
| AirSim | msgpack-RPC | AirSim | Drone/car sim |
| ROS 2 | rclpy | ROS 2 | Robot framework |

## Chapter 9: Integration Bridges (7)

| Bridge | Purpose |
|--------|---------|
| `carla.py` | CARLA TCP client for autonomous driving |
| `airsim.py` | AirSim API for drone/car simulation |
| `ros2.py` | ROS 2 rclpy node bridge |
| `verilator.py` | Verilator VCD/FST trace reader |
| `matlab.py` | MATLAB Engine API for Simulink |
| `ns3.py` | ns-3 network simulator |
| `docker_sim.py` | Docker container simulation runner |

\newpage

# Part VI: Analysis & Advanced Features

## Chapter 10: Power Analysis

Estimate power consumption and battery life:

```python
from eosim.analysis.power import PowerAnalyzer, PowerProfile

analyzer = PowerAnalyzer()
analyzer.add_profile('nrf52', PowerProfile(
    voltage_v=3.3, current_active_ma=5.0,
    current_sleep_ma=0.002, current_deep_sleep_ua=0.4))

hours = analyzer.estimate_battery_life('nrf52',
    capacity_mah=250, duty_cycle_pct=1)
# → ~4,995 hours (208 days)
```

## Chapter 11: Thermal Modeling

Predict junction temperature and thermal throttling:

```python
from eosim.analysis.thermal import ThermalModel

model = ThermalModel(ambient_c=25.0, thermal_resistance_cw=15.0)
steady_state = model.steady_state(power_w=2.0)  # → 55.0°C
time_to_85c = model.time_to_limit(power_w=3.0, limit_c=85.0)
```

## Chapter 12: Functional Safety

Track ISO 26262 / IEC 61508 requirements:

```python
from eosim.analysis.safety import SafetyAnalyzer, SafetyRequirement

sa = SafetyAnalyzer()
sa.add_requirement(SafetyRequirement(
    req_id='SWR-001', standard='ISO 26262', level='ASIL-D',
    description='Watchdog reset within 100ms'))
sa.verify('SWR-001')
print(sa.report())  # coverage %, verified/unverified
```

## Chapter 13: Security Analysis

ISO 21434 threat modeling and risk scoring:

```python
from eosim.analysis.security import SecurityAnalyzer, ThreatModel

sa = SecurityAnalyzer()
sa.add_threat(ThreatModel(
    asset='ECU firmware', threat='Debug port tampering',
    impact='critical', likelihood='medium'))
sa.mitigate('ECU firmware', 'Disable JTAG, enable secure boot')
print(f"Risk score: {sa.risk_score()}")
```

## Chapter 14: WCET Analysis

Worst-case execution time and schedulability:

```python
from eosim.analysis.timing import WCETAnalyzer

wa = WCETAnalyzer(clock_mhz=168)
wa.add_task('sensor_read', cycles=5000, period_us=1000)
wa.add_task('can_tx', cycles=2000, period_us=500)
report = wa.report()
print(f"Utilization: {report['utilization']*100:.1f}%")
print(f"Schedulable: {report['schedulable']}")
```

## Chapter 15: Digital Twin

Real-time hardware mirroring and predictive simulation:

```python
from eosim.digital_twin.twin import DigitalTwin

twin = DigitalTwin('engine_ecu', simulator)
twin.sync()                        # Mirror current state
predictions = twin.predict(100)    # Predict 100 steps ahead
twin.export_json('twin_data.json') # Export history
```

## Chapter 16: Code Generation

Generate C driver stubs from simulation models:

```python
from eosim.codegen.generator import CodeGenerator

gen = CodeGenerator(output_dir='generated/')
files = gen.generate_peripheral_driver(temp_sensor)
gen.write_files({'temp0.h': files['header'], 'temp0.c': files['source']})
```

\newpage

# Part VII: REST API & Plugins

## Chapter 17: REST API

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/platforms` | List platforms |
| GET | `/api/v1/domains` | List domains |
| GET | `/api/v1/simulators` | List simulators |
| GET | `/api/v1/templates` | List product templates |
| GET | `/api/v1/simulations/{name}/state` | Get state |
| POST | `/api/v1/simulations/{name}/tick` | Advance tick |
| POST | `/api/v1/simulations/{name}/reset` | Reset |
| WS | `/ws/simulations/{name}` | Real-time stream |

### Starting the Server

```bash
pip install "eosim[api]"
python -m eosim.api.server
# → http://localhost:8080/docs (Swagger UI)
```

## Chapter 18: Plugin System

```python
from eosim.plugins.base import PluginBase

class DataLoggerPlugin(PluginBase):
    NAME = "data-logger"
    VERSION = "1.0.0"

    def on_load(self):
        self.log = []

    def on_tick(self, simulator, state):
        self.log.append(state)

    def on_unload(self):
        # Save log to file
        pass
```

\newpage

# Part VIII: Mobile Simulation

## Chapter 19: Android Simulation

EoSim simulates Android's **embedded hardware subsystems** — not the full OS:

| Subsystem | What's Simulated |
|-----------|-----------------|
| Sensor HAL | Accelerometer, gyro, mag, GPS, light, proximity |
| Power PMIC | Battery drain/charge, doze/deep sleep modes |
| Touch IC | Multi-touch events, gesture recognition |
| Camera ISP | Preview → capture → encode pipeline |
| Display DDIC | Brightness, refresh rate (120 Hz), FPS |
| Modem | Cellular signal, 5G/LTE registration |
| Wireless | WiFi, BLE, NFC controllers |
| OTA | Firmware update lifecycle |

**8 scenarios**: boot_sequence, sensor_polling, camera_capture, power_management, touch_interaction, connectivity_cycle, telephony_call, ota_update

## Chapter 20: iOS Simulation

| Subsystem | What's Simulated |
|-----------|-----------------|
| CoreMotion | IMU + barometer → attitude estimation |
| Face ID | TrueDepth → IR projector → secure enclave |
| Taptic Engine | Haptic patterns (peek, pop, success, error) |
| Camera ISP | RAW → Deep Fusion → Smart HDR → HEIF |
| Secure Enclave | Key ops, Face ID verification |
| UWB (U1) | Ultra-wideband ranging (AirTag) |
| NFC | Apple Pay: tap → secure element → auth |
| ProMotion | Adaptive 120 Hz, always-on display |

**8 scenarios**: boot_sequence, face_id_unlock, haptic_feedback, camera_pipeline, power_management, uwb_ranging, nfc_payment, sensor_fusion

\newpage

# Part IX: Deployment

## Chapter 21: Docker Deployment

### Docker Images

| Target | Size | Purpose |
|--------|------|---------|
| `production` | ~180 MB | Slim CLI (no QEMU) |
| `api-server` | ~200 MB | REST API (FastAPI) |
| `production-qemu` | ~800 MB | Full QEMU simulation |
| `development` | ~1.2 GB | Dev environment |

```bash
docker compose up api -d
curl http://localhost:8080/api/v1/platforms
```

## Chapter 22: CI/CD Pipeline

### GitHub Actions Workflows

| Workflow | Trigger | Jobs |
|----------|---------|------|
| `ci.yml` | Push/PR | Lint, test (4 Python), coverage, platforms, smoke, docs, security, build |
| `pr-check.yml` | PR | Quick check, coverage gate, smoke |
| `nightly.yml` | Daily 2AM | 12-matrix test, coverage, validation, report |
| `weekly.yml` | Monday 6AM | Full matrix, deep coverage, audit, docs check |
| `release.yml` | Tag v* | Validate, build, docs, Docker, release, PyPI |

## Chapter 23: Production Checklist

- [ ] All 150+ platforms validate (`eosim validate --all`)
- [ ] All 180+ simulator map entries smoke test
- [ ] Test coverage ≥ 70%
- [ ] Docker image builds and health check passes
- [ ] API server responds to `/api/v1/platforms`
- [ ] Documentation builds (Doxygen HTML + PDF)
- [ ] Security scan clean (pip-audit)
- [ ] CI pipeline green on all 12 matrix combinations

\newpage

# Appendices

## Appendix A: Standards Compliance

ISO 26262, IEC 61508, DO-178C, IEC 62304, ISO 21434, FIPS 140-3, EN 50128/50129, IEC 61513, IEEE 603, ECSS-E-ST-40C, ISO 11783, IMO SOLAS, IEC 60079, EN 81-20, NTCIP

## Appendix B: Glossary

| Term | Definition |
|------|-----------|
| ASIL | Automotive Safety Integrity Level (ISO 26262) |
| SIL | Safety Integrity Level (IEC 61508) |
| DAL | Design Assurance Level (DO-178C) |
| HAL | Hardware Abstraction Layer |
| PMIC | Power Management Integrated Circuit |
| ISP | Image Signal Processor |
| UWB | Ultra-Wideband |
| WCET | Worst-Case Execution Time |
| V2X | Vehicle-to-Everything communication |
| HSM | Hardware Security Module |
| PTC | Positive Train Control |
| SCADA | Supervisory Control and Data Acquisition |
| RTU | Remote Terminal Unit |
| PLC | Programmable Logic Controller |

## Appendix C: References

---

*EoSim v2.0.0 — World-Class Embedded Simulation Platform Reference Guide*

*Copyright (c) 2026 EmbeddedOS Organization. MIT License.*

*Part of the [EmbeddedOS Organization](https://embeddedos-org.github.io).*
