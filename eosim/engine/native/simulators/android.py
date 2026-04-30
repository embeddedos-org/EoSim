# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""Android embedded subsystem simulator.

Simulates the embedded hardware abstraction layer (HAL) of Android devices:
sensor HAL, power management, touch controller, camera pipeline, display,
audio, telephony modem, NFC, and BLE/WiFi stacks.

Pure Python, cross-platform (Linux/Windows/macOS). No OS-specific dependencies.
"""
import math
import random


class AndroidSimulator:
    """Android device embedded subsystem simulator.

    This does NOT emulate the full Android OS (use Android Emulator for that).
    Instead it simulates the hardware subsystems that embedded firmware teams
    work on: sensor hub, power PMIC, touch IC, display driver, camera ISP,
    audio codec, modem baseband, and wireless controllers.
    """

    PRODUCT_TYPE = 'android'
    DISPLAY_NAME = 'Android Device'

    SCENARIOS = {
        'boot_sequence': {
            'description': 'Power-on → bootloader → kernel → Android HAL init',
        },
        'sensor_polling': {
            'description': 'Accelerometer + gyro + magnetometer polling at 200 Hz',
        },
        'camera_capture': {
            'description': 'Camera ISP pipeline: preview → capture → JPEG encode',
        },
        'power_management': {
            'description': 'Screen-off → doze → deep sleep → wake-on-motion',
        },
        'touch_interaction': {
            'description': 'Multi-touch event sequence with gesture recognition',
        },
        'connectivity_cycle': {
            'description': 'WiFi scan → connect → BLE advertise → NFC tap',
        },
        'telephony_call': {
            'description': 'Modem: network register → incoming call → audio route',
        },
        'ota_update': {
            'description': 'OTA firmware update: download → verify → flash → reboot',
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
            IMUSensor, GPSModule, TemperatureSensor, LightSensor, ProximitySensor,
        )
        from eosim.engine.native.peripherals.composites import BatteryManagement, WatchdogTimer

        self.vm.add_peripheral('imu0', IMUSensor('imu0', 0x40100200))
        self.vm.add_peripheral('gps0', GPSModule('gps0', 0x40100300))
        self.vm.add_peripheral('temp0', TemperatureSensor('temp0', 0x40100010, -10, 55))
        self.vm.add_peripheral('light0', LightSensor('light0', 0x40100500))
        self.vm.add_peripheral('prox0', ProximitySensor('prox0', 0x40100400, 5))
        self.vm.add_peripheral('bms0', BatteryManagement('bms0', 0x40500000, 4, 5000))
        self.vm.add_peripheral('wdt0', WatchdogTimer('wdt0', 0x40500200))

        self.state = {
            # Boot & system
            'boot_stage': 'off', 'uptime_s': 0, 'android_version': '15',
            # Display
            'screen_on': False, 'brightness_pct': 50, 'resolution': '1080x2400',
            'refresh_hz': 120, 'fps': 0,
            # Power
            'battery_pct': 85.0, 'charging': False, 'power_mode': 'normal',
            'current_ma': 0, 'temperature_c': 28.0,
            # Sensors
            'accel_x': 0.0, 'accel_y': 0.0, 'accel_z': 9.81,
            'gyro_x': 0.0, 'gyro_y': 0.0, 'gyro_z': 0.0,
            'light_lux': 300, 'proximity_cm': 5.0,
            # Camera
            'camera_active': False, 'camera_fps': 0, 'photos_taken': 0,
            # Connectivity
            'wifi_connected': False, 'wifi_rssi_dbm': -65,
            'ble_advertising': False, 'nfc_enabled': False,
            'cellular_signal_dbm': -85, 'cellular_network': '5G',
            # Touch
            'touch_points': 0, 'touch_x': 0, 'touch_y': 0,
            # Audio
            'audio_playing': False, 'volume_pct': 50,
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

        # Update sensor state from peripherals
        imu = self.vm.peripherals.get('imu0')
        if imu:
            self.state['accel_x'] = round(imu.accel[0], 3)
            self.state['accel_y'] = round(imu.accel[1], 3)
            self.state['accel_z'] = round(imu.accel[2], 3)

        light = self.vm.peripherals.get('light0')
        if light:
            self.state['light_lux'] = round(light.lux, 1)

        # Battery drain
        drain = 0.001 if self.state['power_mode'] == 'doze' else 0.005
        if self.state['screen_on']:
            drain += 0.01
        if self.state['camera_active']:
            drain += 0.02
        if not self.state['charging']:
            self.state['battery_pct'] = max(0, self.state['battery_pct'] - drain)
        else:
            self.state['battery_pct'] = min(100, self.state['battery_pct'] + 0.03)

        bms = self.vm.peripherals.get('bms0')
        if bms:
            bms.soc_percent = self.state['battery_pct']

        self.state['temperature_c'] += random.gauss(0, 0.05)
        self.state['temperature_c'] = max(15, min(45, self.state['temperature_c']))
        self.state['current_ma'] = drain * 1000
        self.state['uptime_s'] += 1

        if self.state['screen_on']:
            self.state['fps'] = self.state['refresh_hz'] - random.randint(0, 5)

    def _apply_scenario(self):
        if not self.scenario:
            return
        step = self._scenario_step

        if self.scenario == 'boot_sequence':
            if step == 0:
                self.state['boot_stage'] = 'bootloader'
            elif step == 10:
                self.state['boot_stage'] = 'kernel'
            elif step == 30:
                self.state['boot_stage'] = 'hal_init'
            elif step == 50:
                self.state['boot_stage'] = 'android_ready'
                self.state['screen_on'] = True

        elif self.scenario == 'sensor_polling':
            imu = self.vm.peripherals.get('imu0')
            if imu:
                # Simulate phone being held and tilted
                imu.set_accel(
                    random.gauss(0.1, 0.05),
                    random.gauss(-0.2, 0.05),
                    random.gauss(9.81, 0.02),
                )

        elif self.scenario == 'camera_capture':
            if step == 0:
                self.state['camera_active'] = True
                self.state['camera_fps'] = 30
            elif step == 20:
                self.state['photos_taken'] += 1
                self.state['camera_fps'] = 0
            elif step == 30:
                self.state['camera_active'] = False

        elif self.scenario == 'power_management':
            if step == 10:
                self.state['screen_on'] = False
            elif step == 30:
                self.state['power_mode'] = 'doze'
            elif step == 60:
                self.state['power_mode'] = 'deep_sleep'
            elif step == 80:
                self.state['power_mode'] = 'normal'
                self.state['screen_on'] = True

        elif self.scenario == 'touch_interaction':
            if step % 5 == 0:
                self.state['touch_points'] = random.randint(1, 3)
                self.state['touch_x'] = random.randint(0, 1080)
                self.state['touch_y'] = random.randint(0, 2400)
            else:
                self.state['touch_points'] = 0

        elif self.scenario == 'connectivity_cycle':
            if step == 5:
                self.state['wifi_connected'] = True
                self.state['wifi_rssi_dbm'] = -55 + random.gauss(0, 3)
            elif step == 20:
                self.state['ble_advertising'] = True
            elif step == 35:
                self.state['nfc_enabled'] = True

        elif self.scenario == 'telephony_call':
            if step == 5:
                self.state['cellular_signal_dbm'] = -75 + random.gauss(0, 5)
            elif step == 15:
                self.state['audio_playing'] = True
            elif step == 40:
                self.state['audio_playing'] = False

        elif self.scenario == 'ota_update':
            if step < 30:
                self.state['boot_stage'] = 'ota_downloading'
            elif step < 40:
                self.state['boot_stage'] = 'ota_verifying'
            elif step < 50:
                self.state['boot_stage'] = 'ota_flashing'
            elif step == 50:
                self.state['boot_stage'] = 'rebooting'
            elif step == 60:
                self.state['boot_stage'] = 'android_ready'

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
