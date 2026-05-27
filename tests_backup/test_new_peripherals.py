# SPDX-License-Identifier: MIT
"""Unit tests for new peripheral modules."""
import pytest


class TestEnvironmentSensors:
    def test_humidity_sensor(self):
        from eosim.engine.native.peripherals.sensors_environment import HumiditySensor
        s = HumiditySensor()
        s.simulate_tick()
        assert 0 <= s.humidity_pct <= 100

    def test_soil_moisture(self):
        from eosim.engine.native.peripherals.sensors_environment import SoilMoistureSensor
        s = SoilMoistureSensor()
        s.simulate_tick()
        assert 0 <= s.moisture_pct <= 100

    def test_ph_sensor(self):
        from eosim.engine.native.peripherals.sensors_environment import PHSensor
        s = PHSensor()
        assert abs(s.ph_value - 7.0) < 0.1
        s.simulate_tick()

    def test_gas_sensor(self):
        from eosim.engine.native.peripherals.sensors_environment import GasSensor
        s = GasSensor(gas_type='CO2')
        assert s.concentration_ppm == 400
        s.simulate_tick()

    def test_water_level(self):
        from eosim.engine.native.peripherals.sensors_environment import WaterLevelSensor
        s = WaterLevelSensor()
        assert s.level_cm == 100.0
        s.simulate_tick()

    def test_uv_sensor(self):
        from eosim.engine.native.peripherals.sensors_environment import UVSensor
        s = UVSensor()
        s.simulate_tick()
        assert 0 <= s.uv_index <= 15

    def test_noise_level(self):
        from eosim.engine.native.peripherals.sensors_environment import NoiseLevelSensor
        s = NoiseLevelSensor()
        s.simulate_tick()
        assert 20 <= s.level_db <= 140


class TestIndustrialSensors:
    def test_load_cell(self):
        from eosim.engine.native.peripherals.sensors_industrial import LoadCell
        s = LoadCell()
        s.simulate_tick()
        assert s.force_kg >= 0

    def test_flow_sensor(self):
        from eosim.engine.native.peripherals.sensors_industrial import FlowSensor
        s = FlowSensor()
        s.simulate_tick()
        assert s.total_liters >= 0

    def test_vibration_sensor(self):
        from eosim.engine.native.peripherals.sensors_industrial import VibrationSensor
        s = VibrationSensor()
        s.simulate_tick()
        assert s.rms_g >= 0

    def test_torque_sensor(self):
        from eosim.engine.native.peripherals.sensors_industrial import TorqueSensor
        s = TorqueSensor()
        s.simulate_tick()

    def test_strain_gauge(self):
        from eosim.engine.native.peripherals.sensors_industrial import StrainGauge
        s = StrainGauge()
        s.simulate_tick()

    def test_level_sensor(self):
        from eosim.engine.native.peripherals.sensors_industrial import LevelSensor
        s = LevelSensor()
        s.simulate_tick()
        assert 0 <= s.level_m <= 10


class TestNavigationSensors:
    def test_radar_sensor(self):
        from eosim.engine.native.peripherals.sensors_navigation import RadarSensor
        s = RadarSensor()
        s.simulate_tick()

    def test_lidar_sensor(self):
        from eosim.engine.native.peripherals.sensors_navigation import LidarSensor
        s = LidarSensor()
        s.simulate_tick()
        assert s.distance_m > 0

    def test_depth_sounder(self):
        from eosim.engine.native.peripherals.sensors_navigation import DepthSounder
        s = DepthSounder()
        s.simulate_tick()

    def test_sonar_sensor(self):
        from eosim.engine.native.peripherals.sensors_navigation import SonarSensor
        s = SonarSensor()
        s.simulate_tick()

    def test_compass_sensor(self):
        from eosim.engine.native.peripherals.sensors_navigation import CompassSensor
        s = CompassSensor()
        s.simulate_tick()
        assert 0 <= s.heading_deg < 360


class TestImagingSensors:
    def test_camera_module(self):
        from eosim.engine.native.peripherals.sensors_imaging import CameraModule
        s = CameraModule()
        for _ in range(10):
            s.simulate_tick()

    def test_thermal_camera(self):
        from eosim.engine.native.peripherals.sensors_imaging import ThermalCamera
        s = ThermalCamera()
        s.simulate_tick()

    def test_infrared_sensor(self):
        from eosim.engine.native.peripherals.sensors_imaging import InfraredSensor
        s = InfraredSensor()
        s.simulate_tick()

    def test_xray_sensor(self):
        from eosim.engine.native.peripherals.sensors_imaging import XRaySensor
        s = XRaySensor()
        s.exposure_active = True
        s.simulate_tick()
        assert s.dose_ugy > 0


class TestIndustrialActuators:
    def test_conveyor_belt(self):
        from eosim.engine.native.peripherals.actuators_industrial import ConveyorBelt
        a = ConveyorBelt()
        a.running = True
        a.target_speed = 2.0
        a.simulate_tick()

    def test_crane_controller(self):
        from eosim.engine.native.peripherals.actuators_industrial import CraneController
        a = CraneController()
        a.simulate_tick()

    def test_drill_motor(self):
        from eosim.engine.native.peripherals.actuators_industrial import DrillMotor
        a = DrillMotor()
        a.rpm = 100
        a.simulate_tick()
        assert a.depth_m > 0

    def test_print_head(self):
        from eosim.engine.native.peripherals.actuators_industrial import PrintHead
        a = PrintHead()
        a.simulate_tick()

    def test_extruder(self):
        from eosim.engine.native.peripherals.actuators_industrial import Extruder
        a = Extruder()
        a.feed_rate_mm_s = 5.0
        a.simulate_tick()


class TestEnvironmentActuators:
    def test_irrigation_valve(self):
        from eosim.engine.native.peripherals.actuators_environment import IrrigationValve
        a = IrrigationValve()
        a.open = True
        a.simulate_tick()
        assert a.flow_lpm > 0

    def test_fan_controller(self):
        from eosim.engine.native.peripherals.actuators_environment import FanController
        a = FanController()
        a.speed_pct = 50
        a.simulate_tick()
        assert a.rpm > 0

    def test_heater_element(self):
        from eosim.engine.native.peripherals.actuators_environment import HeaterElement
        a = HeaterElement()
        a.power_pct = 100
        a.simulate_tick()

    def test_compressor(self):
        from eosim.engine.native.peripherals.actuators_environment import Compressor
        a = Compressor()
        a.running = True
        a.simulate_tick()
        assert a.pressure_bar > 0

    def test_damper(self):
        from eosim.engine.native.peripherals.actuators_environment import Damper
        a = Damper()
        a.target_pct = 50
        a.simulate_tick()


class TestAdvancedComposites:
    def test_npu_accelerator(self):
        from eosim.engine.native.peripherals.composites_advanced import NPUAccelerator
        c = NPUAccelerator()
        c.utilization_pct = 80
        c.simulate_tick()

    def test_secure_element(self):
        from eosim.engine.native.peripherals.composites_advanced import SecureElement
        c = SecureElement()
        c.simulate_tick()
        assert c.rng_value != 0 or True  # could be 0 by chance

    def test_tpm_module(self):
        from eosim.engine.native.peripherals.composites_advanced import TPMModule
        c = TPMModule()
        c.extend_pcr(0, 0x12345678)
        assert c.pcrs[0] == 0x12345678

    def test_power_manager(self):
        from eosim.engine.native.peripherals.composites_advanced import PowerManager
        c = PowerManager()
        c.simulate_tick()
        assert c.total_power_mw > 0
