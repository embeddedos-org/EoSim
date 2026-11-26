# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **`esp32-qemu` platform: run an ESP32 flash image in Espressif's QEMU.** The `esp32` machine (from Espressif's QEMU fork; upstream QEMU has none) runs the ESP32 boot ROM, which loads the image from flash as a board does. Two additions to `eosim run` make that usable. A platform's `qemu.firmware_drive` is a `-drive` template; with it `--firmware` is attached as that drive instead of `-kernel`, and commas in the path are doubled (QEMU's escape), so a path cannot add drive options. `--expect TEXT` requires the guest to print TEXT: firmware that never exits, such as an RTOS image, passes on timeout only if it did, and a clean exit without it fails. Without `--expect` a timeout is still a failure. Checked end to end with the EoS ESP32 scheduler image (eos `sim/qemu_esp32`): `eosim run esp32-qemu --firmware sched.flash.bin --expect "SCHEDULER TEST PASSED"` passed, and the same command on an image that prints `SCHEDULER TEST FAILED` exited 1. The machine fixes its CPU and supports at most 4 MB of RAM, so the platform sets neither `cpu` nor more memory.
- **`eosim run` finds Espressif's QEMU where Espressif installs it.** `idf_tools.py install qemu-xtensa` (and ESP-IDF's installer) unpack the QEMU fork to `~/.espressif/tools/qemu-xtensa/<version>/qemu/bin` and do not add it to PATH, so `eosim run esp32-qemu` reported `QEMU NOT INSTALLED` (exit 2) on a machine that had it. A QEMU binary missing from PATH is now looked for under `$IDF_TOOLS_PATH` (default `~/.espressif`)`/tools/qemu-*/*/qemu/bin`; PATH still wins, of several installed versions the highest wins, a `~` in `IDF_TOOLS_PATH` is expanded, and the Windows build's `.exe` name is matched. When it is missing everywhere, an `esp32*` machine's hint names Espressif's installer and the directory searched instead of `sudo apt install`, whose upstream QEMU has no `esp32` machine.

