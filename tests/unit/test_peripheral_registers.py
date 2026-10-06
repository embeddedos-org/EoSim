# SPDX-License-Identifier: MIT
"""Register-level behaviour of the native engine's peripheral models.

Each test drives a device through its memory-mapped interface (``io_handler``
or ``read_reg``/``write_reg``) and checks the register values and state
transitions the device is documented to produce.
"""

import logging
import random
from types import SimpleNamespace

import pytest

from eosim.engine.native.peripherals import (
    GPIODevice,
    I2CDevice,
    InterruptController,
    SPIDevice,
    TimerDevice,
    UARTDevice,
    buses,
)
from eosim.engine.native.peripherals import actuators as act
from eosim.engine.native.peripherals import composites as comp
from eosim.engine.native.peripherals import sensors as sens
from eosim.engine.native.peripherals import wireless as wl

MASK32 = 0xFFFFFFFF


def u32(value: int) -> int:
    return value & MASK32


@pytest.fixture(autouse=True)
def _seed_random():
    random.seed(1234)


# --- Core SoC peripherals --------------------------------------------------


class TestUART:
    def test_tx_register_emits_7bit_char_to_buffers_and_callback(self):
        uart = UARTDevice()
        seen = []
        uart.on_tx = seen.append
        uart.io_handler("write32", uart.base + 0x00, 0x1C1)  # 0x1C1 & 0x7F == 'A'
        uart.io_handler("write32", uart.base + 0x00, ord("b"))
        assert uart.tx_buffer == ["A", "b"]
        assert seen == ["A", "b"]
        assert uart.get_output() == "Ab"

    def test_status_register_reflects_rx_ready_and_enable(self):
        uart = UARTDevice()
        assert uart.read_reg(0x04) == 0b010  # TX always ready
        uart.write_reg(0x04, 1)
        assert uart.read_reg(0x04) == 0b110
        uart.inject_input("hi")
        assert uart.read_reg(0x04) == 0b111

    def test_rx_register_pops_fifo_then_reads_zero(self):
        uart = UARTDevice()
        uart.inject_input("ok")
        assert uart.io_handler("read32", uart.base, 0) == ord("o")
        assert uart.io_handler("read32", uart.base, 0) == ord("k")
        assert uart.io_handler("read32", uart.base, 0) == 0
        assert uart.read_reg(0x04) & 1 == 0

    def test_baud_register_and_unknown_offset(self):
        uart = UARTDevice()
        uart.write_reg(0x08, 9600)
        assert uart.baud == 9600
        assert uart.read_reg(0x10) == 0


class TestGPIO:
    def test_direction_and_output_registers_round_trip(self):
        gpio = GPIODevice()
        gpio.io_handler("write32", gpio.base + 0x00, 0x0F)
        gpio.io_handler("write32", gpio.base + 0x04, 0x05)
        assert gpio.io_handler("read32", gpio.base + 0x00, 0) == 0x0F
        assert gpio.io_handler("read32", gpio.base + 0x04, 0) == 0x05
        assert gpio.read_reg(0x20) == 0

    def test_input_edge_sets_pending_only_for_masked_pins(self):
        gpio = GPIODevice()
        gpio.write_reg(0x08, 1 << 3)  # irq mask
        gpio.set_input(3, True)
        gpio.set_input(5, True)
        assert gpio.read_reg(0x08) == (1 << 3) | (1 << 5)  # offset 0x08 reads inputs
        assert gpio.read_reg(0x0C) == 1 << 3

    def test_pending_is_write_one_to_clear(self):
        gpio = GPIODevice()
        gpio.write_reg(0x08, 0b11)
        gpio.set_input(0, True)
        gpio.set_input(1, True)
        gpio.write_reg(0x0C, 0b01)
        assert gpio.read_reg(0x0C) == 0b10

    def test_clearing_an_input_drops_its_bit(self):
        gpio = GPIODevice()
        gpio.set_input(7, True)
        gpio.set_input(7, False)
        assert gpio.input_val == 0
        assert gpio.irq_pending == 0  # pin 7 is not masked


class TestTimer:
    def test_reload_counts_down_and_raises_irq(self):
        timer = TimerDevice()
        fired = []
        timer.on_irq = lambda: fired.append(timer.counter)
        timer.io_handler("write32", timer.base + 0x00, 3)
        timer.io_handler("write32", timer.base + 0x04, 0b11)
        assert timer.read_reg(0x04) == 0b11
        timer.tick()
        timer.tick()
        assert timer.read_reg(0x00) == 1
        assert timer.read_reg(0x0C) == 0
        timer.tick()
        assert timer.read_reg(0x00) == 3  # reloaded
        assert timer.read_reg(0x0C) == 1
        assert fired == [3]

    def test_irq_pending_cleared_by_write(self):
        timer = TimerDevice()
        timer.write_reg(0x00, 1)
        timer.write_reg(0x04, 0b11)
        timer.tick()
        timer.write_reg(0x0C, 1)
        assert timer.read_reg(0x0C) == 0

    def test_disabled_timer_does_not_count(self):
        timer = TimerDevice()
        timer.write_reg(0x00, 5)
        timer.tick()
        assert timer.counter == 5

    def test_expiry_without_irq_enable_only_reloads(self):
        timer = TimerDevice()
        timer.write_reg(0x00, 1)
        timer.write_reg(0x04, 0b01)
        timer.tick()
        assert timer.counter == 1
        assert timer.irq_pending is False

    def test_prescaler_minimum_is_one(self):
        timer = TimerDevice()
        timer.write_reg(0x08, 0)
        assert timer.read_reg(0x08) == 1
        timer.write_reg(0x08, 8)
        assert timer.read_reg(0x08) == 8
        assert timer.read_reg(0x10) == 0


