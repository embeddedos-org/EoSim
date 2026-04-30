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
    # ── New modeling methods (v2.0) ──────────────────────────────────
    "neural-network": ModelingMethod(
        name="neural-network",
        display_name="Neural Network Surrogate",
        description="Trained neural network as a fast surrogate model.",
        engine_support=["eosim"],
        use_cases=["surrogate_model", "system_identification", "fast_inference"],
        parameters={"layers": 3, "hidden_size": 128},
    ),
    "reinforcement-learning": ModelingMethod(
        name="reinforcement-learning",
        display_name="Reinforcement Learning",
        description="RL agent controlling a simulated environment.",
        engine_support=["eosim", "carla", "airsim"],
        use_cases=["adaptive_control", "path_planning", "optimization"],
        parameters={"algorithm": "PPO", "episodes": 1000},
    ),
    "digital-twin": ModelingMethod(
        name="digital-twin",
        display_name="Digital Twin",
        description="Real-time mirror of physical hardware with predictive capability.",
        engine_support=["eosim"],
        use_cases=["predictive_maintenance", "anomaly_detection", "what_if_analysis"],
        parameters={"sync_interval_s": 1.0},
    ),
    "system-dynamics": ModelingMethod(
        name="system-dynamics",
        display_name="System Dynamics",
        description="Stock-and-flow models for feedback-driven systems.",
        engine_support=["eosim"],
        use_cases=["population_model", "supply_chain", "resource_management"],
        parameters={"dt": 0.1},
    ),
    "cellular-automata": ModelingMethod(
        name="cellular-automata",
        display_name="Cellular Automata",
        description="Grid-based discrete state evolution rules.",
        engine_support=["eosim"],
        use_cases=["fire_spread", "traffic_flow", "crystal_growth"],
        parameters={"grid_size": 100, "neighborhood": "moore"},
    ),
    "lattice-boltzmann": ModelingMethod(
        name="lattice-boltzmann",
        display_name="Lattice Boltzmann Method",
        description="Mesoscale fluid simulation on a discrete lattice.",
        engine_support=["eosim"],
        use_cases=["microfluidics", "porous_media", "multiphase_flow"],
        parameters={"lattice": "D2Q9", "tau": 0.8},
    ),
    "spectral": ModelingMethod(
        name="spectral",
        display_name="Spectral Methods",
        description="Frequency-domain numerical methods for PDEs.",
        engine_support=["eosim"],
        use_cases=["weather_modeling", "signal_processing", "turbulence"],
        parameters={"modes": 64},
    ),
    "multi-body": ModelingMethod(
        name="multi-body",
        display_name="Multi-Body Dynamics",
        description="Rigid/flexible body dynamics with constraints.",
        engine_support=["eosim", "gazebo"],
        use_cases=["robot_kinematics", "vehicle_dynamics", "mechanism_design"],
        parameters={"solver": "runge_kutta_4"},
    ),
    "lumped-parameter": ModelingMethod(
        name="lumped-parameter",
        display_name="Lumped Parameter Model",
        description="Simplified models using electrical circuit analogy.",
        engine_support=["eosim"],
        use_cases=["thermal_circuit", "hydraulic_system", "battery_model"],
        parameters={"components": 10},
    ),
    "bond-graph": ModelingMethod(
        name="bond-graph",
        display_name="Bond Graph",
        description="Energy-based modeling of multi-domain physical systems.",
        engine_support=["eosim"],
        use_cases=["mechatronics", "hydraulics", "electro_mechanical"],
        parameters={"causality": "integral"},
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
