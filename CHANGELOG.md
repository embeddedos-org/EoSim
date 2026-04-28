# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.0.0] — 2026-04-27

### Added — World-Class Enhancement Release

#### Architectures (+13)
- AVR, PIC, MSP430, SH, SPARC, M68K, CEVA, Tensilica, NIOS II, OpenRISC, LoongArch, RX

#### Domains (+25)
- Agriculture, Maritime, Mining, Construction, Retail, Education, Sports, Nuclear,
  Railway, Smart City, Space, Quantum, Photonics, Neuromorphic, HVAC, Printing,
  Elevator, Traffic, Water, Oil & Gas, Forestry, Fisheries, Logistics, Cybersecurity, AR/VR

#### Simulators (+30)
- TelecomSimulator, DefenseSimulator, SubmarineSimulator, NetworkSimulator,
  SmartCitySimulator, RailwaySimulator, AgricultureSimulator, MaritimeSimulator,
  MiningSimulator, ConstructionSimulator, RetailSimulator, EducationSimulator,
  NuclearSimulator, RoverSimulator, LaunchVehicleSimulator, SmartGridSimulator,
  PrinterSimulator, HVACSimulator, ElevatorSimulator, TrafficSimulator,
  WaterSimulator, OilGasSimulator, LogisticsSimulator, ARVRSimulator,
  CybersecuritySimulator, QuantumSimulator, SportsSimulator, ForestrySimulator,
  FisheriesSimulator, AutomotiveV2XSimulator

#### Platforms (+87)
- Microchip/Atmel (8), Texas Instruments (7), Silicon Labs (4), Renesas (6),
  NXP (6), Other MCU (10), FPGA (6), AI Accelerators (6), Application Processors (8),
  Automotive (6), Specialty Sim (8), Consumer (6), Network/Telecom (6)
- Total: 150+ platform definitions

#### Peripherals (+60)
- Environment sensors: Humidity, SoilMoisture, pH, Gas, WaterLevel, UV, NoiseLevel
- Industrial sensors: LoadCell, FlowSensor, VibrationSensor, TorqueSensor, StrainGauge, LevelSensor
- Navigation sensors: Radar, LiDAR, DepthSounder, Sonar, Compass
- Imaging sensors: Camera, ThermalCamera, InfraredSensor, XRaySensor
- Industrial actuators: ConveyorBelt, CraneController, DrillMotor, PrintHead, Extruder
- Environment actuators: IrrigationValve, FanController, HeaterElement, Compressor, Damper
- Industrial buses: EtherCAT, PROFINET, Modbus TCP, OPC UA, HART
- Network buses: Ethernet MAC, USB, PCIe, HDMI, I2S
- Extended wireless: NFC, UWB, Satellite, LTE Cat-M1, NB-IoT, Thread, Matter
- Advanced composites: NPU, GPU, FPGA, SecureElement, TPM, PowerManager

#### Engine Integrations (+7)
- CARLA autonomous driving bridge
- AirSim drone/car bridge
- ROS 2 node bridge
- Verilator VCD/FST trace reader
- MATLAB Engine API bridge
- ns-3 network simulator bridge
- Docker container-based simulation

#### REST API & Plugin System
- FastAPI REST server with Swagger/ReDoc
- WebSocket real-time state streaming
- Plugin discovery, loading, and lifecycle management
- Plugin base class with on_tick/on_load/on_unload hooks

#### Analysis Modules
- Power consumption modeling and battery life estimation
- Thermal simulation (lumped-parameter model)
- Functional safety (ISO 26262, IEC 61508) requirement tracking
- Security analysis (ISO 21434) threat modeling
- WCET analysis and schedulability check

#### Digital Twin
- Real-time state mirroring
- Predictive simulation (future state forecasting)
- Historical state recording and JSON export

#### Code Generation
- C code stub generation from peripheral models
- Header and source file generation

#### Network Topology
- Multi-node network simulation
- Node/link topology management

#### GUI Renderers (+20)
- Domain-specific 3D renderers for all new domains

#### Documentation
- Comprehensive README with 150+ platform catalog
- Doxygen configuration for HTML + PDF generation
- 9 new documentation guides: simulator, peripheral, domain, engine,
  analysis, plugin, REST API, digital twin, production deployment
- Production deployment guide (Docker, CI/CD, monitoring)

### Changed
- Version bumped to 2.0.0 (Production/Stable)
- Schema expanded: 26 architectures, 40 domains, 20 modeling methods, 25 platform classes
- SIMULATOR_MAP expanded from 38 to 170+ entries

### Added
- `.gitignore` with Python, IDE, and EoSim-specific patterns
- `Makefile` with standardized targets (test, lint, format, coverage, build, clean, docker)
- `CONTRIBUTING.md` with development workflow, code style, and PR process
- `CODE_OF_CONDUCT.md` (Contributor Covenant v2.1)
- GitHub Actions CI workflow (`ci.yml`) — Python 3.9-3.12 matrix, lint, test, coverage
- GitHub Actions nightly regression workflow (`nightly.yml`)
- GitHub Actions release workflow (`release.yml`) — PyPI publishing
- GitHub issue templates (bug report, feature request)
- GitHub pull request template with checklist
- `Dockerfile` with multi-stage build and QEMU pre-installed
- `docker-compose.yml` for containerized simulation
- `tests/conftest.py` with shared fixtures (sample platforms, registries, SimResults)
- Integration tests: platform pipeline, CLI commands, scenario runner
- Example READMEs for `examples/` and `examples/cluster-demo/`

### Changed
- Enhanced `pyproject.toml` with URLs, classifiers, authors, tool configs (pytest, coverage, ruff)
- Consolidated `pytest.ini` into `pyproject.toml` `[tool.pytest.ini_options]`
- Expanded `SECURITY.md` with supported versions, scope, and disclosure process

### Fixed
- `docs/architecture.md` — replaced corrupted PowerShell artifacts with proper Markdown

### Documentation
- `docs/getting-started.md` — step-by-step installation and first simulation tutorial
- `docs/api-reference.md` — complete Python API documentation with examples
- `docs/platform-authoring.md` — guide for creating new platform configurations
- `docs/hil-guide.md` — hardware-in-the-loop setup, wiring, and troubleshooting
- `docs/cli-reference.md` — full CLI command tree with options and examples

### Removed
- `pytest.ini` (consolidated into `pyproject.toml`)

## [0.1.0] - 2026-03-31

### Added
- Initial release of eosim
- Custom EoSim native simulation engine (zero external dependencies)
- Engine priority: EoSim native > Renode > dry-run
- Renode engine backend
- 41 platform configurations across 12 architectures
- CPU, memory, and 6 peripheral simulators (UART, GPIO, Timer, SPI, I2C, NVIC)
- pip-installable package with CLI (`eosim` command)
- GUI simulator with Tkinter-based 3D product renderers
- QEMU integration with QMP, GDB, ELF loader, and state bridge
- Hardware-in-the-loop (HIL) session management
- Complete CI/CD pipeline with nightly, weekly, EoSim sanity, and simulation test runs
- Full cross-platform support (Linux, Windows, macOS)
- ISO/IEC standards compliance documentation
- MIT license

[Unreleased]: https://github.com/embeddedos-org/eosim/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/embeddedos-org/eosim/releases/tag/v0.1.0