class TestSPI:
    def test_transfer_loops_back_inverted_byte(self):
        spi = SPIDevice()
        spi.io_handler("write32", spi.base + 0x04, 1)
        spi.io_handler("write32", spi.base + 0x00, 0x5A)
        assert spi.read_reg(0x04) == 0b11
        assert spi.io_handler("read32", spi.base + 0x00, 0) == 0xA5
        assert spi.read_reg(0x04) == 0b01  # reading data clears transfer-complete

    def test_clock_divider_and_slave_select(self):
        spi = SPIDevice()
        spi.write_reg(0x08, 0)
        spi.write_reg(0x0C, 0xFE)
        assert spi.clock_div == 1
        assert spi.slave_select == 0xFE
        assert spi.read_reg(0x0C) == 0


class TestI2C:
    def test_ack_from_registered_slave(self):
        i2c = I2CDevice()
        i2c.add_slave(0x50, lambda v: v + 1)
        i2c.io_handler("write32", i2c.base + 0x00, 0xD0)  # 7-bit masked to 0x50
        i2c.io_handler("write32", i2c.base + 0x04, 7)
        assert i2c.read_reg(0x00) == 0x50
        assert i2c.io_handler("read32", i2c.base + 0x04, 0) == 8
        assert i2c.read_reg(0x08) == 1

    def test_nack_from_missing_slave(self):
        i2c = I2CDevice()
        i2c.write_reg(0x00, 0x51)
        i2c.write_reg(0x04, 1)
        assert i2c.read_reg(0x08) == 2
        assert i2c.read_reg(0x04) == 0

    def test_enable_register(self):
        i2c = I2CDevice()
        i2c.write_reg(0x08, 1)
        assert i2c.enabled is True
        assert i2c.read_reg(0x0C) == 0


class TestInterruptController:
    def test_highest_pending_uses_lowest_priority_number(self):
        nvic = InterruptController()
        for irq, prio in ((5, 3), (9, 1)):
            nvic.enable_irq(irq)
            nvic.priority[irq] = prio
            nvic.trigger(irq)
        assert nvic.get_highest_pending() == 9
        nvic.acknowledge(9)
        assert nvic.get_highest_pending() == 5

    def test_trigger_ignored_for_disabled_irq(self):
        nvic = InterruptController()
        nvic.trigger(7)
        assert nvic.pending[7] is False
        assert nvic.get_highest_pending() == -1

    def test_disabling_masks_pending_irq(self):
        nvic = InterruptController()
        nvic.enable_irq(2)
        nvic.trigger(2)
        nvic.disable_irq(2)
        assert nvic.pending[2] is True
        assert nvic.get_highest_pending() == -1

    def test_out_of_range_irqs_are_ignored(self):
        nvic = InterruptController(irq_count=4)
        nvic.enable_irq(10)
        nvic.trigger(-1)
        nvic.acknowledge(99)
        nvic.disable_irq(4)
        assert nvic.enabled == [False] * 4
        assert nvic.pending == [False] * 4


# --- Sensors ----------------------------------------------------------------


class TestSensorBase:
    def test_unhandled_access_reads_zero_and_logs_write(self, caplog):
        s = sens.SensorBase("probe", 0x1000)
        with caplog.at_level(logging.DEBUG, logger=sens.__name__):
            assert s.io_handler("write32", 0x1004, 0xAB) == 0
        assert s.io_handler("read32", 0x1004, 0) == 0
        assert "probe: unhandled write offset=0x04 val=0x000000ab" in caplog.text

    def test_tick_counter(self):
        s = sens.SensorBase("probe", 0)
        s.simulate_tick()
        s.simulate_tick()
        assert s._tick_count == 2


class TestTemperatureSensor:
    def test_registers_report_centi_units(self):
        t = sens.TemperatureSensor()
        t.set_value(25.5, 60.25)
        assert t.io_handler("read32", t.base + 0x00, 0) == 2550
        assert t.read_reg(0x04) == 6025

    def test_negative_temperature_is_twos_complement(self):
        t = sens.TemperatureSensor()
        t.set_value(-10.25)
        assert t.read_reg(0x00) == u32(-1025)
        assert t.humidity == 45.0  # humidity left untouched

    def test_enable_register(self):
        t = sens.TemperatureSensor()
        t.io_handler("write32", t.base + 0x08, 1)
        assert t.read_reg(0x08) == 1
        t.write_reg(0x00, 1)  # read-only data register
        assert t.temperature == 22.0
        assert t.read_reg(0x0C) == 0

    def test_tick_clamps_to_range(self):
        t = sens.TemperatureSensor(min_c=0, max_c=10)
        t.set_value(10.0, 100.0)
        t._drift = 5.0
        for _ in range(20):
            t.simulate_tick()
            assert 0 <= t.temperature <= 10
            assert 0 <= t.humidity <= 100


class TestPressureSensor:
    def test_pressure_to_altitude(self):
        p = sens.PressureSensor()
        p.set_value(100.0)
        assert p.read_reg(0x00) == 100000
        assert p.altitude_m == pytest.approx(110.9, abs=0.5)
        assert 11040 <= p.read_reg(0x04) <= 11140

    def test_altitude_to_pressure_round_trip(self):
        p = sens.PressureSensor()
        p.set_altitude(1000.0)
        assert p.pressure_kpa == pytest.approx(89.88, abs=0.05)
        p.set_value(p.pressure_kpa)
        assert p.altitude_m == pytest.approx(1000.0, abs=1.0)
        assert p.read_reg(0x08) == 0

    def test_tick_keeps_altitude_consistent_with_pressure(self):
        p = sens.PressureSensor()
        p.simulate_tick()
        expected = 44330 * (1 - (p.pressure_kpa / 101.325) ** 0.1903)
        assert p.altitude_m == pytest.approx(expected)


