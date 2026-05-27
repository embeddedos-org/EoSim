# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.0.1] - 2026-05-27

### Added — Production Release & Enhancements
- **Internationalization (i18n):** Support for 10 languages (English, Spanish, Mandarin, Hindi, French, Arabic, Portuguese, German, Japanese, Korean) with RTL support for Arabic.
- **Production API Configuration:** Defined unified production endpoints (`api.eosim.io`, `docs.eosim.io`, `status.eosim.io`) with automatic geo-location routing (US/EU/AP).
- **Browser Extension:** Manifest V3 extension for Chrome, Edge, and Firefox supporting real-time telemetry, 10-language UI, and global hotkeys.
- **Mobile PWA:** Progressive Web App with GPS-based regional routing, full offline mode, and 10-language support.
- **Native App Configurations:** Kotlin + Swift configs for Android & iOS with FaceID, ATS/Network security, and multi-language support.
- **Production-grade API Server:** FastAPI with full CORS limits, request tracking, Gzip compression, Swagger UI, and ReDoc.
- **DevOps Hardening:** Production Kubernetes Deployment manifests, enterprise Helm chart (v3.0.1), multi-stage Docker configurations, and a developer `Makefile`.
- **Testing:** Added 93 new unit tests covering i18n, production configuration, and mobile app models. All 1,612 tests passing with 75.08% code coverage.

## [3.0.0] - 2026-05-13

### Production Release — Unified EmbeddedOS-org v3.0.0
This is the synchronized production release across all 18 EmbeddedOS-org repos.
- Refreshed governance: LICENSE, NOTICE, CITATION.cff, SECURITY.md
- CI/CD pipelines hardened: release.yml, book-build.yml, video-build.yml, deploy-pages.yml
- Release artifacts produced for: Linux x64/arm64, macOS x64/arm64, Windows x64, Docker, plus per-repo embedded/mobile/extension targets
- mdBook documentation built and deployed to GitHub Pages
- Promo video rendered and attached as a release asset

## [2.0.0] — 2026-04-27

### Added — World-Class Enhancement Release
- **Architectures (+13):** AVR, PIC, MSP430, SH, SPARC, M68K, CEVA, Tensilica, NIOS II, OpenRISC, LoongArch, RX
- **Domains (+25):** Agriculture, Maritime, Mining, Construction, Retail, Education, Sports, Nuclear, Railway, Smart City, Space, Quantum, Photonics, Neuromorphic, HVAC, Printing, Elevator, Traffic, Water, Oil & Gas, Forestry, Fisheries, Logistics, Cybersecurity, AR/VR
- **Simulators (+30):** TelecomSimulator, DefenseSimulator, SubmarineSimulator, NetworkSimulator, SmartCitySimulator, RailwaySimulator, AgricultureSimulator, MaritimeSimulator, MiningSimulator, ConstructionSimulator, RetailSimulator, EducationSimulator, NuclearSimulator, RoverSimulator, LaunchVehicleSimulator, SmartGridSimulator, PrinterSimulator, HVACSimulator, ElevatorSimulator, TrafficSimulator, WaterSimulator, OilGasSimulator, LogisticsSimulator, ARVRSimulator, CybersecuritySimulator, QuantumSimulator, SportsSimulator, ForestrySimulator, FisheriesSimulator, AutomotiveV2XSimulator
- **Platforms (+87):** Microchip/Atmel (8), Texas Instruments (7), Silicon Labs (4), Renesas (6), NXP (6), Other MCU (10), FPGA (6), AI Accelerators (6), Application Processors (8), Automotive (6), Specialty Sim (8), Consumer (6), Network/Telecom (6). Total: 150+ platform definitions.
- **Peripherals (+60):** Environment sensors, Industrial sensors, Navigation sensors, Imaging sensors, Industrial actuators, Environment actuators, Industrial buses, Network buses, Extended wireless, Advanced composites.
- **Engine Integrations (+7):** CARLA, AirSim, ROS 2 node bridge, Verilator VCD/FST trace reader, MATLAB Engine API bridge, ns-3 network simulator bridge, Docker container-based simulation.
- **REST API & Plugin System:** FastAPI REST server with Swagger/ReDoc, WebSocket real-time state streaming, Plugin discovery and loading.
- **Analysis Modules:** Power consumption modeling, Thermal simulation, Functional safety (ISO 26262, IEC 61508), Security analysis (ISO 21434) threat modeling, WCET analysis.
- **Digital Twin:** Real-time state mirroring, Predictive simulation, Historical state recording and JSON export.
- **Code Generation:** C code stub generation from peripheral models.
- **Network Topology:** Multi-node network simulation.
- **GUI Renderers (+20):** Domain-specific 3D renderers for all new domains.
- **Documentation:** Comprehensive README with 150+ platform catalog, Doxygen configuration for HTML + PDF generation, 9 new documentation guides.
- **Infrastructure:** `.gitignore`, `Makefile`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, GitHub Actions CI workflow (`ci.yml`), GitHub Actions nightly regression workflow (`nightly.yml`), GitHub Actions release workflow (`release.yml`), GitHub issue templates, `Dockerfile`, `docker-compose.yml`, `tests/conftest.py` with shared fixtures.

### Changed
- Version bumped to 2.0.0 (Production/Stable)
- Schema expanded: 26 architectures, 40 domains, 20 modeling methods, 25 platform classes
- SIMULATOR_MAP expanded from 38 to 170+ entries

### Fixed
- `docs/architecture.md` — replaced corrupted PowerShell artifacts with proper Markdown

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

[Unreleased]: https://github.com/embeddedos-org/EoSim/compare/v3.0.1...HEAD
[3.0.1]: https://github.com/embeddedos-org/EoSim/releases/tag/v3.0.1
[3.0.0]: https://github.com/embeddedos-org/EoSim/releases/tag/v3.0.0
[2.0.0]: https://github.com/embeddedos-org/EoSim/releases/tag/v2.0.0
[0.1.0]: https://github.com/embeddedos-org/EoSim/releases/tag/v0.1.0
