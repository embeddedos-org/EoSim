# Digital Twin Guide

EoSim's digital twin engine mirrors physical hardware state in real-time.

## Overview

A digital twin is a virtual replica of a physical embedded device that:
- **Mirrors** the device's real-time state
- **Predicts** future behavior through simulation
- **Records** historical state for analysis
- **Exports** data for offline processing

## Usage

```python
from eosim.engine.native.simulators import SimulatorFactory
from eosim.digital_twin.twin import DigitalTwin

# Create simulator
class VM:
    peripherals = {}
    def add_peripheral(self, name, dev):
        self.peripherals[name] = dev

vm = VM()
sim = SimulatorFactory.create('automotive_ecu', vm)

# Create digital twin
twin = DigitalTwin('engine_ecu_001', sim)

# Sync current state (call periodically)
state = twin.sync()
print(f"Current state: {state}")

# Predict future (runs simulation forward)
predictions = twin.predict(steps=100)
print(f"Predicted speed in 100 ticks: {predictions[-1].get('speed_kmh', 'N/A')}")

# Export history
twin.export_json('twin_history.json')

# Check twin status
print(twin.status())
```

## Architecture

```
Physical Device ─── Serial/Network ───> Data Ingestion
                                              │
                                        DigitalTwin
                                        ├── sync()      ── Mirror state
                                        ├── predict()   ── Run simulation
                                        ├── history     ── Store states
                                        └── export()    ── JSON/CSV output
```

## Integration with REST API

The digital twin can be exposed via the REST API:

```python
from eosim.api.server import EoSimAPIServer
from eosim.digital_twin.twin import DigitalTwin

server = EoSimAPIServer()
twin = DigitalTwin('pump_001', pump_sim)
server.add_simulation('pump_001', twin.simulator)
server.run()
```

Access via: `GET /api/v1/simulations/pump_001/state`