class TestIMUSensor:
    def test_axis_registers_in_milli_units(self):
        imu = sens.IMUSensor()
        imu.set_accel(1.5, -2.0, 9.5)
        imu.set_gyro(0.25, 0.0, -0.5)
        imu.set_mag(0.5, 0.0, 0.75)
        regs = [imu.read_reg(i * 4) for i in range(9)]
        assert regs == [1500, u32(-2000), 9500, 250, 0, u32(-500), 500, 0, 750]
        assert imu.read_reg(0x24) == 0

    def test_gyro_decays_towards_zero_when_idle(self):
        imu = sens.IMUSensor()
        imu.set_gyro(100.0, 100.0, 100.0)
        for _ in range(200):
            imu.simulate_tick()
        assert all(abs(g) < 10 for g in imu.gyro)


class TestGPSModule:
    def test_position_registers(self):
        gps = sens.GPSModule()
        gps.set_position(37.5, -122.25, 12.5)
        gps.speed_mps = 2.5
        gps.heading_deg = 90.0
        assert gps.read_reg(0x00) == 375_000_000
        assert gps.read_reg(0x04) == u32(-1_222_500_000)
        assert gps.read_reg(0x08) == 1250
        assert gps.read_reg(0x0C) == 250
        assert gps.read_reg(0x10) == 9000
        assert gps.read_reg(0x14) == 8
        assert gps.read_reg(0x18) == 1
        assert gps.read_reg(0x1C) == 0

    @pytest.mark.parametrize("heading, moves_lat", [(0.0, True), (90.0, False)])
    def test_motion_follows_heading(self, heading, moves_lat):
        gps = sens.GPSModule()
        gps.set_position(10.0, 20.0)
        gps.speed_mps = 100.0
        gps.heading_deg = heading
        for _ in range(100):
            gps.simulate_tick()
        dlat, dlon = gps.latitude - 10.0, gps.longitude - 20.0
        if moves_lat:
            assert dlat > 5e-4 and abs(dlon) < 1e-4
        else:
            assert dlon > 5e-4 and abs(dlat) < 1e-4


class TestProximityLightADC:
    def test_proximity_detection_threshold(self):
        prox = sens.ProximitySensor(max_range_cm=400)
        prox.set_value(50)
        assert prox.read_reg(0x00) == 500
        assert prox.read_reg(0x04) == 1
        prox.set_value(390)
        assert prox.read_reg(0x04) == 0
        assert prox.read_reg(0x08) == 0

    def test_proximity_tick_clamps_minimum_distance(self):
        prox = sens.ProximitySensor()
        prox.set_value(2)
        for _ in range(20):
            prox.simulate_tick()
            assert prox.distance_cm >= 2

    def test_light_registers_and_non_negative(self):
        light = sens.LightSensor()
        light.set_value(1234.5)
        assert light.read_reg(0x00) == 123450
        assert light.read_reg(0x04) == 10000
        assert light.read_reg(0x08) == 0
        light.set_value(0.0)
        for _ in range(20):
            light.simulate_tick()
            assert light.lux >= 0

    def test_adc_raw_values_clamp_to_resolution(self):
        adc = sens.ADCChannel(resolution=12)
        adc.set_channel(2, 5000)
        adc.set_channel(1, -5)
        adc.set_channel(8, 1)  # out of range, ignored
        assert adc.read_reg(0x08) == 4095
        assert adc.read_reg(0x04) == 0
        assert adc.read_reg(0x20) == 0

    def test_adc_voltage_conversion(self):
        adc = sens.ADCChannel(resolution=12)
        adc.set_voltage(0, 1650)
        adc.set_voltage(-1, 1000)  # ignored
        assert adc.read_reg(0x00) == 2047
        assert adc.values[1:] == [0] * 7


class TestPowerAndMedicalSensors:
    def test_current_sensor_registers(self):
        ina = sens.CurrentSensor()
        ina.set_value(250.0, 5000.0)
        assert ina.read_reg(0x00) == 25000
        assert ina.read_reg(0x04) == 5000
        assert ina.read_reg(0x08) == 125000
        assert ina.read_reg(0x0C) == 0

    def test_current_sensor_power_uses_pre_noise_current(self):
        ina = sens.CurrentSensor()
        ina.set_value(250.0, 5000.0)
        ina.simulate_tick()
        assert ina.power_mw == 1250.0
        assert ina.current_ma >= 0

    def test_ecg_heart_rate_clamped(self):
        ecg = sens.ECGSensor()
        ecg.set_heart_rate(300)
        assert ecg.read_reg(0x00) == 250
        ecg.set_heart_rate(10)
        assert ecg.read_reg(0x00) == 30
        assert ecg.read_reg(0x08) == 95
        assert ecg.read_reg(0x0C) == 3
        assert ecg.read_reg(0x10) == 0

    def test_ecg_waveform_contains_r_peak(self):
        ecg = sens.ECGSensor()
        ecg.set_heart_rate(60)
        for _ in range(120):
            ecg.simulate_tick()
        assert len(ecg.waveform) == 256
        assert 0.85 < max(ecg.waveform) < 1.1
        assert ecg.read_reg(0x04) == u32(int(ecg.waveform[-1] * 1000))

    def test_pulse_oximeter_registers(self):
        ox = sens.PulseOximeter()
        ox.set_value(95.5, 80)
        assert ox.read_reg(0x00) == 9550
        assert ox.read_reg(0x04) == 80
        ox.set_value(90.0)  # pulse omitted keeps the previous value
        assert ox.read_reg(0x04) == 80
        assert ox.read_reg(0x08) == 90
        assert ox.read_reg(0x0C) == 0

    def test_pulse_oximeter_tick_clamps(self):
        ox = sens.PulseOximeter()
        ox.set_value(100.0, 200)
        for _ in range(20):
            ox.simulate_tick()
            assert 70 <= ox.spo2_percent <= 100
            assert 40 <= ox.pulse_rate <= 200


