---

# EoSim — Multi-Architecture Embedded Simulation Platform

## The Definitive Technical Reference

![Figure: EoSim System Architecture — simulation orchestration with QEMU and Renode](images/architecture.png)


**Version 1.0**

**Srikanth Patchava & EmbeddedOS Contributors**

**April 2026**

---

*Published as part of the EmbeddedOS Product Reference Series*

*MIT License — Copyright (c) 2026 EmbeddedOS Organization*

---

# Preface

EoSim is the simulation and validation platform for the EmbeddedOS ecosystem. In the embedded systems world, hardware availability is often the bottleneck for software development, testing, and validation. EoSim eliminates this bottleneck by providing high-fidelity simulation of 52+ platforms across 12 architectures, enabling developers to write, test, and validate embedded software before hardware is ready.

This reference book is intended for embedded systems engineers, firmware developers, QA engineers, and DevOps professionals who need to simulate, test, and validate embedded software across diverse hardware targets. Whether you are running a quick CI test against a Cortex-M4, performing full-system validation on a Raspberry Pi 4 simulation, or orchestrating cluster simulations for multi-node IoT deployments, this book provides the comprehensive technical depth required.

EoSim combines a native Python simulation engine with Renode [@renode_docs] integration, QEMU [@bellard2005] binary emulation, and hardware-in-the-loop (HIL [@herber2020]) support. It includes a GUI dashboard with GPIO visualization, UART terminal, CPU state panels, and 3D renderers. The platform is fully CI-native, with configuration-driven testing that integrates seamlessly into GitHub Actions, Jenkins, and other CI/CD systems.

The platform supports architectures from tiny Cortex-M0+ microcontrollers to powerful Cortex-A78AE application processors, RISC-V, Xtensa (ESP32), x86_64, MIPS, PowerPC, MicroBlaze, ARC, and specialty domain simulators for aerodynamics, finance, gaming, physiology, and weather.

— *Srikanth Patchava & EmbeddedOS Contributors, April 2026*

---

# Table of Contents