### Changed
- **MCP failed tool calls carry `isError`:** a `tools/call` that fails (unknown tool, arguments rejected by the schema, or a tool that returns `ok: false`) now sets `isError: true` on its result, so MCP clients can tell a failed call from a successful one. The JSON text in `content` is unchanged. (#53)
- **MCP tool arguments are validated against the published `inputSchema`:** types, ranges, string lengths, enums, required fields and unknown fields are checked before a tool runs, and a call outside the schema returns an error naming the field. Arguments that are not a JSON object (including `[]`, `false`, `0` and `""`) are rejected; only missing arguments count as `{}`. Whole numbers such as `200.0` are accepted for integer fields, as JSON Schema allows, and reach the tool as integers. (#53)

### Fixed
- **`eosim ecosystem` no longer calls a partly skipped sweep `PASSED`.** `EcosystemReport.summary()` printed `VERDICT: PASSED (N repo(s) skipped — see above)` whenever at least one repo passed and the rest were skipped, so a run that tested 8 of 19 repositories headlined as a pass — and that headline is the line that gets pasted into a status update. A skipped repo was not tested, and `PASSED` is now reserved for a run in which everything discovered actually ran; the partial case reads `INCOMPLETE (N repo(s) skipped — see above)`. The fully skipped case already read `NOTHING WAS TESTED` and is unchanged, as are `ALL PASSED` and `FAILURES DETECTED`. **The exit code is deliberately not changed by this commit:** `eosim ecosystem` still exits 0 unless `repos_failed > 0`, so no existing CI gate changes behaviour. Making a skipped repo able to fail a gate needs a `--strict`/`--require` decision on the command's interface and is not settled here.

- **Traffic controller never authorises conflicting approaches, and its scenarios act:** `tick()` recomputed the phase from the cycle position *after* `_apply_scenario()` had set its inputs, so every scenario input was discarded in the same tick, and emergency pre-emption published `green_all` — green on all four approaches at once — on 20 of 30 ticks. The free-running cycle reached only `{green_ns, yellow_ns, green_ew}`: no `yellow_ew` and no `all_red`. Phase resolution now has a single owner, with an explicit per-ring interval table (green → yellow → all-red) parameterised by `yellow_time_s` and `all_red_time_s`. Pre-emption walks every conflicting movement through yellow and all-red before releasing green to one ring alone; the pedestrian interlude is served from the all-red step; a controller fault shows flashing yellow/red. State publishes a per-approach signal map beside the phase name, plus `conflicting_greens()`. Swept over every scenario, 600 ticks each: 0 violations. (#106, #107)

- **Traffic clearance intervals are never skipped or shortened:** re-targeting pre-emption while a ring already held green put the new ring straight to green and dropped the old one from green to red with no yellow and no all-red; pre-emption arriving during a normal yellow skipped the rest of that yellow; and cancelling a request during the pre-emption yellow dropped the rest of it. The active stage now tracks which ring it belongs to and restarts clearance when the target changes (a repeat request for the same ring keeps its progress), and recovery is based on the clearance that was running rather than only on which ring holds a green.

- **Traffic scenarios hand back the inputs they drive:** `load_scenario()` changed only the scenario name, so a previous scenario's inputs kept steering the controller — one tick of `fault_mode` latched `fault_active` and published `flash_yellow` forever, leaving `emergency_vehicle` before its step 20 stranded `emergency_override`, and `rush_hour` stranded its extended `green_time_s`. Scenarios now record the inputs they write and restore them on a scenario change, leaving inputs a caller set independently alone.

- **`net_capture` reads no ports from a later IPv4 fragment:** only the first fragment of a datagram carries the TCP/UDP header, but `_parse_ip()` took bytes at the header offset from every fragment, so the first four payload bytes of a later fragment were reported as source and destination ports. A fragment carrying `12 34 56 78` there was summarised as `4660 -> 22136`, and those invented ports also split the flow into two `top_talkers` entries. A fragment with a non-zero offset is now summarised as `<proto> fragment offset=<n>` with no ports, and is attributed to the bare address pair.

- **Medical monitor reports its highest-priority alarm:** `MedicalSimulator._evaluate_alarms()` gave each alarm a priority but stopped at the first condition in a fixed order, so a lower-priority alarm hid a higher one: a heart rate of 130 bpm (`HR_ABNORMAL`, priority 2) masked an SpO2 of 80 % (`SPO2_CRITICAL`, priority 3), and a disconnected SpO2 probe (`SENSOR_DISCONNECT`, 2) masked an occluded IV pump (`PUMP_OCCLUSION`, 3). Every active condition is now collected and the one with the highest priority is reported; equal priorities keep the old order.

- **Native pulse oximeter keeps its pulse rate:** `PulseOximeter.simulate_tick()` added zero-mean noise to the pulse rate and then truncated it with `int()`, which rounds toward zero, so every negative sample cost a whole beat while small positive ones were dropped. The rate sank from 72 bpm to the 40 bpm floor within about 100 ticks, and the wearable simulator showed that falling heart rate. The rate is now rounded to the nearest beat.

- **GDB client reads the AArch64 `cpsr`:** the `g` reply gives `x0`-`x30`, `sp` and `pc` 8 bytes each but `cpsr` only 4 (it is 32-bit in `aarch64-core.xml`), while `GDBRemoteClient` took 8 bytes for every register, so `read_all_registers()` stopped before `cpsr` and the live CPU view never updated it. Registers now carry their own sizes, and `write_register()` sends `cpsr` as 4 bytes.

- **HIL serial bridge keeps non-ASCII text intact:** `SerialBridge` decoded every read from the port on its own, so a UTF-8 character whose bytes arrived in two reads (for example when the line was idle, the blocking `read(1)` returns only the first byte) reached the UART terminal as two or more `U+FFFD` replacement characters: `°C` became `��C`. The read loop now uses one incremental decoder for the whole stream.

- **OpenOCD target scripts for `samd21` and `k64f`:** `samd21` (SAM D21, Cortex-M0+) pointed at `target/atsame5x.cfg`, the SAM D5x/E5x script, whose `atsame5` flash driver only knows Cortex-M4 parts, so `eosim hil flash --target samd21` could not probe the chip. `k64f` (Kinetis K64, Cortex-M4) pointed at `target/klx.cfg`, the Cortex-M0+ Kinetis KL script. They now use `target/at91samdXX.cfg` and `target/kx.cfg`.

- **Native engine `B` lands on its target:** the ARM `B` decoder added `imm24 * 4` to the address of the branch instead of the address + 8, so every branch landed 4 bytes short, and a backward branch sign-extended into a 34-bit offset, so `B .` and every loop jumped far outside memory. The target is now (the address of the `B` + 8 + `imm24 * 4`) mod 2^32, so a branch to address 0 also lands on 0.

- **Native engine runs the image it was given:** `VirtualMachine.load_firmware()` and `load_binary()` added the image as a new memory region, but the memory bus reads the first region by base address that contains an address, so the image was never read when its base lay inside an existing region: in the flash that `flash_mb` maps at `0x08000000`, anywhere in RAM, or over an image loaded earlier. The CPU then executed blank memory as NOPs (or the old image). An image that fits in an existing RAM or flash region is now written into it, and an earlier image that the new one overlaps is replaced.

- **`eosim test` runs the simulation:** it previously printed every check in `tests.yml` and reported "N/N passed" without running anything. It now runs the platform engine, evaluates each check against the result, prints PASS/FAIL per check, and exits 1 if any check fails.

- **Release Docker image builds again:** the Dockerfile still copied `platforms/` from the repository root after the registry moved into `eosim/platforms`, so the v3.0.2 release failed at the image build (`"/platforms": not found`) and the GitHub Release and PyPI jobs never ran. The registry ships inside the wheel, so the stale copies are removed. The release smoke test now overrides the `eosim` entrypoint to run `python -c`.

- **Native ADC saturates at 0 and full scale:** `ADCChannel.set_voltage()` stored the converted code without the clamp that `set_channel()` applies, so a voltage below 0 mV gave a negative register value and one above the reference gave a code wider than the converter's resolution (5000 mV read 6204 on a 12-bit, 3300 mV channel). The energy simulator feeds its `solar_adc` noisy solar power, so at night it often read a negative code. Out-of-range voltages now read 0 or the maximum code.

- **Wearable workout scenario marks the workout active:** `WearableSimulator.load_scenario("workout_detection")` matched the first branch (`step_counting` or `workout_detection`), so the later `workout_detection` branch that sets `workout_active` and `workout_type` never ran: the scenario drove the IMU and heart rate like a workout but `get_state()` kept `workout_active: False` and an empty `workout_type`. Both are now set to `True` and `"running"`.

### Fixed
- **`/api/v1/platforms` and `/api/v1/metrics` no longer return 500:** both called `PlatformRegistry().discover()`, which does not exist. They now load the packaged platform registry that the CLI uses.

### Fixed
- **`eosim hil flash` honours `--adapter`/`--target` and firmware paths with spaces:** the adapter and target were never passed to OpenOCD (it ran with empty `-f ""` configs), and the firmware path was placed unquoted in the Tcl `program` command, which OpenOCD splits on whitespace. `OpenOCDManager.flash()` now accepts `adapter`/`target` and escapes the path as a single Tcl word.

### Fixed
- **`eosim eos test-suite` reports FAIL when pytest is missing or crashes:** the pytest result was PASS whenever no "N failed" count was parsed, so `No module named pytest`, collection errors, internal errors and "no tests ran" all passed, and the command always exited 0. The result now follows pytest's exit code, and the command exits 1 (printing the tail of the pytest output) when the suite fails.

### Fixed
- **`eosim run` keeps console output on timeout and fails:** on a Renode timeout it printed "saving log" but wrote no log, discarded the output captured so far and exited 0; on a QEMU timeout the log held only the command line. Both now write the partial stdout/stderr to the log, print it, and exit 1.

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