# --- Actuators --------------------------------------------------------------


class TestActuatorBase:
    def test_default_registers_and_debug_log(self, caplog):
        a = act.ActuatorBase("dummy", 0x2000)
        with caplog.at_level(logging.DEBUG, logger=act.__name__):
            assert a.io_handler("write32", 0x2008, 1) == 0
        assert a.io_handler("read32", 0x2008, 0) == 0
        assert "dummy: unhandled write offset=0x08" in caplog.text
        a.simulate_tick()
        assert a._tick_count == 1


class TestMotorController:
    def test_target_speed_capped_at_max_rpm(self):
        m = act.MotorController()
        m.io_handler("write32", m.base + 0x00, 9000)
        assert m.target_speed == 5000

    def test_enabled_motor_ramps_and_rotates(self):
        m = act.MotorController()
        m.write_reg(0x00, 5000)
        m.write_reg(0x10, 1)
        m.simulate_tick()
        assert m.read_reg(0x00) == 500
        assert m.read_reg(0x04) == 300  # 500 rpm * 0.006 deg = 3.00 deg
        assert m.read_reg(0x10) == 1
        assert m.read_reg(0x08) == u32(int(m.current_ma * 100))
        for _ in range(150):
            m.simulate_tick()
            assert 0 <= m.position_deg < 360
        assert 4990 <= m.speed_rpm <= 5000

    def test_reverse_direction_moves_backwards(self):
        m = act.MotorController()
        assert m.read_reg(0x0C) == 1
        m.write_reg(0x0C, 0)
        assert m.direction == -1
        m.write_reg(0x00, 1000)
        m.write_reg(0x10, 1)
        m.simulate_tick()
        assert m.position_deg == pytest.approx(360 - 0.6)

    def test_disabled_motor_coasts_down(self):
        m = act.MotorController()
        m.speed_rpm = 1000
        m.current_ma = 15.0
        m.simulate_tick()
        assert m.speed_rpm == 950
        assert m.current_ma == 5.0
        m.simulate_tick()
        assert m.current_ma == 0
        assert m.read_reg(0x14) == 0


class TestServoController:
    def test_targets_clamped_to_angle_limits(self):
        s = act.ServoController()
        s.set_target(0, 200)
        s.set_target(1, -5)
        s.set_target(9, 10)  # no such channel
        assert s.targets[:2] == [180.0, 0.0]
        s.io_handler("write32", s.base + 0x00, 20000)
        assert s.targets[0] == 180.0

    def test_rate_limited_motion(self):
        s = act.ServoController()
        s.speed_limit = 100.0  # 1 degree per tick
        s.write_reg(0x00, 9500)
        s.simulate_tick()
        assert s.read_reg(0x00) == 9100
        s.set_target(0, 0)
        for _ in range(200):
            s.simulate_tick()
        assert s.positions[0] == 0.0
        assert s.read_reg(0x40) == 0

    def test_write_uses_8_byte_channel_stride(self):
        s = act.ServoController()
        s.write_reg(0x08, 4500)
        s.write_reg(0x0C, 1)  # sub-register 4 is ignored
        assert s.targets[1] == 45.0
        assert s.targets[0] == 90.0


class TestESCController:
    def test_throttle_registers_and_clamp(self):
        esc = act.ESCController()
        esc.io_handler("write32", esc.base + 0x00, 5000)
        esc.write_reg(0x08, 20000)
        assert esc.read_reg(0x00) == 5000
        assert esc.throttle[1] == 100

    def test_spins_only_when_armed_and_enabled(self):
        esc = act.ESCController()
        esc.write_reg(0x00, 5000)
        esc.write_reg(0x30, 1)
        esc.simulate_tick()
        assert esc.rpm[0] == 0
        esc.write_reg(0x34, 1)
        esc.simulate_tick()
        assert esc.read_reg(0x04) == 1200
        assert esc.read_reg(0x30) == 1

    def test_disarm_spins_down(self):
        esc = act.ESCController()
        esc.rpm[0] = 1200
        esc.write_reg(0x30, 0)
        esc.simulate_tick()
        assert esc.rpm[0] == 1080
        assert esc.read_reg(0x38) == 0
        assert esc.read_reg(0x02) == 0


class TestValvePumpRelay:
    def test_on_off_valve(self):
        v = act.ValveController()
        v.io_handler("write32", v.base + 0x04, 5)
        assert v.read_reg(0x04) == 10000
        v.write_reg(0x04, 0)
        assert v.read_reg(0x04) == 0

    def test_proportional_valve_clamped(self):
        v = act.ValveController()
        v.types[2] = "proportional"
        v.write_reg(0x08, 4250)
        assert v.read_reg(0x08) == 4250
        v.write_reg(0x08, 20000)
        assert v.positions[2] == 100
        v.write_reg(0x10, 1)  # channel 4 does not exist
        assert v.read_reg(0x10) == 0

    def test_pump_ramps_flow_and_accumulates_volume(self):
        p = act.PumpController()
        p.io_handler("write32", p.base + 0x00, 1000)
        p.io_handler("write32", p.base + 0x04, 1)
        p.simulate_tick()
        assert p.read_reg(0x00) == 100
        assert p.read_reg(0x04) == 50
        delivered = []
        for _ in range(50):
            p.simulate_tick()
            delivered.append(p.total_delivered_ml)
        assert delivered == sorted(delivered)
        assert p.flow_rate_ml_min == pytest.approx(10.0, abs=0.1)
        assert p.read_reg(0x08) == int(p.total_delivered_ml * 100)

    def test_pump_occlusion_stops_flow_and_raises_pressure(self):
        p = act.PumpController()
        p.write_reg(0x04, 1)
        p.flow_rate_ml_min = 5.0
        p.occlusion = True
        p.simulate_tick()
        assert p.read_reg(0x00) == 0
        assert p.read_reg(0x04) == 20000
        assert p.read_reg(0x0C) == 1
        assert p.read_reg(0x10) == 0

    def test_disabled_pump_is_idle(self):
        p = act.PumpController()
        p.write_reg(0x00, 1000)
        p.simulate_tick()
        assert p.flow_rate_ml_min == 0.0

    def test_relay_bitmask_and_cycle_counting(self):
        r = act.RelayBank()
        r.io_handler("write32", r.base, 0b101)
        assert r.read_reg(0x00) == 0b101
        r.write_reg(0x00, 0b100)
        assert r.states[:3] == [False, False, True]
        assert r.cycle_counts[:3] == [2, 0, 1]
        assert r.read_reg(0x04) == 0
        r.write_reg(0x04, 0xFF)
        assert r.read_reg(0x00) == 0b100


