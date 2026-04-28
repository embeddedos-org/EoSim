# Simulator Development Guide

This guide explains how to create new domain simulators for EoSim.

## Simulator Architecture

Every simulator extends the same interface pattern:

```
BaseSimulator
├── PRODUCT_TYPE        — unique string identifier
├── DISPLAY_NAME        — human-readable name
├── SCENARIOS           — dict of named test scenarios
├── setup()             — initialize peripherals and state
├── tick()              — advance simulation by one step
├── get_state()         — return current state dict
├── get_status_text()   — return status string for UI
└── reset()             — reset to initial state
```

## Step-by-Step: Creating a New Simulator

### 1. Create the Simulator File

Create a new file in `eosim/engine/native/simulators/`:

```python
# eosim/engine/native/simulators/my_domain.py
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""My Domain simulator.

Pure Python, cross-platform (Linux/Windows/macOS). No OS-specific dependencies.
"""
import random


class MyDomainSimulator:
    PRODUCT_TYPE = 'my_domain'
    DISPLAY_NAME = 'My Domain'

    SCENARIOS = {
        'normal_operation': {
            'description': 'Standard operating conditions',
            'param1': 100,
        },
        'stress_test': {
            'description': 'High-load stress test',
        },
        'fault_injection': {
            'description': 'Simulated component failure',
        },
    }

    def __init__(self, vm):
        self.vm = vm
        self.tick_count = 0
        self.state = {}
        self.scenario = ''
        self._scenario_step = 0

    def setup(self):
        # Import and add peripherals
        from eosim.engine.native.peripherals.sensors import TemperatureSensor
        from eosim.engine.native.peripherals.composites import WatchdogTimer

        self.vm.add_peripheral('temp0', TemperatureSensor('temp0', 0x40100010))
        self.vm.add_peripheral('wdt0', WatchdogTimer('wdt0', 0x40500200))

        # Initialize state
        self.state = {
            'value1': 0.0,
            'value2': 100,
            'status': 'idle',
            'scenario': '',
        }

    def load_scenario(self, name):
        if name in self.SCENARIOS:
            self.scenario = name
            self._scenario_step = 0
            self.state['scenario'] = name

    def tick(self):
        self.tick_count += 1
        # Tick all peripherals
        for name, dev in self.vm.peripherals.items():
            if hasattr(dev, 'simulate_tick'):
                dev.simulate_tick()
        self._apply_scenario()
        # Update domain-specific state
        self.state['value1'] += random.gauss(0, 0.1)

    def _apply_scenario(self):
        if not self.scenario:
            return
        cfg = self.SCENARIOS.get(self.scenario, {})
        # Apply scenario-specific logic
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
```

### 2. Register in `__init__.py`

Add an import and SIMULATOR_MAP entries in `eosim/engine/native/simulators/__init__.py`:

```python
from eosim.engine.native.simulators.my_domain import MyDomainSimulator

# In SIMULATOR_MAP:
SIMULATOR_MAP = {
    ...
    'my_domain': MyDomainSimulator,
    'my_product_1': MyDomainSimulator,
    'my_product_2': MyDomainSimulator,
}
```

### 3. Add Product Templates

In `eosim/gui/product_templates.py`:

```python
"my_product_1": ProductTemplate(
    name="my_product_1",
    display_name="My Product",
    icon="\U0001F4BB",
    arch="arm",
    ram_mb=256,
    peripherals=["temp", "gpio", "watchdog"],
    domain="my_domain",
    description="Description of the product",
    default_platform="stm32h7",
    simulator_class="MyDomainSimulator",
),
```

### 4. Add Domain Profile

In `eosim/core/domains.py`:

```python
"my_domain": DomainProfile(
    name="my_domain",
    display_name="My Domain",
    description="Description of the domain.",
    standards=["ISO XXXXX"],
    safety_levels=["SIL-1", "SIL-2"],
    typical_arches=["arm", "arm64"],
    typical_classes=["mcu", "sbc"],
    test_scenarios=["scenario1", "scenario2"],
),
```

### 5. Add Schema Entry

In `eosim/core/schema.py`, add the domain to `VALID_DOMAINS`.

### 6. Create GUI Renderer (Optional)

In `eosim/gui/renderers/my_domain.py`:

```python
from eosim.gui.renderers import BaseRenderer, register_renderer

class MyDomainRenderer(BaseRenderer):
    DOMAIN = "my_domain"
    DISPLAY_NAME = "My Domain"

    def setup(self, ax):
        ax.set_xlim(-10, 10)
        ax.set_ylim(-10, 10)
        ax.set_zlim(0, 10)
        ax.set_title(self.DISPLAY_NAME, fontsize=10)

    def update(self, ax, state):
        ax.cla()
        self.setup(ax)
        info = "\n".join(f"{k}: {v}" for k, v in list(state.items())[:6])
        ax.text2D(0.02, 0.95, info, transform=ax.transAxes, fontsize=8,
                  verticalalignment='top', family='monospace')

register_renderer("my_domain", MyDomainRenderer)
```

### 7. Write Tests

In `tests/unit/test_my_simulator.py`:

```python
class FakeVM:
    peripherals = {}
    def add_peripheral(self, name, dev):
        self.peripherals[name] = dev

def test_my_domain_simulator():
    from eosim.engine.native.simulators.my_domain import MyDomainSimulator
    vm = FakeVM()
    sim = MyDomainSimulator(vm)
    sim.setup()
    assert sim.tick_count == 0
    sim.tick()
    assert sim.tick_count == 1
    state = sim.get_state()
    assert isinstance(state, dict)
```

## Best Practices

1. **Pure Python** — no C extensions, no OS-specific code
2. **Use `random.gauss()`** for realistic sensor noise
3. **At least 3 scenarios** per simulator
4. **Import peripherals locally** in `setup()` to avoid circular imports
5. **State as flat dict** — keys should be descriptive (e.g., `speed_kmh`, `pressure_bar`)
6. **Tick all peripherals** at the start of `tick()`
