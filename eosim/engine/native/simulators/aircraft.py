# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""Aircraft simulator — fixed-wing / helicopter with flight dynamics.

Pure Python, cross-platform. No OS-specific dependencies.
"""
import math


class AircraftSimulator:
    PRODUCT_TYPE = 'aircraft'
    DISPLAY_NAME = 'Aircraft'

    SCENARIOS = {
        'takeoff': {'description': 'Takeoff roll and initial climb'},
        'cruise': {'altitude_ft': 35000, 'airspeed_kts': 250, 'description': 'Level cruise flight'},
        'approach': {'altitude_ft': 3000, 'airspeed_kts': 140, 'description': 'Final approach'},
        'landing': {'description': 'Flare and touchdown'},
        'engine_failure': {'description': 'Single engine failure, maintain control'},
        'stall_recovery': {'description': 'Approach stall and recovery'},
        'autopilot_engage': {'description': 'Engage autopilot at current state'},
    }

    def __init__(self, vm):
        self.vm = vm
        self.tick_count = 0
        self.state = {}
        self.scenario = ''
        self._scenario_step = 0
        self._autopilot = False
        self._target_alt = 0
        self._target_speed = 0

    def setup(self):
        from eosim.engine.native.peripherals.actuators import ServoController, ThrottleActuator
        from eosim.engine.native.peripherals.buses import ARINC429
        from eosim.engine.native.peripherals.sensors import GPSModule, IMUSensor, PressureSensor

        self.vm.add_peripheral('imu0', IMUSensor('imu0', 0x40100200, 9))
        self.vm.add_peripheral('gps0', GPSModule('gps0', 0x40100300))
        self.vm.add_peripheral('baro0', PressureSensor('baro0', 0x40100100))
        self.vm.add_peripheral('servo0', ServoController('servo0', 0x40200100, 4))
        self.vm.add_peripheral('throttle', ThrottleActuator('throttle', 0x40200900))
        self.vm.add_peripheral('arinc0', ARINC429('arinc0', 0x40300400))

        self.state = {
            'altitude_ft': 0, 'airspeed_kts': 0, 'heading_deg': 0,
            'roll_deg': 0, 'pitch_deg': 0, 'vs_fpm': 0, 'aoa_deg': 2.0,
            'throttle_pct': 0, 'flaps_deg': 0, 'gear_down': True,
            'autopilot': False, 'stall_warning': False,
            'lift_n': 0, 'drag_n': 0, 'scenario': '',
        }

    def load_scenario(self, name: str):
        if name not in self.SCENARIOS:
            return
        self.scenario = name
        self._scenario_step = 0
        self.state['scenario'] = name

        if name == 'takeoff':
            self.state['altitude_ft'] = 0
            self.state['airspeed_kts'] = 0
            self.state['gear_down'] = True
            self.state['flaps_deg'] = 10
        elif name == 'cruise':
            cfg = self.SCENARIOS[name]
            self._target_alt = cfg['altitude_ft']
            self._target_speed = cfg['airspeed_kts']
            self._autopilot = True
            self.state['autopilot'] = True
        elif name == 'approach':
            cfg = self.SCENARIOS[name]
            self._target_alt = cfg['altitude_ft']
            self._target_speed = cfg['airspeed_kts']
            self.state['flaps_deg'] = 20
            self.state['gear_down'] = True
        elif name == 'engine_failure':
            self.state['throttle_pct'] = 0
        elif name == 'stall_recovery':
            self.state['aoa_deg'] = 14.0
        elif name == 'autopilot_engage':
            self._autopilot = True
            self.state['autopilot'] = True
            self._target_alt = self.state.get('altitude_ft', 10000)
            self._target_speed = self.state.get('airspeed_kts', 200)

    def tick(self):
        self.tick_count += 1
        for _, dev in self.vm.peripherals.items():
            if hasattr(dev, 'simulate_tick'):
                dev.simulate_tick()

        throttle = self.vm.peripherals.get('throttle')
        baro = self.vm.peripherals.get('baro0')
        servo = self.vm.peripherals.get('servo0')
        imu = self.vm.peripherals.get('imu0')
        gps = self.vm.peripherals.get('gps0')

        self._apply_scenario(throttle, servo)

        thr_pct = throttle.position_pct if throttle else 0
        self.state['throttle_pct'] = round(thr_pct, 1)
        thrust = thr_pct * 50
        speed = self.state.get('airspeed_kts', 0)
        aoa = self.state.get('aoa_deg', 2.0)

        cl = 0.1 + 0.1 * aoa
        cd = 0.02 + 0.005 * aoa * aoa
        q = 0.5 * 1.225 * (speed * 0.5144) ** 2
        wing_area = 30.0
        lift = cl * q * wing_area
        drag = cd * q * wing_area
        self.state['lift_n'] = round(lift, 0)
        self.state['drag_n'] = round(drag, 0)

        net_force = thrust - drag
        speed = max(0, speed + net_force * 0.0001)
        self.state['airspeed_kts'] = round(speed, 1)

        stall_speed = 60
        self.state['stall_warning'] = speed < stall_speed * 1.1 and speed > 0

        pitch = self.state.get('pitch_deg', 0)
        vs = pitch * speed * 0.3
        self.state['vs_fpm'] = round(vs, 0)
        alt = self.state.get('altitude_ft', 0) + vs / 60 * 0.1
        self.state['altitude_ft'] = max(0, round(alt, 0))

        if servo:
            self.state['roll_deg'] = round((servo.positions[0] - 90) * 2, 1)
            self.state['pitch_deg'] = round((servo.positions[1] - 90) * 1.5, 1)
            self.state['flaps_deg'] = round(max(0, servo.positions[3] - 90), 1)
            heading = self.state.get('heading_deg', 0)
            heading += self.state['roll_deg'] * 0.05
            self.state['heading_deg'] = round(heading % 360, 1)

        if baro:
            baro.set_altitude(self.state['altitude_ft'] * 0.3048)
        if imu:
            imu.set_accel(
                math.sin(math.radians(self.state.get('pitch_deg', 0))) * 9.81,
                math.sin(math.radians(self.state.get('roll_deg', 0))) * 9.81,
                9.81 * math.cos(math.radians(self.state.get('pitch_deg', 0))))
        if gps:
            gps.speed_mps = speed * 0.5144
            gps.heading_deg = self.state['heading_deg']

        self._scenario_step += 1

    def _apply_scenario(self, throttle, servo):
        if not self.scenario:
            if self._autopilot:
                self._autopilot_control(throttle, servo)
            return

        if self.scenario == 'takeoff':
            if self._scenario_step < 50:
                if throttle:
                    throttle.target_pct = 100
            elif self.state['airspeed_kts'] > 70:
                if servo:
                    servo.set_target(1, 100)
                self.state['gear_down'] = False

        elif self.scenario == 'cruise' or self.scenario == 'autopilot_engage':
            self._autopilot_control(throttle, servo)

        elif self.scenario == 'approach':
            if throttle:
                speed_err = self._target_speed - self.state.get('airspeed_kts', 0)
                throttle.target_pct = max(0, min(100, 30 + speed_err * 2))
            if servo:
                alt_err = self._target_alt - self.state.get('altitude_ft', 0)
                pitch = 90 + max(-10, min(10, alt_err * 0.01))
                servo.set_target(1, pitch)

        elif self.scenario == 'engine_failure':
            if throttle:
                throttle.target_pct = 0
            if servo:
                servo.set_target(1, 85)

        elif self.scenario == 'stall_recovery':
            if self.state.get('stall_warning', False):
                if servo:
                    servo.set_target(1, 80)
                if throttle:
                    throttle.target_pct = 100
                self.state['aoa_deg'] = max(2, self.state.get('aoa_deg', 14) - 0.5)

        elif self.scenario == 'landing':
            if throttle:
                throttle.target_pct = max(0, throttle.position_pct - 0.5)
            self.state['gear_down'] = True
            if servo:
                servo.set_target(3, 120)

    def _autopilot_control(self, throttle, servo):
        if throttle:
            speed_err = self._target_speed - self.state.get('airspeed_kts', 0)
            throttle.target_pct = max(0, min(100, 50 + speed_err * 1.5))
        if servo:
            alt_err = self._target_alt - self.state.get('altitude_ft', 0)
            pitch = 90 + max(-10, min(10, alt_err * 0.005))
            servo.set_target(1, pitch)
            servo.set_target(0, 90)

    def get_state(self) -> dict:
        return dict(self.state)

    def get_peripherals(self) -> dict:
        return dict(self.vm.peripherals)

    def get_status_text(self) -> str:
        alt = self.state.get('altitude_ft', 0)
        spd = self.state.get('airspeed_kts', 0)
        return f"{self.DISPLAY_NAME} | ALT {alt}ft | {spd}kts | Tick {self.tick_count}"

    def reset(self):
        self.tick_count = 0
        self.state = {}
        self.scenario = ''
        self._autopilot = False