class TestDisplayHaptic:
    def test_display_geometry_and_contrast(self):
        d = act.DisplayDriver()
        assert (d.read_reg(0x00), d.read_reg(0x04), d.read_reg(0x08)) == (128, 64, 255)
        d.write_reg(0x08, 0x180)
        d.write_reg(0x0C, 1)
        assert d.read_reg(0x08) == 0x80
        assert d.read_reg(0x0C) == 1
        assert d.read_reg(0x14) == 0

    def test_framebuffer_write_packs_index_and_value(self):
        d = act.DisplayDriver()
        d.io_handler("write32", d.base + 0x10, (0xAB << 16) | 5)
        d.write_reg(0x10, (0xCD << 16) | len(d.framebuffer))  # out of range
        assert d.framebuffer[5] == 0xAB
        assert len(d.framebuffer) == 128 * 64 // 8
        assert d.framebuffer.count(0) == len(d.framebuffer) - 1

    def test_haptic_pulse_expires(self):
        h = act.HapticDriver()
        h.write_reg(0x00, 0x1FF)
        h.write_reg(0x04, 3)
        h.write_reg(0x08, 25)
        assert h.read_reg(0x00) == 0xFF
        assert h.pattern == 3
        assert h.read_reg(0x04) == 25
        h.simulate_tick()
        h.simulate_tick()
        assert h.read_reg(0x00) == 0xFF
        h.simulate_tick()
        assert h.read_reg(0x00) == 0
        assert h.read_reg(0x0C) == 0

    def test_haptic_without_duration_keeps_intensity(self):
        h = act.HapticDriver()
        h.write_reg(0x00, 10)
        h.simulate_tick()
        assert h.intensity == 10


class TestVehicleActuators:
    def test_steering_rate_limited_with_torque(self):
        s = act.SteeringActuator()
        s.io_handler("write32", s.base, 1250)
        s.simulate_tick()
        assert s.read_reg(0x00) == 500
        assert s.read_reg(0x04) == 125
        s.simulate_tick()
        s.simulate_tick()
        assert s.angle_deg == 12.5
        assert s.read_reg(0x04) == 25  # 2.5 deg error * 0.1
        s.simulate_tick()
        assert s.torque_nm == 0.0
        assert s.read_reg(0x08) == 0

    def test_steering_clamped_both_directions(self):
        s = act.SteeringActuator()
        s.write_reg(0x00, 100000)
        assert s.target_angle == 540.0
        s.write_reg(0x00, -100000)
        assert s.target_angle == -540.0
        s.simulate_tick()
        assert s.read_reg(0x00) == u32(-500)

    def test_throttle_first_order_response_and_mode(self):
        t = act.ThrottleActuator()
        t.write_reg(0x00, 5000)
        t.simulate_tick()
        assert t.read_reg(0x00) == 1000
        t.write_reg(0x00, 20000)
        assert t.target_pct == 100
        t.write_reg(0x04, 1)
        assert t.mode == "cruise"
        t.write_reg(0x04, 0)
        assert t.mode == "manual"
        assert t.read_reg(0x04) == 0

    def test_brake_pressure_applies_to_all_channels(self):
        b = act.BrakeActuator()
        b.io_handler("write32", b.base, 10000)
        b.simulate_tick()
        assert b.read_reg(0x00) == 3000
        assert b.channels == [30.0] * 4
        assert b.read_reg(0x04) == 0
        b.write_reg(0x00, 50000)
        assert b.target_pct == 100
        assert b.read_reg(0x08) == 0


# --- Wireless ---------------------------------------------------------------


class TestWirelessBase:
    def test_default_handlers(self):
        w = wl.WirelessBase("radio", 0x3000)
        assert w.io_handler("write32", 0x3000, 1) == 0
        assert w.io_handler("read32", 0x3000, 0) == 0
        w.simulate_tick()
        assert w.enabled is False


class TestWiFi:
    def test_connect_via_control_register(self):
        w = wl.WiFiModule()
        w.io_handler("write32", w.base, 0b11)
        assert w.connected and w.enabled
        assert -60 <= w.rssi <= -40
        assert w.read_reg(0x00) == 0b11
        assert w.read_reg(0x04) == u32(w.rssi)

    def test_clearing_connect_bit_disconnects(self):
        w = wl.WiFiModule()
        w.write_reg(0x00, 0b11)
        w.write_reg(0x00, 0b10)
        assert w.read_reg(0x00) == 0b10
        assert w.rssi == 0
        w.write_reg(0x00, 0)  # already disconnected: no-op
        assert w.read_reg(0x00) == 0

    def test_connect_ssid_handling(self):
        w = wl.WiFiModule()
        w.connect("Lab")
        assert w.ssid == "Lab"
        w.connect("")
        assert w.ssid == "Lab"

    def test_rssi_clamped_while_connected_only(self):
        w = wl.WiFiModule()
        w.simulate_tick()
        assert w.rssi == -55
        w.connect()
        w.rssi = -5
        w.simulate_tick()
        assert -90 <= w.rssi <= -20
        w.tx_packets, w.rx_packets = 4, 7
        assert (w.read_reg(0x08), w.read_reg(0x0C), w.read_reg(0x10)) == (4, 7, 0)


