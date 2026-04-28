# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""iOS embedded subsystem simulator.

Simulates the embedded hardware abstraction layer of Apple iOS devices:
CoreMotion sensors, power management (PMIC), display driver, camera ISP,
haptic engine (Taptic), Face ID / Touch ID, Ultra Wideband (U1), NFC,
and wireless controllers.

Pure Python, cross-platform (Linux/Windows/macOS). No OS-specific dependencies.
"""
import math
import random


class IOSSimulator:
    """iOS device embedded subsystem simulator.

    This does NOT emulate iOS itself (use Xcode Simulator for that).
    Instead it simulates the hardware subsystems that embedded firmware
    engineers work on: sensor fusion, PMIC, display DDIC, camera ISP,
    haptic driver, secure enclave, UWB, NFC, and wireless.
    """

    PRODUCT_TYPE = 'ios'
    DISPLAY_NAME = 'iOS Device'

    SCENARIOS = {
        'boot_sequence': {
            'description': 'iBoot → XNU kernel → SpringBoard launch',
        },
        'face_id_unlock': {
            'description': 'TrueDepth camera → IR dot projector → secure enclave verify',
        },
        'haptic_feedback': {
            'description': 'Taptic Engine feedback patterns (peek, pop, success, error)',
        },
        'camera_pipeline': {
            'description': 'ISP: RAW capture → Deep Fusion → Smart HDR → HEIF encode',
        },
        'power_management': {
            'description': 'Screen lock → background refresh → low power mode',
        },
        'uwb_ranging': {
            'description': 'U1 chip: AirTag ranging, precise find-my, spatial audio',
        },
        'nfc_payment': {
            'description': 'NFC: Apple Pay tap → secure element → payment auth',
        },
        'sensor_fusion': {
            'description': 'CoreMotion: accel + gyro + mag + baro → attitude estimation',
        },
    }

    def __init__(self, vm):
        self.vm = vm
        self.tick_count = 0
        self.state = {}
        self.scenario = ''
        self._scenario_step = 0

    def setup(self):
        from eosim.engine.native.peripherals.sensors import (
            IMUSensor, GPSModule, TemperatureSensor, PressureSensor,
            LightSensor, ProximitySensor,
        )
        from eosim.engine.native.peripherals.composites import BatteryManagement, WatchdogTimer

        self.vm.add_peripheral('imu0', IMUSensor('imu0', 0x40100200))
        self.vm.add_peripheral('gps0', GPSModule('gps0', 0x40100300))
        self.vm.add_peripheral('baro0', PressureSensor('baro0', 0x40100100))
        self.vm.add_peripheral('temp0', TemperatureSensor('temp0', 0x40100010, -10, 50))
        self.vm.add_peripheral('light0', LightSensor('light0', 0x40100500))
        self.vm.add_peripheral('prox0', ProximitySensor('prox0', 0x40100400, 3))
        self.vm.add_peripheral('bms0', BatteryManagement('bms0', 0x40500000, 3, 4352))
        self.vm.add_peripheral('wdt0', WatchdogTimer('wdt0', 0x40500200))

        self.state = {
            # Boot & system
            'boot_stage': 'off', 'uptime_s': 0, 'ios_version': '18.0',
            'soc': 'A17 Pro',
            # Display
            'screen_on': False, 'brightness_nits': 800, 'resolution': '1179x2556',
            'promotion_hz': 120, 'always_on': True, 'fps': 0,
            # Power
            'battery_pct': 80.0, 'charging': False, 'low_power_mode': False,
            'thermal_state': 'nominal', 'temperature_c': 30.0,
            # Sensors (CoreMotion)
            'accel_x': 0.0, 'accel_y': 0.0, 'accel_z': 9.81,
            'gyro_x': 0.0, 'gyro_y': 0.0, 'gyro_z': 0.0,
            'magnetometer_ut': 45.0, 'altitude_m': 0.0,
            'attitude_pitch': 0.0, 'attitude_roll': 0.0, 'attitude_yaw': 0.0,
            # Biometrics
            'face_id_enrolled': True, 'face_id_locked': True,
            'secure_enclave_ops': 0,
            # Camera
            'camera_active': False, 'camera_mode': 'photo',
            'deep_fusion_active': False, 'photos_taken': 0,
            # Haptics
            'haptic_pattern': 'none', 'haptic_intensity': 0,
            # Wireless
            'wifi_connected': False, 'wifi_rssi_dbm': -60,
            'ble_connected': False, 'uwb_ranging': False, 'uwb_distance_m': 0,
            'nfc_active': False, 'apple_pay_ready': False,
            'scenario': '',
        }

    def load_scenario(self, name):
        if name in self.SCENARIOS:
            self.scenario = name
            self._scenario_step = 0
            self.state['scenario'] = name

    def tick(self):
        self.tick_count += 1
        for name, dev in self.vm.peripherals.items():
            if hasattr(dev, 'simulate_tick'):
                dev.simulate_tick()
        self._apply_scenario()

        # Sensor fusion from peripherals
        imu = self.vm.peripherals.get('imu0')
        if imu:
            self.state['accel_x'] = round(imu.accel[0], 3)
            self.state['accel_y'] = round(imu.accel[1], 3)
            self.state['accel_z'] = round(imu.accel[2], 3)
            self.state['gyro_x'] = round(imu.gyro[0], 3)
            self.state['gyro_y'] = round(imu.gyro[1], 3)
            self.state['gyro_z'] = round(imu.gyro[2], 3)
            # Simple attitude estimation
            self.state['attitude_pitch'] = math.degrees(math.atan2(imu.accel[0], imu.accel[2]))
            self.state['attitude_roll'] = math.degrees(math.atan2(imu.accel[1], imu.accel[2]))

        baro = self.vm.peripherals.get('baro0')
        if baro:
            self.state['altitude_m'] = round(baro.altitude_m, 1)

        # Battery drain
        drain = 0.002
        if self.state['screen_on']:
            drain += 0.008
        if self.state['camera_active']:
            drain += 0.015
        if self.state['low_power_mode']:
            drain *= 0.6
        if not self.state['charging']:
            self.state['battery_pct'] = max(0, self.state['battery_pct'] - drain)
        else:
            self.state['battery_pct'] = min(100, self.state['battery_pct'] + 0.04)

        bms = self.vm.peripherals.get('bms0')
        if bms:
            bms.soc_percent = self.state['battery_pct']

        self.state['temperature_c'] += random.gauss(0, 0.03)
        self.state['temperature_c'] = max(15, min(45, self.state['temperature_c']))
        if self.state['temperature_c'] > 40:
            self.state['thermal_state'] = 'serious'
        elif self.state['temperature_c'] > 35:
            self.state['thermal_state'] = 'fair'
        else:
            self.state['thermal_state'] = 'nominal'

        self.state['uptime_s'] += 1
        if self.state['screen_on']:
            self.state['fps'] = self.state['promotion_hz'] - random.randint(0, 3)

    def _apply_scenario(self):
        if not self.scenario:
            return
        step = self._scenario_step

        if self.scenario == 'boot_sequence':
            if step == 0:
                self.state['boot_stage'] = 'iboot'
            elif step == 10:
                self.state['boot_stage'] = 'xnu_kernel'
            elif step == 25:
                self.state['boot_stage'] = 'hal_init'
            elif step == 40:
                self.state['boot_stage'] = 'springboard'
                self.state['screen_on'] = True

        elif self.scenario == 'face_id_unlock':
            if step == 0:
                self.state['screen_on'] = True
            elif step == 5:
                self.state['camera_active'] = True
                self.state['camera_mode'] = 'face_id'
            elif step == 10:
                self.state['secure_enclave_ops'] += 1
                self.state['face_id_locked'] = False
                self.state['camera_active'] = False

        elif self.scenario == 'haptic_feedback':
            patterns = ['peek', 'pop', 'success', 'error', 'warning', 'selection']
            if step % 8 == 0:
                self.state['haptic_pattern'] = patterns[step // 8 % len(patterns)]
                self.state['haptic_intensity'] = random.randint(50, 100)
            elif step % 8 == 3:
                self.state['haptic_pattern'] = 'none'
                self.state['haptic_intensity'] = 0

        elif self.scenario == 'camera_pipeline':
            if step == 0:
                self.state['camera_active'] = True
                self.state['camera_mode'] = 'photo'
            elif step == 5:
                self.state['deep_fusion_active'] = True
            elif step == 15:
                self.state['photos_taken'] += 1
                self.state['deep_fusion_active'] = False
            elif step == 25:
                self.state['camera_active'] = False

        elif self.scenario == 'power_management':
            if step == 5:
                self.state['screen_on'] = False
            elif step == 20:
                self.state['low_power_mode'] = True
            elif step == 50:
                self.state['screen_on'] = True
                self.state['low_power_mode'] = False

        elif self.scenario == 'uwb_ranging':
            self.state['uwb_ranging'] = True
            self.state['uwb_distance_m'] = max(0, 5.0 + random.gauss(0, 0.1) - step * 0.05)

        elif self.scenario == 'nfc_payment':
            if step == 5:
                self.state['nfc_active'] = True
            elif step == 10:
                self.state['apple_pay_ready'] = True
                self.state['secure_enclave_ops'] += 1
            elif step == 15:
                self.state['haptic_pattern'] = 'success'
                self.state['nfc_active'] = False

        elif self.scenario == 'sensor_fusion':
            imu = self.vm.peripherals.get('imu0')
            if imu:
                t = step * 0.1
                imu.set_accel(
                    math.sin(t) * 0.5,
                    math.cos(t) * 0.3,
                    9.81 + random.gauss(0, 0.01),
                )
                imu.set_gyro(
                    math.cos(t) * 5,
                    math.sin(t) * 3,
                    random.gauss(0, 0.5),
                )

        self._scenario_step += 1

    def get_state(self) -> dict:
        return dict(self.state)

    def get_peripherals(self) -> dict:
        return dict(self.vm.peripherals)

    def get_status_text(self) -> str:
        scn = f" [{self.scenario}]" if self.scenario else ""
        return f"{self.DISPLAY_NAME} | Tick {self.tick_count}{scn}"

    def reset(self):
        self.tick_count = 0
        self.state = {}
        self.scenario = ''
        self._scenario_step = 0
