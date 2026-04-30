# Peripheral Development Guide

This guide explains how to create new peripheral models for EoSim.

## Peripheral Types

EoSim peripherals are organized into categories:

| Category | Base Class | Location | Examples |
|----------|-----------|----------|----------|
| Sensors | `SensorBase` | `peripherals/sensors*.py` | Temperature, IMU, GPS, pH |
| Actuators | `ActuatorBase` | `peripherals/actuators*.py` | Motor, valve, heater |
| Buses | `BusBase` | `peripherals/buses*.py` | CAN, SPI, EtherCAT, Modbus |
| Wireless | `WirelessBase` | `peripherals/wireless*.py` | BLE, WiFi, NFC, UWB |
| Composites | `CompositeBase` | `peripherals/composites*.py` | BMS, watchdog, PMIC |

## Creating a Sensor

```python
from eosim.engine.native.peripherals.sensors import SensorBase

class MySensor(SensorBase):
    def __init__(self, name='mysensor0', base_addr=0x40110000):
        super().__init__(name, base_addr)
        self.value = 0.0

    def simulate_tick(self):
        super().simulate_tick()
        self.value += random.gauss(0, 0.1)

    def read_reg(self, offset):
        if offset == 0x00:
            return int(self.value * 100) & 0xFFFFFFFF
        return 0

    def write_reg(self, offset, val):
        if offset == 0x08:
            self.enabled = bool(val & 1)
```

## Creating an Actuator

```python
from eosim.engine.native.peripherals.actuators import ActuatorBase

class MyActuator(ActuatorBase):
    def __init__(self, name='myactuator0', base_addr=0x40210000):
        super().__init__(name, base_addr)
        self.position = 0.0
        self.target = 0.0

    def simulate_tick(self):
        super().simulate_tick()
        err = self.target - self.position
        self.position += err * 0.1
```

## Register Layout Convention

| Offset | Purpose |
|--------|---------|
| 0x00 | Primary value (read) |
| 0x04 | Secondary value (read) |
| 0x08 | Control / enable register (write) |
| 0x0C | Status register (read) |
| 0x10+ | Extended registers |

## Available Peripherals (100+)

### Sensors
- **Environment**: Temperature, Humidity, SoilMoisture, pH, Gas, WaterLevel, UV, NoiseLevel
- **Industrial**: LoadCell, FlowSensor, VibrationSensor, TorqueSensor, StrainGauge, LevelSensor
- **Navigation**: Radar, LiDAR, DepthSounder, Sonar, Compass, GPS, IMU
- **Imaging**: Camera, ThermalCamera, InfraredSensor, XRaySensor
- **Medical**: ECG, PulseOximeter
- **General**: Pressure, Proximity, Light, ADC, CurrentSensor

### Actuators
- **Motion**: MotorController, SteeringActuator, ServoController, ESCController
- **Industrial**: ConveyorBelt, CraneController, DrillMotor, PrintHead, Extruder
- **Environment**: IrrigationValve, FanController, HeaterElement, Compressor, Damper
- **Vehicle**: ThrottleActuator, BrakeActuator

### Buses
- **Automotive**: CAN, LIN, FlexRay, ARINC 429
- **Industrial**: EtherCAT, PROFINET, Modbus TCP, OPC UA, HART
- **Network**: Ethernet MAC, USB, PCIe, HDMI, I2S
- **Serial**: SPI, I2C, UART

### Wireless
- **Short Range**: BLE, WiFi, Zigbee, NFC, UWB, Thread, Matter
- **Long Range**: LoRa, LTE Cat-M1, NB-IoT, Satellite