class TestBLE:
    def test_advertise_then_connect(self):
        b = wl.BLEModule()
        b.io_handler("write32", b.base, 0b101)
        assert b.read_reg(0x00) == 0b101
        b.connect_peer()
        assert b.read_reg(0x00) == 0b110
        assert b.peer_addr == "AA:BB:CC:DD:EE:FF"
        assert -65 <= b.rssi <= -45

    def test_enable_without_advertising(self):
        b = wl.BLEModule()
        b.write_reg(0x00, 0b100)
        assert b.advertising is False
        assert b.read_reg(0x00) == 0b100

    def test_rssi_clamp_and_counters(self):
        b = wl.BLEModule()
        b.simulate_tick()
        assert b.rssi == -60
        b.connect_peer("11:22:33:44:55:66")
        b.rssi = -100
        b.simulate_tick()
        assert b.rssi >= -90
        assert b.read_reg(0x04) == u32(b.rssi)
        b.tx_packets, b.rx_packets = 2, 3
        assert (b.read_reg(0x08), b.read_reg(0x0C), b.read_reg(0x10)) == (2, 3, 0)


class TestLoRa:
    def test_spreading_factor_clamped(self):
        lora = wl.LoRaModule()
        lora.write_reg(0x04, 3)
        assert lora.read_reg(0x04) == 7
        lora.write_reg(0x04, 15)
        assert lora.read_reg(0x04) == 12
        lora.write_reg(0x04, 9)
        assert lora.read_reg(0x04) == 9

    def test_join_and_send(self):
        lora = wl.LoRaModule()
        lora.io_handler("write32", lora.base, 0b11)
        assert lora.read_reg(0x00) == 0b11
        assert -100 <= lora.rssi <= -70
        lora.send_packet(b"hello")
        lora.send_packet(b"world")
        assert lora.read_reg(0x08) == 2
        assert lora.read_reg(0x0C) == u32(lora.rssi)
        assert lora.read_reg(0x10) == 0

    def test_enable_only_does_not_join(self):
        lora = wl.LoRaModule()
        lora.write_reg(0x00, 0b10)
        lora.simulate_tick()
        assert lora.read_reg(0x00) == 0b10
        assert lora.rssi == -100

    def test_rssi_clamp_when_joined(self):
        lora = wl.LoRaModule()
        lora.join_network()
        lora.rssi = 0
        lora.simulate_tick()
        assert lora.rssi <= -30


class TestZigbee:
    def test_join_via_register_assigns_short_address(self):
        z = wl.ZigbeeModule()
        z.io_handler("write32", z.base, 0b11)
        assert z.read_reg(0x00) == 0b11
        assert 0x0001 <= z.read_reg(0x08) <= 0xFFF0
        assert z.read_reg(0x04) == 0x1234

    def test_join_with_explicit_pan(self):
        z = wl.ZigbeeModule()
        z.join_network(0xBEEF)
        assert z.read_reg(0x04) == 0xBEEF
        z.join_network(0)
        assert z.read_reg(0x04) == 0xBEEF

    def test_enable_only_and_channel_clamp(self):
        z = wl.ZigbeeModule()
        z.write_reg(0x00, 0b10)
        assert z.read_reg(0x00) == 0b10
        for val, expected in ((5, 11), (30, 26), (20, 20)):
            z.write_reg(0x0C, val)
            assert z.read_reg(0x0C) == expected
        assert z.read_reg(0x10) == 0


class TestRFTransceiver:
    def test_frequency_and_power_registers(self):
        rf = wl.RFTransceiver()
        rf.io_handler("write32", rf.base + 0x00, 1)
        rf.write_reg(0x04, 91500)
        rf.write_reg(0x08, 50)
        assert rf.read_reg(0x00) == 1
        assert rf.read_reg(0x04) == 91500
        assert rf.read_reg(0x08) == 30
        rf.write_reg(0x08, -50)
        assert rf.tx_power_dbm == -20
        assert rf.read_reg(0x10) == 0

    def test_rssi_moves_only_when_enabled(self):
        rf = wl.RFTransceiver()
        rf.simulate_tick()
        assert rf.rssi == -80
        rf.write_reg(0x00, 1)
        rf.rssi = 0
        rf.simulate_tick()
        assert rf.rssi <= -10
        assert rf.read_reg(0x0C) == u32(rf.rssi)


# --- Composites -------------------------------------------------------------


class TestCompositeBase:
    def test_default_handlers(self):
        c = comp.CompositeBase("blk", 0x5000)
        assert c.io_handler("write32", 0x5004, 3) == 0
        assert c.io_handler("read32", 0x5004, 0) == 0
        c.simulate_tick()
        assert c.enabled is False


