# SPDX-License-Identifier: MIT
"""Modeling method catalog for simulation approaches."""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ModelingMethod:
    name: str = ""
    display_name: str = ""
    description: str = ""
    engine_support: list[str] = field(default_factory=list)
    use_cases: list[str] = field(default_factory=list)
    parameters: dict = field(default_factory=dict)


MODELING_CATALOG: dict[str, ModelingMethod] = {
    "deterministic": ModelingMethod(
        name="deterministic",
        display_name="Deterministic Simulation",
        description="Fully repeatable cycle-accurate simulation with fixed outcomes.",
        engine_support=["eosim", "renode", "qemu"],
        use_cases=["regression_testing", "timing_analysis", "reproducible_debug"],
        parameters={"seed": 0},
    ),
    "stochastic": ModelingMethod(
        name="stochastic",
        display_name="Stochastic Simulation",
        description="Probabilistic simulation with random variations.",
        engine_support=["eosim", "renode"],
        use_cases=["reliability_analysis", "monte_carlo", "fault_injection"],
        parameters={"seed": None, "iterations": 1000},
    ),
    "discrete-event": ModelingMethod(
        name="discrete-event",
        display_name="Discrete Event Simulation",
        description="Event-driven simulation with discrete time steps.",
        engine_support=["eosim", "renode"],
        use_cases=["network_simulation", "queue_modeling", "protocol_testing"],
        parameters={"event_queue_size": 10000},
    ),
    "continuous": ModelingMethod(
        name="continuous",
        display_name="Continuous Simulation",
        description="Continuous-time simulation using differential equations.",
        engine_support=["eosim"],
        use_cases=["analog_circuits", "control_systems", "signal_processing"],
        parameters={"dt": 0.001, "solver": "rk4"},
    ),
    "hybrid": ModelingMethod(
        name="hybrid",
        display_name="Hybrid Simulation",
        description="Combined discrete-event and continuous simulation.",
        engine_support=["eosim", "renode"],
        use_cases=["mixed_signal", "cyber_physical", "hil_testing"],
        parameters={"dt": 0.001, "event_queue_size": 10000},
    ),
    "agent-based": ModelingMethod(
        name="agent-based",
        display_name="Agent-Based Modeling",
        description="Multi-agent simulation for emergent behavior analysis.",
        engine_support=["eosim"],
        use_cases=["swarm_robotics", "traffic_simulation", "social_modeling"],
        parameters={"max_agents": 1000, "interaction_radius": 10.0},
    ),
    "cfd": ModelingMethod(
        name="cfd",
        display_name="Computational Fluid Dynamics",
        description="Fluid flow simulation using Navier-Stokes equations.",
        engine_support=["eosim", "openfoam"],
        use_cases=["aerodynamics", "thermal_analysis", "turbulence_modeling"],
        parameters={"mesh_resolution": "medium", "turbulence_model": "k-epsilon"},
    ),
    "monte-carlo": ModelingMethod(
        name="monte-carlo",
        display_name="Monte Carlo Simulation",
        description="Statistical sampling-based simulation for probabilistic analysis.",
        engine_support=["eosim"],
        use_cases=["risk_analysis", "reliability_estimation", "financial_modeling"],
        parameters={"samples": 10000, "confidence_level": 0.95},
    ),
    "finite-element": ModelingMethod(
        name="finite-element",
        display_name="Finite Element Analysis",
        description="Mesh-based structural and thermal analysis.",
        engine_support=["eosim"],
        use_cases=["structural_analysis", "thermal_stress", "vibration_analysis"],
        parameters={"mesh_type": "tetrahedral", "element_order": 2},
    ),
    "particle-based": ModelingMethod(
        name="particle-based",
        display_name="Particle-Based Simulation",
        description="Lagrangian particle methods for fluid and solid mechanics.",
        engine_support=["eosim"],
        use_cases=["fluid_particles", "granular_flow", "sph_simulation"],
        parameters={"particle_count": 50000, "smoothing_length": 0.01},
    ),
}


def list_modeling_methods() -> list[str]:
    return list(MODELING_CATALOG.keys())


def get_modeling(name: str) -> Optional[ModelingMethod]:
    return MODELING_CATALOG.get(name)


def validate_modeling_for_engine(method: str, engine: str) -> list[str]:
    warnings = []
    m = get_modeling(method)
    if m is None:
        warnings.append(f"Unknown modeling method: {method}")
        return warnings
    if engine not in m.engine_support:
        warnings.append(
            "Modeling method '{}' is not supported by engine '{}'. "
            "Supported engines: {}".format(method, engine, ", ".join(m.engine_support))
        )
    return warnings
