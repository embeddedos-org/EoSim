# SPDX-License-Identifier: MIT
"""Domain profiles catalog for simulation contexts."""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DomainProfile:
    name: str = ""
    display_name: str = ""
    description: str = ""
    standards: list[str] = field(default_factory=list)
    safety_levels: list[str] = field(default_factory=list)
    typical_arches: list[str] = field(default_factory=list)
    typical_classes: list[str] = field(default_factory=list)
    test_scenarios: list[str] = field(default_factory=list)


DOMAIN_CATALOG: dict[str, DomainProfile] = {
    "automotive": DomainProfile(
        name="automotive",
        display_name="Automotive / Transportation",
        description="Vehicle ECU and transportation system simulation.",
        standards=["ISO 26262", "AUTOSAR", "SAE J3061"],
        safety_levels=["ASIL-A", "ASIL-B", "ASIL-C", "ASIL-D"],
        typical_arches=["arm", "arm64", "riscv64"],
        typical_classes=["mcu", "sbc"],
        test_scenarios=["ecu_boot", "can_bus", "ota_update", "diagnostics"],
    ),
    "medical": DomainProfile(
        name="medical",
        display_name="Medical Devices",
        description="Medical device firmware and safety-critical health systems.",
        standards=["IEC 62304", "FDA 510(k)", "ISO 14971"],
        safety_levels=["Class A", "Class B", "Class C"],
        typical_arches=["arm", "arm64"],
        typical_classes=["mcu", "sbc"],
        test_scenarios=["sensor_reading", "alarm_trigger", "data_logging", "ble_pairing"],
    ),
    "industrial": DomainProfile(
        name="industrial",
        display_name="Industrial Automation",
        description="PLC, SCADA, and factory automation simulation.",
        standards=["IEC 61508", "IEC 61131", "OPC UA"],
        safety_levels=["SIL-1", "SIL-2", "SIL-3", "SIL-4"],
        typical_arches=["arm", "x86_64"],
        typical_classes=["mcu", "sbc"],
        test_scenarios=["plc_cycle", "modbus_comm", "safety_relay", "hmi_display"],
    ),
    "consumer": DomainProfile(
        name="consumer",
        display_name="Consumer Electronics",
        description="Smart home, wearables, and consumer product simulation.",
        standards=["Bluetooth SIG", "Zigbee", "Matter"],
        safety_levels=[],
        typical_arches=["arm", "arm64", "xtensa"],
        typical_classes=["mcu", "sbc"],
        test_scenarios=["ble_connect", "wifi_provision", "ota_update", "power_mgmt"],
    ),
    "aerospace": DomainProfile(
        name="aerospace",
        display_name="Aerospace & Avionics",
        description="Avionics, satellite, and space system simulation.",
        standards=["DO-178C", "DO-254", "ARINC 653"],
        safety_levels=["DAL-A", "DAL-B", "DAL-C", "DAL-D", "DAL-E"],
        typical_arches=["arm64", "powerpc", "x86_64"],
        typical_classes=["sbc", "devboard"],
        test_scenarios=["boot_sequence", "arinc_msg", "redundancy_failover", "time_sync"],
    ),
    "iot": DomainProfile(
        name="iot",
        display_name="Internet of Things",
        description="IoT sensor nodes, gateways, and edge devices.",
        standards=["MQTT", "CoAP", "LwM2M"],
        safety_levels=[],
        typical_arches=["arm", "xtensa", "riscv64"],
        typical_classes=["mcu"],
        test_scenarios=["mqtt_publish", "deep_sleep", "sensor_read", "cloud_connect"],
    ),
    "robotics": DomainProfile(
        name="robotics",
        display_name="Robotics & Motion Control",
        description="Robot controllers, motor drives, and actuator systems.",
        standards=["ROS 2", "ISO 10218", "ISO 13482"],
        safety_levels=["PLd", "PLe"],
        typical_arches=["arm64", "x86_64"],
        typical_classes=["sbc", "devboard"],
        test_scenarios=["motor_control", "path_planning", "sensor_fusion", "emergency_stop"],
    ),
    "defense": DomainProfile(
        name="defense",
        display_name="Defense & Military",
        description="Defense electronics, radar, and communications.",
        standards=["MIL-STD-810", "MIL-STD-461", "DO-178C"],
        safety_levels=["SIL-3", "SIL-4"],
        typical_arches=["arm64", "powerpc", "x86_64"],
        typical_classes=["sbc", "devboard"],
        test_scenarios=["secure_boot", "crypto_ops", "radio_comm", "jamming_test"],
    ),
    "energy": DomainProfile(
        name="energy",
        display_name="Energy & Power Systems",
        description="Smart grid, battery management, and power electronics.",
        standards=["IEC 61850", "IEEE 1547", "IEC 62351"],
        safety_levels=["SIL-2", "SIL-3"],
        typical_arches=["arm", "arm64"],
        typical_classes=["mcu", "sbc"],
        test_scenarios=["grid_sync", "battery_charge", "fault_detect", "mppt_control"],
    ),
    "telecom": DomainProfile(
        name="telecom",
        display_name="Telecommunications",
        description="5G baseband, network equipment, and protocol simulation.",
        standards=["3GPP", "O-RAN", "IEEE 802.11"],
        safety_levels=[],
        typical_arches=["arm64", "x86_64"],
        typical_classes=["sbc", "devboard"],
        test_scenarios=["baseband_init", "packet_switching", "handover", "qos_test"],
    ),
    "aerodynamics": DomainProfile(
        name="aerodynamics",
        display_name="Aerodynamics & CFD",
        description="Computational fluid dynamics and aerodynamic simulation.",
        standards=["NASA CFD", "AIAA", "ISO 5167"],
        safety_levels=["Advisory", "Verification"],
        typical_arches=["x86_64", "arm64"],
        typical_classes=["sbc", "devboard"],
        test_scenarios=[
            "laminar_flow", "turbulent_flow", "shock_wave",
            "boundary_layer", "drag_analysis", "lift_curve",
        ],
    ),
    "physiology": DomainProfile(
        name="physiology",
        display_name="Physiology & Biomed Simulation",
        description="Human physiology modeling and biomedical signal simulation.",
        standards=["HL7 FHIR", "IEEE 11073", "ISO 13485"],
        safety_levels=["Class I", "Class II", "Class III"],
        typical_arches=["arm64", "x86_64"],
        typical_classes=["sbc"],
        test_scenarios=["ecg_waveform", "blood_pressure", "respiratory", "drug_response"],
    ),
    "finance": DomainProfile(
        name="finance",
        display_name="Financial Systems",
        description="Trading systems, risk engines, and financial modeling.",
        standards=["FIX Protocol", "ISO 20022", "PCI DSS"],
        safety_levels=["Critical", "High", "Medium"],
        typical_arches=["x86_64", "arm64"],
        typical_classes=["sbc", "devboard"],
        test_scenarios=["order_matching", "monte_carlo_risk", "latency_test", "market_data"],
    ),
    "weather": DomainProfile(
        name="weather",
        display_name="Weather & Climate Simulation",
        description="Numerical weather prediction and climate modeling.",
        standards=["WMO", "GRIB2", "NetCDF"],
        safety_levels=["Advisory", "Watch", "Warning"],
        typical_arches=["x86_64", "arm64"],
        typical_classes=["sbc", "devboard"],
        test_scenarios=["hurricane", "forecast_48h", "precipitation", "wind_model", "temperature_grid"],
    ),
    "gaming": DomainProfile(
        name="gaming",
        display_name="Gaming & Real-Time Simulation",
        description="Game physics, rendering pipelines, and real-time simulation.",
        standards=["PhysX", "Vulkan", "OpenXR"],
        safety_levels=[],
        typical_arches=["x86_64", "arm64"],
        typical_classes=["sbc", "devboard"],
        test_scenarios=["physics_sandbox", "collision_test", "render_pipeline", "input_latency"],
    ),
}


def list_domains() -> list[str]:
    return list(DOMAIN_CATALOG.keys())


def get_domain(name: str) -> Optional[DomainProfile]:
    return DOMAIN_CATALOG.get(name)


def suggest_platforms(domain: str, registry) -> list:
    profile = get_domain(domain)
    if profile is None:
        return []
    results = registry.filter(domain=domain)
    if not results:
        results = [p for p in registry.all()
                    if p.arch in profile.typical_arches
                    or p.platform_class in profile.typical_classes]
    return results