class TestBatteryManagement:
    def test_discharge_reduces_soc_and_voltage(self):
        bms = comp.BatteryManagement()
        bms.io_handler("write32", bms.base + 0x04, 250000)  # 2500 mA load
        assert bms.read_reg(0x04) == 250000
        bms.simulate_tick()
        assert bms.soc_percent == pytest.approx(84.9995)
        assert bms.read_reg(0x00) == int(3000 + 0.849995 * 1200) * 4
        assert bms.read_reg(0x08) == int(bms.soc_percent * 100)
        assert bms.read_reg(0x14) == 0

    def test_charging_raises_soc_and_stops_at_full(self):
        bms = comp.BatteryManagement()
        bms.write_reg(0x10, 1)
        assert bms.read_reg(0x10) == 1
        bms.simulate_tick()
        assert bms.soc_percent == pytest.approx(85.01)
        bms.soc_percent = 100.0
        bms.simulate_tick()
        assert bms.soc_percent == 100.0

    def test_alarm_register_bits(self):
        bms = comp.BatteryManagement()
        bms.soc_percent = 10.0
        bms.temperature_c = 100.0
        bms.simulate_tick()
        assert bms.temperature_c == 60
        assert bms.read_reg(0x14) == 0b11
        assert bms.read_reg(0x0C) == 6000
        assert bms.read_reg(0x18) == 0

    def test_soc_never_negative_and_cells_balanced(self):
        bms = comp.BatteryManagement(cell_count=3)
        bms.soc_percent = 0.0
        bms.write_reg(0x04, 1_000_000)
        bms.simulate_tick()
        assert bms.soc_percent == 0
        per_cell = bms.voltage_mv // 3
        assert len(bms.cell_voltages) == 3
        assert all(abs(v - per_cell) <= 20 for v in bms.cell_voltages)


class TestPowerSupplyAndWatchdog:
    def test_power_supply_registers_read_only(self):
        psu = comp.PowerSupply()
        psu.io_handler("write32", psu.base, 1)
        assert psu.read_reg(0x00) == 12000
        assert psu.read_reg(0x04) == 9200
        assert psu.read_reg(0x08) == 1
        assert psu.read_reg(0x0C) == 0

    def test_watchdog_expires_and_reloads(self):
        wdt = comp.WatchdogTimer(timeout_ms=1000)
        wdt.simulate_tick()
        assert wdt.read_reg(0x00) == 1000  # disabled: not counting
        wdt.io_handler("write32", wdt.base + 0x08, 1)
        for _ in range(99):
            wdt.simulate_tick()
        assert wdt.read_reg(0x00) == 10
        assert wdt.read_reg(0x08) == 0
        wdt.simulate_tick()
        assert wdt.read_reg(0x08) == 1
        assert wdt.read_reg(0x0C) == 1
        assert wdt.read_reg(0x00) == 1000
        assert wdt.read_reg(0x10) == 0

    def test_kick_reloads_and_clears_reset(self):
        wdt = comp.WatchdogTimer()
        wdt.reset_triggered = True
        wdt.counter = 10
        wdt.write_reg(0x00, 0)
        assert wdt.counter == 1000
        assert wdt.reset_triggered is False

    def test_timeout_register_has_floor(self):
        wdt = comp.WatchdogTimer()
        wdt.write_reg(0x04, 50)
        assert wdt.read_reg(0x04) == 100
        assert wdt.read_reg(0x00) == 100

    def test_window_mode_rejects_early_kick(self):
        wdt = comp.WatchdogTimer(timeout_ms=1000)
        wdt.window_mode = True
        wdt.write_reg(0x08, 1)
        wdt.kick()
        assert wdt.reset_triggered is True
        assert wdt.reset_count == 1
        for _ in range(30):
            wdt.simulate_tick()
        wdt.kick()  # 700 ms left: inside the window
        assert wdt.counter == 1000
        assert wdt.reset_triggered is False
        assert wdt.reset_count == 1


class TestCryptoEngine:
    def test_encrypt_decrypt_round_trip(self):
        c = comp.CryptoEngine()
        ct = c.encrypt(b"\x00\xff\x5a")
        assert ct == b"\xa5\x5a\xff"
        assert c.decrypt(ct) == b"\x00\xff\x5a"
        assert c.busy is False
        assert c.read_reg(0x04) == 2

    def test_hash_ready_flag_and_value(self):
        c = comp.CryptoEngine()
        assert c.read_reg(0x00) == 0
        c.compute_hash(b"abc")
        assert c.read_reg(0x00) == 0b10
        assert c.read_reg(0x08) == hash(b"abc") & MASK32
        assert c.read_reg(0x0C) == 256
        assert c.read_reg(0x10) == 0
        assert c.operations_done == 1


class TestRTC:
    def test_initial_time_from_host_clock(self, monkeypatch):
        monkeypatch.setattr(comp, "time", SimpleNamespace(time=lambda: 1_700_000_000.7))
        rtc = comp.RTCModule()
        assert rtc.read_reg(0x00) == 1_700_000_000

    def test_alarm_fires_when_time_reaches_alarm(self):
        rtc = comp.RTCModule()
        rtc.io_handler("write32", rtc.base + 0x00, 1000)
        rtc.write_reg(0x04, 1003)
        rtc.write_reg(0x08, 0b101)  # alarm enable + run
        rtc.simulate_tick()
        rtc.simulate_tick()
        assert rtc.read_reg(0x08) == 0b101
        rtc.simulate_tick()
        assert rtc.read_reg(0x00) == 1003
        assert rtc.read_reg(0x08) == 0b111
        assert rtc.read_reg(0x04) == 1003

    def test_alarm_clear_bit_and_stop(self):
        rtc = comp.RTCModule()
        rtc.write_reg(0x00, 50)
        rtc.alarm_triggered = True
        rtc.write_reg(0x08, 0b011)  # clear triggered, alarm on, clock stopped
        assert rtc.read_reg(0x08) == 0b101
        rtc.simulate_tick()
        assert rtc.read_reg(0x00) == 50
        assert rtc.read_reg(0x0C) == 0


# --- Buses ------------------------------------------------------------------


class TestBusBase:
    def test_default_handlers_log_writes(self, caplog):
        b = buses.BusBase("bus", 0x6000)
        with caplog.at_level(logging.DEBUG, logger=buses.__name__):
            assert b.io_handler("write32", 0x6010, 0xFF) == 0
        assert b.io_handler("read32", 0x6010, 0) == 0
        assert "bus: unhandled write offset=0x10 val=0x000000ff" in caplog.text
        b.simulate_tick()
        assert b._tick_count == 1


