# SPDX-License-Identifier: MIT
"""Platform schema validation constants and helpers."""

VALID_ARCHES = [
    "arm", "arm64", "aarch64", "riscv64", "riscv32", "x86_64",
    "mips", "mipsel", "xtensa", "microblaze", "arc", "powerpc", "tricore",
    "avr", "pic", "msp430", "sh", "sparc", "m68k", "ceva",
    "tensilica", "nios2", "openrisc", "loongarch", "rx",
]

VALID_ENGINES = [
    "renode", "qemu", "eosim", "xplane", "gazebo", "openfoam",
    "carla", "airsim", "verilator", "matlab", "ros2", "ns3", "omnet",
]

VALID_DOMAINS = [
    "automotive", "medical", "industrial", "consumer", "aerospace",
    "iot", "robotics", "defense", "energy", "telecom",
    "aerodynamics", "physiology", "finance", "weather", "gaming",
    "agriculture", "maritime", "mining", "construction", "retail",
    "education", "sports", "nuclear", "railway", "smart-city",
    "space", "quantum", "photonics", "neuromorphic", "hvac",
    "printing", "elevator", "traffic", "water", "oil-gas",
    "forestry", "fisheries", "logistics", "cybersecurity", "ar-vr",
]

VALID_MODELING = [
    "deterministic", "stochastic", "discrete-event", "continuous",
    "hybrid", "agent-based", "cfd", "monte-carlo",
    "finite-element", "particle-based",
    "neural-network", "reinforcement-learning", "digital-twin",
    "system-dynamics", "cellular-automata", "lattice-boltzmann",
    "spectral", "multi-body", "lumped-parameter", "bond-graph",
]

VALID_CLASSES = [
    "mcu", "sbc", "devboard", "soc", "mpu", "fpga", "virtual",
    "automotive", "mobile", "tv", "industrial", "desktop", "safety",
    "ai-accelerator", "gateway", "edge", "hpc", "wearable",
    "sensor", "actuator", "router", "switch", "plc", "rtu",
]


def validate_platform(data: dict) -> list[str]:
    errors = []

    if "name" not in data or not data.get("name"):
        errors.append("missing required field: name")
    if "arch" not in data or not data.get("arch"):
        errors.append("missing required field: arch")
    if "engine" not in data or not data.get("engine"):
        errors.append("missing required field: engine")

    if data.get("arch") and data["arch"] not in VALID_ARCHES:
        errors.append("invalid arch: {}".format(data["arch"]))

    if data.get("engine") and data["engine"] not in VALID_ENGINES:
        errors.append("invalid engine: {}".format(data["engine"]))

    if data.get("class") and data["class"] not in VALID_CLASSES:
        errors.append("invalid class: {}".format(data["class"]))

    if data.get("domain") and data["domain"] not in VALID_DOMAINS:
        errors.append("invalid domain: {}".format(data["domain"]))

    if data.get("modeling") and data["modeling"] not in VALID_MODELING:
        errors.append("invalid modeling: {}".format(data["modeling"]))

    return errors
