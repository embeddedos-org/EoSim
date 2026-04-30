# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""Product simulator framework — BaseSimulator, individual simulators, and SimulatorFactory.

All simulators are pure Python, cross-platform (Linux/Windows/macOS).
No OS-specific dependencies. No tkinter, no C extensions.
"""
from eosim.engine.native.simulators.aerodynamics import AerodynamicsSimulator
from eosim.engine.native.simulators.agriculture import AgricultureSimulator
from eosim.engine.native.simulators.aircraft import AircraftSimulator
from eosim.engine.native.simulators.android import AndroidSimulator
from eosim.engine.native.simulators.ar_vr import ARVRSimulator
from eosim.engine.native.simulators.camera import HomeCameraSimulator
from eosim.engine.native.simulators.construction import ConstructionSimulator
from eosim.engine.native.simulators.cybersecurity import CybersecuritySimulator
from eosim.engine.native.simulators.defense import DefenseSimulator
from eosim.engine.native.simulators.drone import DroneSimulator
from eosim.engine.native.simulators.education import EducationSimulator
from eosim.engine.native.simulators.elevator import ElevatorSimulator
from eosim.engine.native.simulators.energy import EnergySimulator
from eosim.engine.native.simulators.finance import FinanceSimulator
from eosim.engine.native.simulators.fisheries import FisheriesSimulator
from eosim.engine.native.simulators.forestry import ForestrySimulator
from eosim.engine.native.simulators.gaming import GamingSimulator
from eosim.engine.native.simulators.hvac import HVACSimulator
from eosim.engine.native.simulators.industrial import IndustrialSimulator
from eosim.engine.native.simulators.ios import IOSSimulator
from eosim.engine.native.simulators.iot import IoTSimulator
from eosim.engine.native.simulators.launch_vehicle import LaunchVehicleSimulator
from eosim.engine.native.simulators.logistics import LogisticsSimulator
from eosim.engine.native.simulators.maritime import MaritimeSimulator
from eosim.engine.native.simulators.media import MediaDeviceSimulator
from eosim.engine.native.simulators.medical import MedicalSimulator
from eosim.engine.native.simulators.mining import MiningSimulator
from eosim.engine.native.simulators.network import NetworkSimulator
from eosim.engine.native.simulators.nuclear import NuclearSimulator
from eosim.engine.native.simulators.oil_gas import OilGasSimulator
from eosim.engine.native.simulators.physiology import PhysiologySimulator
from eosim.engine.native.simulators.printer import PrinterSimulator
from eosim.engine.native.simulators.quantum import QuantumSimulator
from eosim.engine.native.simulators.railway import RailwaySimulator
from eosim.engine.native.simulators.retail import RetailSimulator
from eosim.engine.native.simulators.robot import RobotSimulator
from eosim.engine.native.simulators.rover import RoverSimulator
from eosim.engine.native.simulators.satellite import SatelliteSimulator
from eosim.engine.native.simulators.smart_city import SmartCitySimulator
from eosim.engine.native.simulators.smart_grid import SmartGridSimulator
from eosim.engine.native.simulators.speaker import SmartSpeakerSimulator
from eosim.engine.native.simulators.sports import SportsSimulator
from eosim.engine.native.simulators.submarine import SubmarineSimulator
from eosim.engine.native.simulators.telecom import TelecomSimulator
from eosim.engine.native.simulators.traffic import TrafficSimulator
from eosim.engine.native.simulators.v2x import AutomotiveV2XSimulator
from eosim.engine.native.simulators.vehicle import VehicleSimulator
from eosim.engine.native.simulators.water import WaterSimulator
from eosim.engine.native.simulators.wearable import WearableSimulator
from eosim.engine.native.simulators.weather import WeatherSimulator


class BaseSimulator:
    """Base class for all product simulators (fallback for unmapped types)."""

    PRODUCT_TYPE = 'generic'
    DISPLAY_NAME = 'Generic Simulator'

    def __init__(self, vm):
        self.vm = vm
        self.tick_count = 0
        self.state = {}

    def setup(self):
        pass

    def tick(self):
        self.tick_count += 1
        for name, dev in self.vm.peripherals.items():
            if hasattr(dev, 'simulate_tick'):
                dev.simulate_tick()

    def get_state(self) -> dict:
        return dict(self.state)

    def get_peripherals(self) -> dict:
        return dict(self.vm.peripherals)

    def get_status_text(self) -> str:
        return f"{self.DISPLAY_NAME} | Tick {self.tick_count}"

    def reset(self):
        self.tick_count = 0
        self.state = {}


SIMULATOR_MAP = {
    # Automotive
    'vehicle': VehicleSimulator,
    'automotive_ecu': VehicleSimulator,
    'ev_powertrain': VehicleSimulator,
    'adas_controller': VehicleSimulator,
    'electric_scooter': VehicleSimulator,
    # V2X
    'v2x': AutomotiveV2XSimulator,
    'v2x_rsu': AutomotiveV2XSimulator,
    # Drone
    'drone': DroneSimulator,
    'drone_controller': DroneSimulator,
    'ag_drone': DroneSimulator,
    # Robot
    'robot': RobotSimulator,
    'robot_controller': RobotSimulator,
    'surgical_robot': RobotSimulator,
    # Aircraft
    'aircraft': AircraftSimulator,
    'fixed_wing': AircraftSimulator,
    # Satellite
    'cubesat': SatelliteSimulator,
    'satellite': SatelliteSimulator,
    # Medical
    'medical': MedicalSimulator,
    'medical_monitor': MedicalSimulator,
    # Industrial
    'industrial': IndustrialSimulator,
    'industrial_plc': IndustrialSimulator,
    # IoT
    'iot': IoTSimulator,
    'iot_sensor': IoTSimulator,
    'smart_home_hub': IoTSimulator,
    # Energy
    'smart_meter': EnergySimulator,
    'energy': EnergySimulator,
    'solar_inverter': EnergySimulator,
    # Smart Grid
    'smart_grid': SmartGridSimulator,
    'power_distribution': SmartGridSimulator,
    'substation': SmartGridSimulator,
    # Wearable
    'wearable': WearableSimulator,
    'wearable_device': WearableSimulator,
    # Media
    'iptv_stb': MediaDeviceSimulator,
    'cast_device': MediaDeviceSimulator,
    'tv_os': MediaDeviceSimulator,
    'media_device': MediaDeviceSimulator,
    # Speaker / Camera
    'smart_speaker': SmartSpeakerSimulator,
    'google_mini': SmartSpeakerSimulator,
    'home_camera': HomeCameraSimulator,
    'spy_camera': HomeCameraSimulator,
    # Aerodynamics
    'aerodynamics': AerodynamicsSimulator,
    'wind_tunnel': AerodynamicsSimulator,
    'cfd_lab': AerodynamicsSimulator,
    # Physiology
    'physiology': PhysiologySimulator,
    'patient_model': PhysiologySimulator,
    # Finance
    'finance': FinanceSimulator,
    'stock_market': FinanceSimulator,
    'trading_sim': FinanceSimulator,
    # Weather
    'weather': WeatherSimulator,
    'weather_station_sim': WeatherSimulator,
    'atmosphere': WeatherSimulator,
    # Gaming
    'gaming': GamingSimulator,
    'game_world': GamingSimulator,
    'physics_sandbox': GamingSimulator,
    # Telecom
    'telecom': TelecomSimulator,
    'base_station_5g': TelecomSimulator,
    'lte_enodeb': TelecomSimulator,
    'network_switch': TelecomSimulator,
    # Defense
    'defense': DefenseSimulator,
    'tactical_radio': DefenseSimulator,
    'radar_system': DefenseSimulator,
    'missile_guidance': DefenseSimulator,
    # Submarine
    'submarine': SubmarineSimulator,
    'submarine_sim': SubmarineSimulator,
    'auv': SubmarineSimulator,
    # Network
    'network': NetworkSimulator,
    'router': NetworkSimulator,
    'firewall': NetworkSimulator,
    'sdn_controller': NetworkSimulator,
    # Smart City
    'smart_city': SmartCitySimulator,
    'traffic_light': SmartCitySimulator,
    'smart_parking': SmartCitySimulator,
    'street_lighting': SmartCitySimulator,
    # Railway
    'railway': RailwaySimulator,
    'train_control': RailwaySimulator,
    'signaling': RailwaySimulator,
    'ptc_system': RailwaySimulator,
    # Agriculture
    'agriculture': AgricultureSimulator,
    'irrigation': AgricultureSimulator,
    'tractor_ecu': AgricultureSimulator,
    'greenhouse': AgricultureSimulator,
    # Maritime
    'maritime': MaritimeSimulator,
    'ship_autopilot': MaritimeSimulator,
    'ais_transponder': MaritimeSimulator,
    'port_crane': MaritimeSimulator,
    # Mining
    'mining': MiningSimulator,
    'drill_controller': MiningSimulator,
    'mine_ventilation': MiningSimulator,
    'gas_detection': MiningSimulator,
    # Construction
    'construction': ConstructionSimulator,
    'crane_controller': ConstructionSimulator,
    'excavator': ConstructionSimulator,
    'concrete_pump': ConstructionSimulator,
    # Retail
    'retail': RetailSimulator,
    'pos_terminal': RetailSimulator,
    'smart_shelf': RetailSimulator,
    'vending_machine': RetailSimulator,
    # Education
    'education': EducationSimulator,
    'lab_equipment': EducationSimulator,
    'stem_kit': EducationSimulator,
    'coding_robot': EducationSimulator,
    # Nuclear
    'nuclear': NuclearSimulator,
    'reactor_control': NuclearSimulator,
    'radiation_monitor': NuclearSimulator,
    # Rover / Space
    'rover': RoverSimulator,
    'mars_rover': RoverSimulator,
    'lunar_rover': RoverSimulator,
    'exploration_bot': RoverSimulator,
    # Launch Vehicle
    'launch_vehicle': LaunchVehicleSimulator,
    'rocket_guidance': LaunchVehicleSimulator,
    'stage_separation': LaunchVehicleSimulator,
    # Printer
    'printer': PrinterSimulator,
    '3d_printer': PrinterSimulator,
    'laser_printer': PrinterSimulator,
    'inkjet_printer': PrinterSimulator,
    # HVAC
    'hvac': HVACSimulator,
    'hvac_controller': HVACSimulator,
    'thermostat': HVACSimulator,
    # Elevator
    'elevator': ElevatorSimulator,
    'lift_controller': ElevatorSimulator,
    'escalator': ElevatorSimulator,
    # Traffic
    'traffic': TrafficSimulator,
    'traffic_light_controller': TrafficSimulator,
    'speed_camera': TrafficSimulator,
    # Water
    'water': WaterSimulator,
    'water_treatment': WaterSimulator,
    'pump_station': WaterSimulator,
    # Oil & Gas
    'oil_gas': OilGasSimulator,
    'pipeline_scada': OilGasSimulator,
    'wellhead_controller': OilGasSimulator,
    # Logistics
    'logistics': LogisticsSimulator,
    'warehouse_robot': LogisticsSimulator,
    'conveyor_sort': LogisticsSimulator,
    # AR/VR
    'ar_vr': ARVRSimulator,
    'ar_glasses': ARVRSimulator,
    'vr_headset': ARVRSimulator,
    'haptic_controller': ARVRSimulator,
    # Cybersecurity
    'cybersecurity': CybersecuritySimulator,
    'firewall_appliance': CybersecuritySimulator,
    'ids_ips': CybersecuritySimulator,
    'hsm': CybersecuritySimulator,
    # Quantum
    'quantum': QuantumSimulator,
    'quantum_processor': QuantumSimulator,
    'error_correction': QuantumSimulator,
    # Sports
    'sports': SportsSimulator,
    'performance_tracker': SportsSimulator,
    'scoring_system': SportsSimulator,
    # Forestry
    'forestry': ForestrySimulator,
    'fire_detection': ForestrySimulator,
    'fire_detection_node': ForestrySimulator,
    'chainsaw_controller': ForestrySimulator,
    # Fisheries
    'fisheries': FisheriesSimulator,
    'sonar_finder': FisheriesSimulator,
    'fish_finder': FisheriesSimulator,
    'aquaculture': FisheriesSimulator,
    'aquaculture_controller': FisheriesSimulator,
    # Android
    'android': AndroidSimulator,
    'android_phone': AndroidSimulator,
    'android_tablet': AndroidSimulator,
    'android_tv_device': AndroidSimulator,
    'android_auto': AndroidSimulator,
    'android_wear': AndroidSimulator,
    # iOS
    'ios': IOSSimulator,
    'iphone': IOSSimulator,
    'ipad': IOSSimulator,
    'apple_watch': IOSSimulator,
    # Generic fallback
    'vbox_test': BaseSimulator,
}


class SimulatorFactory:
    """Factory to create the right simulator from a product template name."""

    @staticmethod
    def create(product_type: str, vm) -> 'BaseSimulator':
        cls = SIMULATOR_MAP.get(product_type, BaseSimulator)
        sim = cls(vm)
        sim.setup()
        return sim

    @staticmethod
    def list_simulators():
        return sorted(set(cls.PRODUCT_TYPE for cls in SIMULATOR_MAP.values()))