class TestCANBus:
    def test_send_without_loopback(self):
        can = buses.CANBusController()
        can.send_message(0x123, b"\x01\x02")
        assert can.read_reg(0x04) == 1
        assert can.last_tx_id == 0x123
        assert can.tx_queue[-1] == {"id": 0x123, "data": b"\x01\x02", "extended": False, "dlc": 2}
        assert can.receive_message() is None

    def test_loopback_delivers_to_rx(self):
        can = buses.CANBusController()
        can.loopback = True
        can.send_message(0x7E8, b"\xaa", extended=True)
        assert can.read_reg(0x0C) == 1
        msg = can.receive_message()
        assert msg["id"] == 0x7E8 and msg["extended"] is True
        assert can.read_reg(0x10) == 0x7E8
        assert can.read_reg(0x08) == 1

    def test_acceptance_filters(self):
        can = buses.CANBusController()
        can.filters = [0x100]
        can.inject_message(0x200, b"x")
        can.inject_message(0x100, b"yz")
        assert can.rx_count == 1
        assert can.receive_message()["dlc"] == 2

    def test_rx_queue_bounded(self):
        can = buses.CANBusController()
        for i in range(70):
            can.inject_message(i, b"")
        assert can.read_reg(0x0C) == 64
        assert can.read_reg(0x08) == 70
        assert can.receive_message()["id"] == 6  # oldest six dropped

    def test_control_registers(self):
        can = buses.CANBusController()
        can.io_handler("write32", can.base + 0x00, 1)
        can.bus_off = True
        assert can.read_reg(0x00) == 0b11
        can.write_reg(0x04, 250000)
        assert can.bitrate == 250000
        can.write_reg(0x10, 0x7FF)
        assert can.last_tx_id == 0x7FF
        assert can.tx_queue[-1]["data"] == b"\x00" * 8
        can.error_count = 3
        assert can.read_reg(0x14) == 3
        assert can.read_reg(0x18) == 0


class TestLINAndModbus:
    def test_lin_frames(self):
        lin = buses.LINBusController()
        lin.send_frame(0x10, b"ab")
        assert lin.frame_buffer == {0x10: b"ab"}
        assert lin.read_reg(0x00) == 0x10
        lin.io_handler("write32", lin.base, 0xFF)
        assert lin.read_reg(0x00) == 0x3F
        lin.write_reg(0x04, 0)
        assert lin.read_reg(0x04) == 0
        assert lin.read_reg(0x08) == 0

    def test_modbus_holding_registers_are_16_bit(self):
        mb = buses.ModbusController()
        mb.write_holding(10, [0x12345, 7])
        assert mb.read_holding(10, 2) == [0x2345, 7]
        mb.write_holding(255, [1, 2])
        assert mb.registers[255] == 1
        assert len(mb.registers) == 256
        assert mb.read_reg(0x04) == 2

    def test_modbus_coils(self):
        mb = buses.ModbusController()
        mb.write_coil(3, True)
        mb.write_coil(300, True)
        assert mb.read_coil(3) is True
        assert mb.read_coil(300) is False
        assert mb.transaction_count == 2

    def test_modbus_slave_address_register(self):
        mb = buses.ModbusController()
        mb.io_handler("write32", mb.base, 0x1F7)
        assert mb.read_reg(0x00) == 0xF7
        assert mb.read_reg(0x08) == 0


class TestEthernet:
    def test_packet_counters(self):
        eth = buses.EthernetMAC()
        eth.send_packet(b"abcd")
        eth.inject_packet(b"xyz")
        assert (eth.tx_packets, eth.tx_bytes, eth.rx_packets, eth.rx_bytes) == (1, 4, 1, 3)
        assert eth.read_reg(0x08) == 1
        assert eth.read_reg(0x0C) == 1
        assert eth.rx_buffer[-1] == b"xyz"

    def test_link_and_enable(self):
        eth = buses.EthernetMAC()
        assert eth.read_reg(0x00) == 0b01
        eth.io_handler("write32", eth.base, 1)
        assert eth.read_reg(0x00) == 0b11
        assert eth.read_reg(0x04) == 100
        assert eth.read_reg(0x10) == 0


class TestAvionicsBuses:
    def test_arinc_word_packing(self):
        a = buses.ARINC429()
        a.send_word(label=0x185, sdi=5, data=0xF12345, ssm=7)
        expected = 0x85 | (1 << 8) | (0x12345 << 10) | (3 << 29)
        assert a.tx_labels[-1] == expected
        assert a.read_reg(0x04) == 1

    def test_arinc_rx_fifo(self):
        a = buses.ARINC429()
        a.inject_word(0xDEAD)
        assert a.read_reg(0x0C) == 1
        assert a.read_reg(0x10) == 0xDEAD
        assert a.read_reg(0x10) == 0
        assert a.read_reg(0x08) == 1
        assert a.read_reg(0x14) == 0

    def test_arinc_register_tx_and_enable(self):
        a = buses.ARINC429()
        a.io_handler("write32", a.base + 0x00, 1)
        a.write_reg(0x10, 0x1234)
        assert a.read_reg(0x00) == 1
        assert list(a.tx_labels) == [0x1234]
        assert a.tx_count == 1

    def test_mil1553(self):
        m = buses.MIL1553Bus()
        m.send_command(5, 2, [1, 2, 3])
        assert m.messages[-1] == {"rt": 5, "sa": 2, "data": [1, 2, 3], "word_count": 3}
        assert m.read_reg(0x04) == 1
        m.io_handler("write32", m.base, 0x3F)
        assert m.read_reg(0x00) == 0x1F
        m.write_reg(0x0C, 0)
        assert m.read_reg(0x0C) == 0
        assert m.read_reg(0x08) == 0
        assert m.read_reg(0x10) == 0
