# Analysis Tools Guide

EoSim includes five analysis modules for production-grade embedded system validation.

## Power Analysis

Estimate power consumption and battery life for embedded platforms.

```python
from eosim.analysis.power import PowerAnalyzer, PowerProfile

analyzer = PowerAnalyzer()
analyzer.add_profile('nrf52840', PowerProfile(
    name='nrf52840',
    voltage_v=3.3,
    current_active_ma=5.0,
    current_sleep_ma=0.002,
    current_deep_sleep_ua=0.4,
    clock_mhz=64.0,
))

# Measure power in different modes
active = analyzer.measure('nrf52840', mode='active', duration_s=0.01)
sleep = analyzer.measure('nrf52840', mode='sleep', duration_s=0.99)

# Estimate battery life (hours)
hours = analyzer.estimate_battery_life('nrf52840', capacity_mah=250, duty_cycle_pct=1)
print(f"Battery life: {hours:.0f} hours ({hours/24:.0f} days)")
```

## Thermal Modeling

Predict temperature rise and thermal limits.

```python
from eosim.analysis.thermal import ThermalModel

model = ThermalModel(
    ambient_c=25.0,
    thermal_resistance_cw=15.0,  # °C/W (junction-to-ambient)
    thermal_capacitance_jc=5.0,  # J/°C
)

# Steady-state temperature at 2W
print(model.steady_state(power_w=2.0))  # 55.0°C

# Time to reach 85°C thermal limit
print(model.time_to_limit(power_w=3.0, limit_c=85.0))
```

## Functional Safety (ISO 26262 / IEC 61508)

Track and verify safety requirements.

```python
from eosim.analysis.safety import SafetyAnalyzer, SafetyRequirement

sa = SafetyAnalyzer()
sa.add_requirement(SafetyRequirement(
    req_id='SWR-001',
    description='Watchdog timer shall reset within 100ms',
    standard='ISO 26262',
    level='ASIL-D',
))
sa.add_requirement(SafetyRequirement(
    req_id='SWR-002',
    description='CAN bus error shall trigger safe state',
    standard='ISO 26262',
    level='ASIL-B',
))

# Verify requirements
sa.verify('SWR-001')
report = sa.report()
print(f"Coverage: {report['coverage_pct']:.0f}%")
```

## Security Analysis (ISO 21434 / IEC 62443)

Threat modeling and risk scoring.

```python
from eosim.analysis.security import SecurityAnalyzer, ThreatModel

sa = SecurityAnalyzer()
sa.add_threat(ThreatModel(
    asset='ECU firmware',
    threat='Tampering via debug port',
    impact='critical',
    likelihood='medium',
))
sa.mitigate('ECU firmware', 'Disable JTAG in production, secure boot')
print(sa.report())
```

## WCET Analysis

Worst-case execution time and schedulability analysis.

```python
from eosim.analysis.timing import WCETAnalyzer

wa = WCETAnalyzer(clock_mhz=168)  # STM32F4 @ 168 MHz
wa.add_task('sensor_read', cycles=5000, period_us=1000)
wa.add_task('can_tx', cycles=2000, period_us=500)
wa.add_task('pid_control', cycles=10000, period_us=5000)

report = wa.report()
print(f"CPU Utilization: {report['utilization']*100:.1f}%")
print(f"Schedulable (Liu & Layland): {report['schedulable']}")
```