1. [Introduction](#chapter-1-introduction)
2. [Getting Started](#chapter-2-getting-started)
3. [System Architecture](#chapter-3-system-architecture)
4. [CLI Reference](#chapter-4-cli-reference)
5. [Platform Registry](#chapter-5-platform-registry)
6. [Supported Platforms](#chapter-6-supported-platforms)
7. [Simulation Engines](#chapter-7-simulation-engines)
8. [Platform Definition Format](#chapter-8-platform-definition-format)
9. [Native Simulation Engine](#chapter-9-native-simulation-engine)
10. [Renode Integration](#chapter-10-renode-integration)
11. [QEMU Integration](#chapter-11-qemu-integration)
12. [Hardware-in-the-Loop (HIL)](#chapter-12-hardware-in-the-loop)
13. [GUI Dashboard](#chapter-13-gui-dashboard)
14. [Peripheral Simulation](#chapter-14-peripheral-simulation)
15. [CPU Simulation & State Bridge](#chapter-15-cpu-simulation--state-bridge)
16. [Cluster Simulation](#chapter-16-cluster-simulation)
17. [CI/CD Integration](#chapter-17-cicd-integration)
18. [Testing & Validation](#chapter-18-testing--validation)
19. [Configuration Reference](#chapter-19-configuration-reference)
20. [API Reference](#chapter-20-api-reference)
21. [Troubleshooting](#chapter-21-troubleshooting)
22. [Glossary](#chapter-22-glossary)

---

# Chapter 1: Introduction

## 1.1 What is EoSim?


![Figure: EoSim — 3D Product Visualization](images/product-3d.png)

EoSim is a multi-architecture embedded simulation platform that enables developers to simulate, validate, and test embedded systems before hardware is ready. It is the simulation and validation component of the EmbeddedOS ecosystem, supporting **52+ platforms** across **12 architectures**.

The platform provides:

- A native Python simulation engine for rapid prototyping and CI testing
- Renode integration for deterministic, peripheral-accurate simulation
- QEMU integration for full binary emulation with QMP and GDB support
- Hardware-in-the-loop (HIL) support for real hardware via debug probes
- A GUI dashboard with GPIO, UART, CPU, memory, and 3D visualization
- Configuration-driven platform definitions in YAML format
- CI-native testing with automatic validation and artifact generation

## 1.2 Key Capabilities

| Capability | Description |
|---|---|
| 52+ platforms | ARM Cortex-M, Cortex-A, RISC-V, Xtensa, x86, MIPS, PowerPC, and more |
| 12 architectures | Comprehensive coverage from MCUs to application processors |
| 4 simulation engines | EoSim native, Renode, QEMU, Hardware-in-the-Loop |
| GUI dashboard | GPIO panel, UART terminal, CPU state, memory view, 3D renderers |
| CI-native | Configuration-driven testing for automated validation pipelines |
| Cluster simulation | Multi-node IoT and distributed system testing |
| Platform YAML | Declarative platform definitions with full hardware specification |
| Artifact management | Export simulation artifacts for documentation and analysis |

## 1.3 Design Philosophy

1. **Simulate everything** — Every supported platform can be tested without physical hardware, from bare-metal MCU firmware to full Linux images on application processors.

![Figure: EoSim Hardware-in-the-Loop Test Architecture — GDB bridge with QEMU virtual peripherals](images/hil-testing.png)


2. **Engine flexibility** — Different simulation engines serve different needs: native Python for speed, Renode for determinism, QEMU for binary accuracy, HIL for real hardware.

3. **Configuration-driven** — Platform definitions are YAML files, not code. Adding a new platform requires no Python changes, just a new YAML configuration.

4. **CI-first** — Every simulation can run headless in a CI pipeline with deterministic pass/fail results.

5. **Ecosystem integration** — EoSim integrates tightly with EoS, eBoot, eBuild, and other EmbeddedOS components.

## 1.4 Use Cases

- **Pre-silicon development** — Write and test firmware before hardware prototypes are available
- **CI/CD validation** — Automated testing of embedded software across multiple targets
- **Hardware abstraction** — Test platform-independent code across diverse architectures
- **Cluster testing** — Validate multi-node IoT and distributed embedded systems
- **Education** — Learn embedded systems without purchasing development boards
- **Regression testing** — Catch platform-specific bugs before they reach hardware

---

# Chapter 2: Getting Started

## 2.1 Prerequisites

- **Python**: 3.10 or later
- **pip**: Latest version recommended
- **Optional**: QEMU (for QEMU engine), Renode (for Renode engine)

## 2.2 Installation

```bash
pip install git+https://github.com/embeddedos-org/eosim.git
```

## 2.3 Environment Health Check

After installation, run the doctor command to verify your environment:

```bash
eosim doctor
```

This checks for:
- Python version compatibility
- Required dependencies
- Optional tool availability (QEMU, Renode, GDB)
- Platform registry integrity

## 2.4 Quick Start

```bash
# List all available platforms
eosim list

# Get details about a specific platform
eosim info arm64-linux

# Run a simulation
eosim run arm64-linux

# Run validation tests
eosim test arm64-linux

# View platform statistics
eosim stats

# Open the GUI dashboard
eosim gui stm32f4

# Search for platforms
eosim search "cortex-m4"
```

## 2.5 First Simulation

Here is a complete workflow for simulating an STM32F4 target:

![Figure: EoSim Simulation Execution Flow — platform load through assertion checking](images/simulation-flow.png)


```bash
# 1. Check the platform is available
eosim info stm32f4

# 2. Run the simulation
eosim run stm32f4

# 3. Run validation tests
eosim test stm32f4

# 4. Export artifacts
eosim artifact stm32f4

# 5. Open the GUI for interactive debugging
eosim gui stm32f4
```

---

# Chapter 3: System Architecture

## 3.1 Architectural Overview

```
eosim/
├── eosim/
│   ├── cli/              CLI entry point (click-based)
│   ├── core/             Core simulation logic
│   ├── engine/           Backend engines (EoSim native, Renode)
│   ├── gui/              Tkinter GUI dashboard
│   ├── integrations/     External tool integrations
│   ├── artifacts/        Simulation artifact management
│   └── platforms/        Platform abstraction
├── platforms/            52+ platform definitions (YAML + Renode .repl/.resc)
│   ├── stm32f4/          STM32F4 Discovery
│   ├── raspi4/           Raspberry Pi 4
│   ├── esp32/            ESP32
│   ├── riscv64/          RISC-V 64-bit
│   ├── jetson-orin/      NVIDIA Jetson Orin
│   └── ...               + 47 more
├── tests/                Unit + integration + scenario tests
├── examples/             Demo scenarios (cluster-demo)
├── pyproject.toml        Python package configuration
└── pytest.ini            Test configuration
```

## 3.2 Component Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        CLI (click)                           │
│    list │ info │ run │ test │ gui │ doctor │ stats │ search  │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                    Core Engine                               │
│  ┌──────────┐  ┌───────────┐  ┌───────────┐  ┌──────────┐  │
│  │ Platform  │  │ Simulator │  │ Validator │  │ Artifact │  │
│  │ Registry  │  │ Manager   │  │ Runner    │  │ Manager  │  │
│  └─────┬────┘  └─────┬─────┘  └─────┬─────┘  └────┬─────┘  │
│        │              │              │              │        │
│  ┌─────▼──────────────▼──────────────▼──────────────▼─────┐ │
│  │                 Platform Abstraction                     │ │
│  │          YAML config → Platform object → Engine          │ │
│  └──────────────────────┬──────────────────────────────────┘ │
└─────────────────────────┼───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                   Simulation Engines                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │  EoSim   │  │  Renode   │  │  QEMU    │  │   HIL    │    │
│  │  Native   │  │          │  │  QMP/GDB │  │          │    │
│  │  Python   │  │  .repl   │  │          │  │  Debug   │    │
│  │          │  │  .resc   │  │          │  │  Probe   │    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## 3.3 Data Flow

1. **CLI invocation** — User runs `eosim run <platform>`
2. **Platform lookup** — Registry resolves the platform YAML configuration
3. **Engine selection** — The appropriate simulation engine is selected based on platform config
4. **Simulation start** — Engine initializes CPU, memory, and peripherals
5. **Execution** — Firmware executes on the simulated hardware
6. **Validation** — Test assertions verify expected behavior
7. **Artifact export** — Simulation results are packaged for analysis

---

# Chapter 4: CLI Reference

## 4.1 Overview

EoSim provides a Click-based CLI with 10 commands. All commands follow the pattern `eosim <command> [options] [arguments]`.

## 4.2 Command Reference

### `eosim list`

List available simulation platforms with optional filtering.

```bash
# List all platforms
eosim list

# Filter by architecture
eosim list --arch arm-cortex-m

# Filter by vendor
eosim list --vendor stmicro

# Filter by class
eosim list --class mcu

# Filter by engine
eosim list --engine renode
```

**Options:**

| Option | Description |
|---|---|
| `--arch` | Filter by CPU architecture |
| `--vendor` | Filter by chip vendor |
| `--class` | Filter by platform class (mcu, app, specialty) |
| `--engine` | Filter by simulation engine |
| `--format` | Output format: table, json, csv |

### `eosim info <platform>`

Show detailed information about a specific platform.

```bash
eosim info stm32f4
```

**Output includes:**
- Platform name and display name
- Architecture and CPU
- Memory configuration (RAM, Flash)
- Supported peripherals
- Simulation engine
- Boot configuration
- Runtime parameters

### `eosim run <platform>`

Run a simulation for the specified platform.

```bash
# Basic run
eosim run arm64-linux

# Run with custom firmware
eosim run stm32f4 --firmware path/to/firmware.bin

# Headless mode (no GUI)
eosim run stm32f4 --headless

# With GDB server
eosim run stm32f4 --gdb --gdb-port 1234

# With timeout
eosim run stm32f4 --timeout 60
```

**Options:**

| Option | Description |
|---|---|
| `--firmware` | Path to firmware binary |
| `--headless` | Run without GUI |
| `--gdb` | Enable GDB server |
| `--gdb-port` | GDB server port (default: 1234) |
| `--timeout` | Simulation timeout in seconds |
| `--trace` | Enable execution trace |

### `eosim test <platform>`

Run validation tests for a platform.

```bash
# Run all tests
eosim test arm64-linux

# Run specific test suite
eosim test stm32f4 --suite peripheral

# Verbose output
eosim test stm32f4 -v
```

### `eosim validate <config>`

Validate a platform configuration file.

```bash
eosim validate platforms/stm32f4/platform.yaml
```

### `eosim artifact <platform>`

Export simulation artifacts.

```bash
eosim artifact stm32f4 --output ./artifacts/
```

### `eosim doctor`

Check environment health and dependencies.

```bash
eosim doctor
```

**Checks performed:**
- Python version
- Required packages
- QEMU installation
- Renode installation
- GDB availability
- Platform registry integrity
- Disk space

### `eosim stats`

Display platform registry statistics.

```bash
eosim stats
```

**Output:**
- Total platform count
- Platforms per architecture
- Platforms per engine
- Platforms per vendor

### `eosim search <query>`

Fuzzy search across all platforms.

```bash
eosim search "bluetooth"
eosim search "cortex-a"
eosim search "automotive"
```

### `eosim gui [platform]`

Open the GUI dashboard.

```bash
# Open with a specific platform
eosim gui stm32f4

# Open platform selector
eosim gui
```

---

# Chapter 5: Platform Registry

## 5.1 Overview

The platform registry is the central catalog of all supported simulation targets. Each platform is defined by a YAML configuration file in the `platforms/` directory.

## 5.2 Registry Structure

```
platforms/
├── stm32f4/
│   ├── platform.yaml       # Platform definition
│   ├── stm32f4.repl        # Renode platform description (optional)
│   └── stm32f4.resc        # Renode script (optional)
├── raspi4/
│   ├── platform.yaml
│   └── images/             # Boot images (kernel, rootfs)
├── esp32/
│   └── platform.yaml
├── riscv64/
│   └── platform.yaml
└── ...
```

## 5.3 Platform Discovery

EoSim discovers platforms by scanning the `platforms/` directory at startup. Each directory containing a `platform.yaml` file is registered as an available platform.

## 5.4 Platform Metadata

Each platform exposes the following metadata:

| Field | Description |
|---|---|
| `name` | Unique platform identifier (e.g., `stm32f4`) |
| `display_name` | Human-readable name (e.g., `STM32F4 Discovery`) |
| `arch` | CPU architecture (e.g., `arm-cortex-m4`) |
| `vendor` | Chip vendor (e.g., `stmicro`) |
| `class` | Platform class: `mcu`, `app`, `specialty` |
| `engine` | Default simulation engine |
| `description` | Platform description |

---

# Chapter 6: Supported Platforms

## 6.1 ARM Cortex-M (MCU)

| Platform | SoC | Description |
|---|---|---|
| `stm32f4` | STM32F407 | Cortex-M4F, 168 MHz, FPU |
| `stm32h7` | STM32H743 | Cortex-M7, 480 MHz, Dual-core |
| `stm32l4` | STM32L4xx | Cortex-M4, Ultra-low-power |
| `nrf52` | nRF52840 | Cortex-M4F, BLE 5.0 |
| `nrf5340` | nRF5340 | Cortex-M33, Dual-core, BLE 5.3 |
| `nrf9160` | nRF9160 | Cortex-M33, LTE-M/NB-IoT |
| `samd51` | ATSAMD51 | Cortex-M4F, Arduino/Adafruit |
| `samc21` | ATSAMC21 | Cortex-M0+, CAN, Industrial |
| `k64f` | MK64FN1M0 | Cortex-M4F, Ethernet |
| `rp2040` | RP2040 | Dual Cortex-M0+, PIO |
| `psoc6` | PSoC 6 | Cortex-M4F + M0+, BLE |
| `s32k344` | S32K344 | Cortex-M7, Automotive CAN-FD |
| `renesas-ra6m5` | RA6M5 | Cortex-M33, TrustZone |

## 6.2 ARM Cortex-A (Application Processors)

| Platform | SoC | Description |
|---|---|---|
| `raspi2b` | BCM2836 | Cortex-A7, Quad-core |
| `raspi3` | BCM2837 | Cortex-A53, 64-bit |
| `raspi4` | BCM2711 | Cortex-A72, 4-core, 8GB |
| `raspi5` | BCM2712 | Cortex-A76, 4-core |
| `raspi-zero2w` | BCM2710A1 | Cortex-A53, Compact |
| `imx8m` | i.MX8M | Cortex-A53, NPU, 4K |
| `am64x` | AM6442 | Cortex-A53 + R5F, Industrial |
| `stm32mp1` | STM32MP1 | Cortex-A7 + M4, Linux |
| `jetson-nano` | Tegra X1 | Cortex-A57, 128 CUDA |
| `jetson-orin` | Orin | Cortex-A78AE, 40 TOPS |
| `arm-vexpress` | Versatile Express | Cortex-A9/A15 development |
| `vexpress-a9` | VExpress A9 | Cortex-A9 QEMU target |
| `vexpress-a15` | VExpress A15 | Cortex-A15 QEMU target |
| `arm64` | Generic | AArch64 Linux |
| `arm-mcu` | Generic | ARM MCU reference |
| `beaglebone` | AM335x | Cortex-A8, PRU |

## 6.3 RISC-V

| Platform | SoC | Description |
|---|---|---|
| `riscv64` | Generic | RISC-V 64-bit Linux |
| `sifive_u` | FU740 | RISC-V U74, Linux-capable |
| `esp32c3` | ESP32-C3 | RISC-V, Wi-Fi/BLE, Single-core |
| `kendryte-k210` | K210 | Dual-core RISC-V, AI |
| `gd32vf103` | GD32VF103 | RISC-V, 108 MHz, USB OTG |

## 6.4 Xtensa

| Platform | SoC | Description |
|---|---|---|
| `esp32` | ESP32 | Xtensa LX6, Wi-Fi/BLE, Dual-core |
| `esp32s3` | ESP32-S3 | Xtensa LX7, AI acceleration |
| `xtensa-esp` | Generic | Xtensa ESP reference |

## 6.5 x86 / MIPS / PowerPC / Other

| Platform | Arch | Description |
|---|---|---|
| `x86_64` | x86_64 | Generic Linux on q35 |
| `qemu-q35` | x86_64 | QEMU Q35 chipset |
| `mipsel` | MIPS | MIPS little-endian |
| `ppce500` | PowerPC | PowerPC e500 |
| `microblaze` | MicroBlaze | Xilinx soft-core FPGA |
| `arc-em` | ARC EM | Synopsys ARC |
| `versatilepb` | ARM | ARM Versatile PB |
| `pic32mz` | MIPS | Microchip PIC32MZ |
| `ti-msp432` | ARM | TI MSP432 |
| `ti-tms570` | ARM | TI TMS570 Safety MCU |

## 6.6 Automotive / Safety

| Platform | SoC | Description |
|---|---|---|
| `aurix-tc3xx` | AURIX TC3xx | TriCore, Automotive safety |
| `renesas-rh850` | RH850 | Automotive MCU |
| `cortex-r5` | Generic | Cortex-R5 safety MCU |
| `cortex-r52` | Generic | Cortex-R52 safety MCU |

## 6.7 Specialty Simulators

| Platform | Type | Description |
|---|---|---|
| `aerodynamics-sim` | Physics | Aerodynamics simulation |
| `finance-sim` | Domain | Financial modeling |
| `gaming-sim` | Domain | Game engine simulation |
| `physiology-sim` | Domain | Physiological simulation |
| `weather-sim` | Domain | Weather modeling |

---

# Chapter 7: Simulation Engines

## 7.1 Engine Comparison

| Engine | Type | Speed | Fidelity | Use Case |
|---|---|---|---|---|
| **EoSim native** | Python simulation | Fast | Medium | Rapid prototyping, CI testing, peripheral logic |
| **Renode** | Deterministic sim | Medium | High | Peripheral-accurate, multi-node, deterministic |
| **QEMU** | Binary emulation | Medium | High | Full firmware on emulated CPU |
| **HIL** | Hardware-in-loop | Real-time | Exact | Real hardware via debug probe |

## 7.2 Engine Selection Guidelines

| Scenario | Recommended Engine |
|---|---|
| Quick CI smoke test | EoSim native |
| Peripheral register testing | Renode |
| Full firmware validation | QEMU |
| Production-identical testing | HIL |
| Multi-node cluster testing | Renode or EoSim native |
| Power consumption analysis | HIL |
| Timing-critical validation | Renode (deterministic) or HIL |

## 7.3 Engine Configuration

The simulation engine is specified in the platform YAML:

```yaml
engine: renode    # Options: native, renode, qemu, hil
```

Engines can also be overridden at runtime:

```bash
eosim run stm32f4 --engine qemu
```

---

# Chapter 8: Platform Definition Format

## 8.1 YAML Schema

Each platform is defined by a `platform.yaml` file with the following structure:

```yaml
name: arm64-linux
display_name: ARM64 Generic Linux
arch: arm64
engine: renode
simulation:
  machine: virt
  cpu: cortex-a57
boot:
  kernel: images/arm64-Image
  rootfs: images/arm64-rootfs.ext4
runtime:
  memory_mb: 2048
  headless: true
  uart: sysbus.uart0
```

## 8.2 Schema Fields

### Top-Level Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Unique platform identifier |
| `display_name` | string | Yes | Human-readable name |
| `arch` | string | Yes | CPU architecture |
| `engine` | string | Yes | Default simulation engine |
| `vendor` | string | No | Chip vendor |
| `class` | string | No | Platform class (mcu/app/specialty) |
| `description` | string | No | Platform description |

### Simulation Section

| Field | Type | Description |
|---|---|---|
| `machine` | string | Machine type (e.g., `virt`, `stm32f4discovery`) |
| `cpu` | string | CPU model (e.g., `cortex-a57`, `cortex-m4f`) |
| `memory_kb` | int | RAM size in KB (MCU targets) |
| `flash_kb` | int | Flash size in KB (MCU targets) |
| `clock_mhz` | int | CPU clock frequency in MHz |

### Boot Section

| Field | Type | Description |
|---|---|---|
| `kernel` | string | Path to kernel image |
| `rootfs` | string | Path to root filesystem |
| `firmware` | string | Path to firmware binary |
| `dtb` | string | Path to device tree blob |

### Runtime Section

| Field | Type | Description |
|---|---|---|
| `memory_mb` | int | RAM size in MB (Linux targets) |
| `headless` | bool | Run without display |
| `uart` | string | Primary UART device path |
| `gdb_port` | int | Default GDB port |
| `timeout_s` | int | Default simulation timeout |

### Peripherals Section

```yaml
peripherals:
  gpio:
    ports: [A, B, C, D]
    pins_per_port: 16
  uart:
    count: 4
    baud_default: 115200
  spi:
    count: 3
  i2c:
    count: 2
  adc:
    channels: 16
    resolution_bits: 12
  timer:
    count: 8
  can:
    count: 2
```

## 8.3 MCU Platform Example

```yaml
name: stm32f4
display_name: STM32F4 Discovery
arch: arm-cortex-m4
vendor: stmicro
class: mcu
engine: renode
description: STM32F407VG Discovery board with Cortex-M4F at 168 MHz

simulation:
  machine: stm32f4discovery
  cpu: cortex-m4f
  memory_kb: 192
  flash_kb: 1024
  clock_mhz: 168

peripherals:
  gpio:
    ports: [A, B, C, D, E]
    pins_per_port: 16
  uart:
    count: 6
    baud_default: 115200
  spi:
    count: 3
  i2c:
    count: 3
  adc:
    channels: 16
    resolution_bits: 12
  timer:
    count: 14
  dma:
    streams: 16

runtime:
  headless: true
  uart: sysbus.usart2
  gdb_port: 3333
  timeout_s: 30
```

## 8.4 Application Processor Platform Example

```yaml
name: raspi4
display_name: Raspberry Pi 4
arch: arm-cortex-a72
vendor: broadcom
class: app
engine: qemu
description: Raspberry Pi 4 Model B with BCM2711 Cortex-A72 quad-core

simulation:
  machine: raspi4b
  cpu: cortex-a72
  cores: 4
  clock_mhz: 1500

boot:
  kernel: images/raspi4-Image
  rootfs: images/raspi4-rootfs.ext4
  dtb: images/bcm2711-rpi-4-b.dtb

runtime:
  memory_mb: 4096
  headless: true
  uart: serial0
  gdb_port: 1234
  timeout_s: 120

peripherals:
  gpio:
    ports: [0]
    pins_per_port: 54
  uart:
    count: 6
  spi:
    count: 7
  i2c:
    count: 7
  ethernet:
    speed_mbps: 1000
  usb:
    ports: 4
    version: "3.0"
  pcie:
    lanes: 1
    gen: 2
```

---

# Chapter 9: Native Simulation Engine

## 9.1 Overview

The EoSim native engine is a Python-based simulation engine designed for fast iteration and CI testing. It simulates CPU execution, peripheral registers, and I/O behavior at a functional level.

## 9.2 Architecture

```
┌──────────────────────────────────────────┐
│           EoSim Native Engine            │
│                                          │
│  ┌──────────┐  ┌──────────────────────┐  │
│  │ CPU Sim   │  │ Peripheral Models    │  │
│  │ - Fetch   │  │ - GPIO              │  │
│  │ - Decode  │  │ - UART              │  │
│  │ - Execute │  │ - SPI               │  │
│  │ - Regs    │  │ - I2C               │  │
│  └─────┬────┘  │ - Timer             │  │
│        │       │ - ADC               │  │
│  ┌─────▼────┐  │ - DMA               │  │
│  │ Memory   │  └──────────────────────┘  │
│  │ - RAM    │                            │
│  │ - Flash  │  ┌──────────────────────┐  │
│  │ - MMIO   │  │ State Bridge         │  │
│  └──────────┘  │ (export/import)      │  │
│                └──────────────────────┘  │
└──────────────────────────────────────────┘
```

## 9.3 CPU Simulation

The native engine provides a simplified CPU model that supports:

- Register file (R0-R15 for ARM, x0-x31 for RISC-V)
- Program counter and stack pointer tracking
- Basic instruction decode and execute
- Interrupt controller simulation
- Clock cycle estimation

```python
from eosim.engine.native import NativeEngine

engine = NativeEngine("stm32f4")
engine.load_firmware("firmware.bin")
engine.reset()

# Step execution
for _ in range(1000):
    engine.step()

# Check registers
pc = engine.cpu.pc
sp = engine.cpu.sp
r0 = engine.cpu.regs[0]
```

## 9.4 Peripheral Models

Each peripheral is modeled as a Python class with register-level access:

```python
from eosim.engine.native.peripherals import GPIO

gpio = engine.get_peripheral("GPIOA")

# Read/write registers
gpio.write_register("ODR", 0x0001)  # Set pin 0 high
value = gpio.read_register("IDR")    # Read input data

# Pin-level access
gpio.set_pin(0, True)
state = gpio.get_pin(0)
```

## 9.5 State Bridge

The state bridge enables exporting and importing simulation state for checkpoint/restore and cross-engine migration:

```python
# Export state
state = engine.export_state()
with open("checkpoint.json", "w") as f:
    json.dump(state, f)

# Import state
with open("checkpoint.json") as f:
    state = json.load(f)
engine.import_state(state)
```

---

# Chapter 10: Renode Integration

## 10.1 Overview

Renode is a deterministic simulation framework that provides cycle-accurate peripheral simulation. EoSim integrates with Renode for high-fidelity testing.

## 10.2 Renode Platform Files

Each Renode-compatible platform includes:

- **`.repl`** (Renode Platform Layout) — Defines the hardware topology
- **`.resc`** (Renode Script) — Configures the simulation scenario

### Example `.repl` File

```
cpu: CPU.CortexM4 @ sysbus
    cpuType: "cortex-m4f"
    nvic: nvic

nvic: IRQControllers.NVIC @ sysbus 0xE000E000
    -> cpu@0

usart2: UART.STM32_UART @ sysbus 0x40004400
    -> nvic@38

gpioa: GPIOPort.STM32_GPIOPort @ sysbus 0x40020000
    numberOfPins: 16

flash: Memory.MappedMemory @ sysbus 0x08000000
    size: 0x100000

sram: Memory.MappedMemory @ sysbus 0x20000000
    size: 0x30000
```

### Example `.resc` File

```
mach create
machine LoadPlatformDescription @platforms/stm32f4/stm32f4.repl

sysbus LoadELF @firmware.elf

showAnalyzer usart2

start
```

## 10.3 Running with Renode

```bash
# Run platform with Renode engine
eosim run stm32f4 --engine renode

# With Renode telnet monitor
eosim run stm32f4 --engine renode --monitor
```

## 10.4 Deterministic Execution

Renode provides deterministic execution, meaning the same firmware binary will always produce the same results. This is critical for:

- Reproducible test results in CI
- Debugging timing-dependent bugs
- Regression testing

---

# Chapter 11: QEMU Integration

## 11.1 Overview

QEMU provides full binary emulation for supported architectures. EoSim integrates with QEMU via the QEMU Machine Protocol (QMP) and GDB stub for control and debugging.

## 11.2 QMP Integration

The QEMU Machine Protocol enables programmatic control of QEMU instances:

```python
from eosim.integrations.qemu import QEMUManager

qemu = QEMUManager()
qemu.start("arm64-linux", qmp_port=4444)

# QMP commands
qemu.qmp_command("query-status")
qemu.qmp_command("stop")
qemu.qmp_command("cont")

# Memory inspection
memory = qemu.qmp_command("memsave", {
    "val": 0x80000000,
    "size": 4096,
    "filename": "/tmp/memdump.bin"
})
```

## 11.3 GDB Integration

QEMU's built-in GDB stub enables source-level debugging:

```bash
# Start QEMU with GDB server
eosim run arm64-linux --engine qemu --gdb --gdb-port 1234

# In another terminal, connect GDB
gdb-multiarch firmware.elf
(gdb) target remote :1234
(gdb) break main
(gdb) continue
```

## 11.4 Supported QEMU Machines

| Platform | QEMU Machine | QEMU System |
|---|---|---|
| `arm64` | virt | qemu-system-aarch64 |
| `raspi2b` | raspi2b | qemu-system-aarch64 |
| `raspi3` | raspi3b | qemu-system-aarch64 |
| `raspi4` | raspi4b | qemu-system-aarch64 |
| `vexpress-a9` | vexpress-a9 | qemu-system-arm |
| `vexpress-a15` | vexpress-a15 | qemu-system-arm |
| `x86_64` | q35 | qemu-system-x86_64 |
| `riscv64` | virt | qemu-system-riscv64 |
| `mipsel` | malta | qemu-system-mipsel |
| `ppce500` | ppce500 | qemu-system-ppc |

## 11.5 QEMU Configuration

```yaml
# In platform.yaml
engine: qemu
qemu:
  system: qemu-system-aarch64
  machine: virt
  cpu: cortex-a57
  memory_mb: 2048
  extra_args:
    - "-nographic"
    - "-serial"
    - "mon:stdio"
  qmp_port: 4444
  gdb_port: 1234
```

---

# Chapter 12: Hardware-in-the-Loop

## 12.1 Overview

Hardware-in-the-Loop (HIL) mode connects EoSim to real hardware via debug probes (J-Link, ST-Link, CMSIS-DAP). This provides exact hardware behavior at real-time speed.

## 12.2 Supported Debug Probes

| Probe | Interface | Platforms |
|---|---|---|
| Segger J-Link | SWD/JTAG | All ARM targets |
| ST-Link V2/V3 | SWD | STM32 targets |
| CMSIS-DAP | SWD/JTAG | All ARM targets |
| Black Magic Probe | SWD/JTAG | All ARM targets |

## 12.3 HIL Configuration

```yaml
engine: hil
hil:
  probe: jlink
  interface: swd
  speed_khz: 4000
  target: stm32f407vg
  reset_strategy: hw
```

## 12.4 HIL Workflow

```bash
# Flash and run on real hardware
eosim run stm32f4 --engine hil

# Run tests on real hardware
eosim test stm32f4 --engine hil

# Monitor UART output
eosim run stm32f4 --engine hil --uart /dev/ttyACM0
```

---

# Chapter 13: GUI Dashboard

## 13.1 Overview

The EoSim GUI dashboard is an optional Tkinter-based interface providing real-time visualization of simulation state.

## 13.2 Panels

### GPIO Panel

Visual representation of all GPIO pins with click-to-toggle functionality:

- Pin state indicators (high/low)
- Direction indicators (input/output)
- Alternate function labels
- Click to toggle output pins

### UART Terminal

Real-time serial output display:

- Auto-scroll with configurable buffer size
- Send commands to simulated UART
- Configurable baud rate display
- Export transcript to file

### CPU State Panel

Live register and state display:

- General-purpose registers (R0-R15 / x0-x31)
- Program counter (PC)
- Stack pointer (SP)
- Status flags (N, Z, C, V)
- Clock cycle count
- Current instruction disassembly

### Memory View

Hex dump viewer for RAM and Flash regions:

- Configurable base address and range
- ASCII column
- Live update during simulation
- Search functionality

### Peripheral Registers

Register-level view for all simulated peripherals:

- Timer configuration (TIMx_CR1, TIMx_ARR, etc.)
- ADC configuration (ADC_CR, ADC_DR, etc.)
- SPI configuration (SPIx_CR1, SPIx_DR, etc.)
- I2C configuration (I2Cx_CR1, I2Cx_DR, etc.)

### 3D Renderers

Domain-specific 3D visualization:

| Renderer | Description |
|---|---|
| Drone | Quadcopter position, orientation, rotor speeds |
| Robot | Articulated robot arm joint angles |
| Vehicle | Automotive simulation with steering, speed |
| Aircraft | Flight simulation with attitude, altitude |
| Medical | Physiological signal visualization |
| Satellite | Orbital mechanics and attitude control |

## 13.3 Launching the GUI

```bash
# Launch with platform selection
eosim gui

# Launch for a specific platform
eosim gui stm32f4

# Launch with specific panels
eosim gui stm32f4 --panels gpio,uart,cpu
```

---

# Chapter 14: Peripheral Simulation

## 14.1 GPIO

The GPIO peripheral simulates digital I/O pins with support for:

- Input/output direction control
- Pull-up/pull-down configuration
- Alternate function mapping
- Interrupt generation (rising/falling edge)
- Open-drain and push-pull modes

```python
# GPIO simulation API
gpio = engine.peripheral("GPIOA")
gpio.configure_pin(0, direction="output", mode="push-pull")
gpio.write_pin(0, True)

gpio.configure_pin(1, direction="input", pull="up")
state = gpio.read_pin(1)

# Interrupt simulation
gpio.configure_interrupt(2, trigger="rising", callback=my_handler)
```

## 14.2 UART

UART simulation supports:

- Configurable baud rate, data bits, parity, stop bits
- TX/RX FIFOs
- DMA integration
- Interrupt generation (TXE, RXNE, IDLE)

```python
uart = engine.peripheral("USART2")
uart.configure(baud=115200, bits=8, parity="none", stop=1)
uart.transmit(b"Hello, EoSim!\r\n")
data = uart.receive(timeout_ms=100)
```

## 14.3 SPI

SPI simulation supports:

- Master and slave modes
- Configurable clock polarity and phase (CPOL/CPHA)
- 8-bit and 16-bit data width
- DMA integration

## 14.4 I2C

I2C simulation supports:

- Master and slave modes
- 7-bit and 10-bit addressing
- Clock stretching
- Multi-master arbitration

## 14.5 Timers

Timer simulation supports:

- Up/down counting modes
- PWM output generation
- Input capture
- Output compare
- Encoder mode
- DMA burst transfers

## 14.6 ADC

ADC simulation supports:

- Configurable resolution (8/10/12-bit)
- Single and continuous conversion
- Scan mode across multiple channels
- DMA integration
- Configurable sample time
- Injected channel support

## 14.7 DMA

DMA simulation supports:

- Memory-to-memory transfers
- Peripheral-to-memory and memory-to-peripheral
- Circular mode
- Double-buffer mode
- Transfer complete and half-transfer interrupts

---

# Chapter 15: CPU Simulation & State Bridge

## 15.1 CPU Models

EoSim models the following CPU architectures:

| Architecture | Instruction Sets | Features |
|---|---|---|
| ARM Cortex-M | Thumb, Thumb-2 | NVIC, SysTick, MPU |
| ARM Cortex-A | ARM, Thumb-2, AArch64 | GIC, MMU, Cache |
| ARM Cortex-R | ARM, Thumb-2 | MPU, TCM |
| RISC-V | RV32I/RV64I + extensions | PLIC, CLINT |
| Xtensa | Xtensa LX6/LX7 | Custom TIE |
| x86_64 | x86-64 | APIC, IOMMU |
| MIPS | MIPS32/MIPS64 | CP0 |
| PowerPC | PowerPC | MPIC |

## 15.2 State Bridge

The state bridge is a mechanism for exporting and importing the complete simulation state, enabling:

- **Checkpoint/restore** — Save simulation state and resume later
- **Cross-engine migration** — Start with native engine, switch to QEMU for detailed analysis
- **Test fixture creation** — Create known states for deterministic testing
- **Debugging** — Capture state at point of failure for offline analysis

### State Format

```json
{
    "platform": "stm32f4",
    "engine": "native",
    "timestamp": "2026-04-25T10:30:00Z",
    "cpu": {
        "registers": {
            "r0": 0, "r1": 1024, "r2": 0,
            "pc": 134217728, "sp": 536870912,
            "psr": 16777216
        },
        "cycle_count": 1000000
    },
    "memory": {
        "flash": {"base": 134217728, "data": "base64..."},
        "sram": {"base": 536870912, "data": "base64..."}
    },
    "peripherals": {
        "GPIOA": {"ODR": 1, "IDR": 0, "MODER": 1},
        "USART2": {"CR1": 8192, "BRR": 1667}
    }
}
```

### State Bridge API

```python
from eosim.core.state_bridge import StateBridge

bridge = StateBridge(engine)

# Export
state = bridge.export_state()
bridge.save_to_file("checkpoint.json")

# Import
bridge.load_from_file("checkpoint.json")
bridge.import_state(state)

# Diff two states
diff = StateBridge.diff(state1, state2)
```

---

# Chapter 16: Cluster Simulation

## 16.1 Overview

Cluster simulation enables testing of multi-node embedded systems, such as IoT networks, distributed sensor arrays, and vehicle networks.

## 16.2 Cluster Configuration

```yaml
# cluster.yaml
name: iot-sensor-network
nodes:
  - platform: nrf52
    name: sensor-1
    firmware: sensor_firmware.bin
    connections:
      - target: gateway
        type: ble
  - platform: nrf52
    name: sensor-2
    firmware: sensor_firmware.bin
    connections:
      - target: gateway
        type: ble
  - platform: raspi4
    name: gateway
    firmware: gateway_firmware.img
    connections:
      - target: cloud
        type: ethernet
```

## 16.3 Running Cluster Simulations

```bash
# Run cluster simulation
eosim cluster run cluster.yaml

# Test cluster
eosim cluster test cluster.yaml

# Monitor all nodes
eosim cluster monitor cluster.yaml
```

## 16.4 Inter-Node Communication

The cluster engine simulates communication channels between nodes:

- **BLE** — Simulated Bluetooth Low Energy with configurable RSSI and latency
- **Ethernet** — TCP/IP networking between nodes
- **CAN** — Controller Area Network for automotive clusters
- **Serial** — UART-based point-to-point links

---

# Chapter 17: CI/CD Integration

## 17.1 CI-Native Design

EoSim is designed for CI integration. Every simulation can run headless with deterministic pass/fail results.

## 17.2 GitHub Actions Example

```yaml
name: Firmware CI
on: [push, pull_request]

jobs:
  simulate:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        platform: [stm32f4, nrf52, raspi4, riscv64]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install eosim
      - run: eosim doctor
      - run: eosim test ${{ matrix.platform }}
      - run: eosim artifact ${{ matrix.platform }} --output ./artifacts/
      - uses: actions/upload-artifact@v4
        with:
          name: sim-${{ matrix.platform }}
          path: ./artifacts/
```

## 17.3 Jenkins Pipeline

```groovy
pipeline {
    agent any
    stages {
        stage('Setup') {
            steps {
                sh 'pip install eosim'
                sh 'eosim doctor'
            }
        }
        stage('Test') {
            matrix {
                axes {
                    axis {
                        name 'PLATFORM'
                        values 'stm32f4', 'nrf52', 'raspi4'
                    }
                }
                stages {
                    stage('Simulate') {
                        steps {
                            sh "eosim test ${PLATFORM}"
                        }
                    }
                }
            }
        }
    }
}
```

## 17.4 Test Result Formats

EoSim generates test results in standard formats:

| Format | Option | Use Case |
|---|---|---|
| JUnit XML | `--junit-xml results.xml` | CI system integration |
| JSON | `--json results.json` | Programmatic processing |
| TAP | `--tap results.tap` | Test Anything Protocol |
| HTML | `--html report.html` | Human-readable reports |

---

# Chapter 18: Testing & Validation

## 18.1 Test Framework

EoSim uses pytest for its test suite with unit, integration, and scenario tests.

## 18.2 Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest -v

# Run with coverage
pytest --cov=eosim --cov-report=term-missing

# Run specific test category
pytest tests/unit/ -v
pytest tests/integration/ -v
pytest tests/scenarios/ -v
```

## 18.3 Test Categories

| Category | Directory | Description |
|---|---|---|
| Unit | `tests/unit/` | Individual component tests |
| Integration | `tests/integration/` | Cross-component interaction tests |
| Scenario | `tests/scenarios/` | End-to-end simulation scenarios |
| Platform | `tests/platform/` | Platform-specific validation |

## 18.4 Writing Platform Tests

Platform validation tests verify that a simulation produces expected behavior:

```python
import pytest
from eosim.core import Simulator

def test_stm32f4_gpio_toggle():
    sim = Simulator("stm32f4")
    sim.load_firmware("test_gpio.bin")
    sim.run(timeout_ms=1000)

    gpio = sim.peripheral("GPIOA")
    assert gpio.read_pin(5) == True  # LED should be on

def test_stm32f4_uart_output():
    sim = Simulator("stm32f4")
    sim.load_firmware("test_uart.bin")
    sim.run(timeout_ms=1000)

    uart = sim.peripheral("USART2")
    output = uart.get_transcript()
    assert "Hello, EoSim!" in output
```

---

# Chapter 19: Configuration Reference

## 19.1 Environment Variables

| Variable | Default | Description |
|---|---|---|
| `EOSIM_PLATFORMS_DIR` | `./platforms` | Platform definitions directory |
| `EOSIM_ENGINE` | `native` | Default simulation engine |
| `EOSIM_QEMU_PATH` | (system) | Path to QEMU installation |
| `EOSIM_RENODE_PATH` | (system) | Path to Renode installation |
| `EOSIM_LOG_LEVEL` | `INFO` | Logging level |
| `EOSIM_GUI_THEME` | `default` | GUI color theme |
| `EOSIM_ARTIFACT_DIR` | `./artifacts` | Artifact output directory |

## 19.2 Global Configuration File

```yaml
# ~/.eosim/config.yaml
engine: native
log_level: INFO
gui:
  theme: dark
  default_panels: [gpio, uart, cpu]
qemu:
  path: /usr/bin
  extra_args: ["-nographic"]
renode:
  path: /opt/renode
  telnet_port: 12345
hil:
  default_probe: jlink
  speed_khz: 4000
```

## 19.3 pyproject.toml Configuration

```toml
[project]
name = "eosim"
version = "1.0.0"
requires-python = ">=3.10"
dependencies = [
    "click>=8.0",
    "pyyaml>=6.0",
    "rich>=12.0",
]

[project.optional-dependencies]
gui = ["tkinter"]
renode = ["renode-run"]
dev = ["pytest", "pytest-cov", "flake8", "mypy"]

[project.scripts]
eosim = "eosim.cli:main"
```

---

# Chapter 20: API Reference

## 20.1 Core API

```python
from eosim.core import Simulator, PlatformRegistry

# Platform Registry
registry = PlatformRegistry()
platforms = registry.list_platforms()
platform = registry.get_platform("stm32f4")
results = registry.search("cortex-m4")
stats = registry.stats()

# Simulator
sim = Simulator("stm32f4")
sim = Simulator("stm32f4", engine="qemu")
sim.load_firmware("firmware.bin")
sim.reset()
sim.run(timeout_ms=5000)
sim.step(count=100)
sim.stop()
```

## 20.2 Engine API

```python
from eosim.engine import NativeEngine, RenodeEngine, QEMUEngine

# Native Engine
engine = NativeEngine(platform_config)
engine.initialize()
engine.load_firmware(path)
engine.run()
engine.step()
state = engine.export_state()
engine.import_state(state)

# QEMU Engine
engine = QEMUEngine(platform_config)
engine.start(qmp_port=4444, gdb_port=1234)
engine.qmp_command(cmd, args)
engine.stop()

# Renode Engine
engine = RenodeEngine(platform_config)
engine.load_repl(path)
engine.load_resc(path)
engine.start()
engine.monitor_command(cmd)
engine.stop()
```

## 20.3 Peripheral API

```python
from eosim.engine.native.peripherals import GPIO, UART, SPI, I2C, Timer, ADC

# GPIO
gpio = engine.peripheral("GPIOA")
gpio.configure_pin(pin, direction, mode, pull)
gpio.write_pin(pin, value)
value = gpio.read_pin(pin)
gpio.configure_interrupt(pin, trigger, callback)
reg = gpio.read_register(name)
gpio.write_register(name, value)

# UART
uart = engine.peripheral("USART2")
uart.configure(baud, bits, parity, stop)
uart.transmit(data)
data = uart.receive(timeout_ms)
transcript = uart.get_transcript()

# Timer
timer = engine.peripheral("TIM2")
timer.configure(prescaler, period, mode)
timer.start()
timer.stop()
count = timer.get_count()
```

## 20.4 State Bridge API

```python
from eosim.core.state_bridge import StateBridge

bridge = StateBridge(engine)
state = bridge.export_state()
bridge.import_state(state)
bridge.save_to_file(path)
bridge.load_from_file(path)
diff = StateBridge.diff(state1, state2)
```

## 20.5 GUI API

```python
from eosim.gui import Dashboard

dashboard = Dashboard(engine)
dashboard.add_panel("gpio")
dashboard.add_panel("uart")
dashboard.add_panel("cpu")
dashboard.add_panel("memory", base=0x20000000, size=0x1000)
dashboard.launch()
```

## 20.6 Artifact API

```python
from eosim.artifacts import ArtifactManager

artifacts = ArtifactManager(engine)
artifacts.capture_screenshot()
artifacts.export_uart_log(path)
artifacts.export_state(path)
artifacts.export_coverage(path)
artifacts.package(output_dir)
```

---

# Chapter 21: Troubleshooting

## 21.1 Installation Issues

### pip install fails

```
ERROR: Could not find a version that satisfies the requirement eosim
```

**Solution**: Install from source:

```bash
git clone https://github.com/embeddedos-org/eosim.git
cd eosim
pip install -e .
```

### Python version incompatible

```
ERROR: Python 3.8 is not supported
```

**Solution**: EoSim requires Python 3.10+. Install a newer Python version.

## 21.2 Runtime Issues

### QEMU not found

```
ERROR: qemu-system-aarch64 not found
```

**Solution**: Install QEMU and ensure it is in your PATH:

```bash
# Ubuntu
sudo apt install qemu-system-arm qemu-system-misc

# macOS
brew install qemu
```

### Renode not found

```
ERROR: Renode not found
```

**Solution**: Install Renode:

```bash
# Ubuntu
wget https://github.com/renode/renode/releases/latest/download/renode.deb
sudo dpkg -i renode.deb
```

### Platform not found

```
ERROR: Platform 'myplatform' not found
```

**Solution**: Check available platforms with `eosim list` and verify the platform name.

### Simulation timeout

```
ERROR: Simulation timed out after 30 seconds
```

**Solution**: Increase the timeout:

```bash
eosim run stm32f4 --timeout 120
```

### GUI fails to launch

```
ERROR: No display found
```

**Solution**: The GUI requires a display. For headless environments, use X11 forwarding or run in headless mode:

```bash
eosim run stm32f4 --headless
```

## 21.3 Debugging Tips

1. **Enable verbose logging**: `eosim --log-level DEBUG run stm32f4`
2. **Check platform config**: `eosim validate platforms/stm32f4/platform.yaml`
3. **Run environment doctor**: `eosim doctor`
4. **Verify firmware format**: Ensure the firmware binary matches the platform architecture
5. **Check memory layout**: Verify firmware is linked for the correct memory addresses

## 21.4 Performance Tips

1. Use the native engine for quick CI tests
2. Use QEMU for full-system validation
3. Disable unused peripherals in the platform config
4. Reduce memory size for faster simulation startup
5. Use headless mode when GUI is not needed

---

# Chapter 22: Glossary

| Term | Definition |
|---|---|
| **EoSim** | EmbeddedOS Simulation Platform |
| **Platform** | A hardware target definition (e.g., STM32F4, Raspberry Pi 4) |
| **Engine** | Simulation backend (native, Renode, QEMU, HIL) |
| **QEMU** | Quick Emulator — open-source machine emulator and virtualizer |
| **QMP** | QEMU Machine Protocol — JSON-based control interface for QEMU |
| **GDB** | GNU Debugger — source-level debugger |
| **Renode** | Open-source simulation framework for deterministic embedded testing |
| **HIL** | Hardware-in-the-Loop — testing with real hardware via debug probes |
| **SWD** | Serial Wire Debug — two-pin debug interface for ARM processors |
| **JTAG** | Joint Test Action Group — debug and programming interface |
| **MMIO** | Memory-Mapped I/O — peripheral registers accessed via memory addresses |
| **NVIC** | Nested Vectored Interrupt Controller — ARM Cortex-M interrupt controller |
| **DMA** | Direct Memory Access — hardware data transfer without CPU involvement |
| **GPIO** | General Purpose Input/Output — digital I/O pins |
| **UART** | Universal Asynchronous Receiver/Transmitter — serial communication |
| **SPI** | Serial Peripheral Interface — synchronous serial bus |
| **I2C** | Inter-Integrated Circuit — two-wire serial bus |
| **ADC** | Analog-to-Digital Converter |
| **PWM** | Pulse Width Modulation |
| **MCU** | Microcontroller Unit |
| **SoC** | System on Chip |
| **DTB** | Device Tree Blob — hardware description for Linux boot |
| **State Bridge** | Mechanism for exporting/importing simulation state |
| **Cluster Simulation** | Multi-node simulation for distributed embedded systems |
| **Platform YAML** | YAML configuration file defining a simulation platform |
| **CI** | Continuous Integration |

---

# Appendix A: Standards Compliance

EoSim is part of the EoS ecosystem and aligns with international standards including:

- **ISO/IEC/IEEE 15288:2023** — Systems and software engineering lifecycle
- **ISO/IEC 12207** — Software lifecycle processes
- **ISO/IEC/IEEE 42010** — Architecture description
- **ISO/IEC 25000/25010** — Systems and software quality
- **ISO/IEC 27001** — Information security management
- **IEC 61508** — Functional safety
- **ISO 26262** — Automotive functional safety
- **DO-178C** — Airborne systems software

---

# Appendix B: Related Projects

| Project | Repository | Purpose |
|---|---|---|
| **EoS** | embeddedos-org/eos | Embedded OS — HAL, RTOS kernel, services |
| **eBoot** | embeddedos-org/eboot | Bootloader — 24 board ports, secure boot |
| **eBuild** | embeddedos-org/ebuild | Build system — SDK generator, packaging |
| **EIPC** | embeddedos-org/eipc | IPC framework — Go + C SDK, HMAC auth |
| **EAI** | embeddedos-org/eai | AI layer — LLM inference, agent loop |
| **ENI** | embeddedos-org/eni | Neural interface — BCI, Neuralink adapter |
| **eApps** | embeddedos-org/eApps | Cross-platform apps — 46 C + LVGL apps |
| **EoStudio** | embeddedos-org/EoStudio | Design suite — 12 editors with LLM |
| **eDB** | embeddedos-org/eDB | Multi-model database engine |

---

# Appendix C: Platform Quick Reference

### Top 10 Most Used Platforms

| # | Platform | Architecture | Engine | Use Case |
|---|---|---|---|---|
| 1 | `stm32f4` | Cortex-M4F | Renode | General embedded development |
| 2 | `nrf52` | Cortex-M4F | Renode | BLE IoT devices |
| 3 | `raspi4` | Cortex-A72 | QEMU | Linux application development |
| 4 | `esp32` | Xtensa LX6 | Native | Wi-Fi/BLE IoT devices |
| 5 | `riscv64` | RISC-V 64 | QEMU | RISC-V development |
| 6 | `arm64` | AArch64 | QEMU | Generic ARM64 Linux |
| 7 | `stm32h7` | Cortex-M7 | Renode | High-performance MCU |
| 8 | `jetson-orin` | Cortex-A78AE | QEMU | AI/ML at the edge |
| 9 | `nrf5340` | Cortex-M33 | Renode | Dual-core BLE 5.3 |
| 10 | `x86_64` | x86_64 | QEMU | Desktop Linux testing |

---

*EoSim — Multi-Architecture Embedded Simulation Platform Reference — Version 1.0 — April 2026*

*Copyright (c) 2026 EmbeddedOS Organization. MIT License.*

## References

::: {#refs}
:::
