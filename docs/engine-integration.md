# Engine Integration Guide

## Overview

EoSim supports 10 simulation engine backends. Each engine provides a bridge to an
external simulation tool or an internal simulation model.

## Engine Architecture

```
get_engine(platform)
    → EoSimEngine     (Pure Python, always available)
    → QemuEngine      (Binary emulation via QEMU)
    → QemuLiveEngine  (QEMU + QMP/GDB for interactive debugging)
    → RenodeEngine    (Deterministic simulation via Renode)
    → XPlaneEngine    (X-Plane flight simulator bridge)
    → GazeboEngine    (Gazebo robot simulator bridge)
    → OpenFOAMEngine  (OpenFOAM CFD solver)
    → CARLAEngine     (CARLA autonomous driving simulator)
    → AirSimEngine    (AirSim drone/car simulator)
    → ROS2Engine      (ROS 2 node bridge)
```

## Adding a New Engine

### 1. Create Integration Bridge

Create a client in `eosim/integrations/`:

```python
# eosim/integrations/my_engine.py
class MyEngineConnection:
    def __init__(self, host='127.0.0.1', port=5000):
        self.host = host
        self.port = port
        self._connected = False

    def connect(self, timeout=5.0):
        # Connect to external engine
        ...
        return self._connected

    def disconnect(self):
        self._connected = False
```

### 2. Create Engine Backend

Add a class in `eosim/engine/backend.py`:

```python
class MyEngine:
    @staticmethod
    def available() -> bool:
        # Check if the external engine is running
        ...

    @staticmethod
    def run(platform, timeout=60, log_file=''):
        result = SimResult(engine='my_engine', platform=platform.name)
        # Run simulation
        ...
        return result
```

### 3. Register in `get_engine()`

```python
def get_engine(platform):
    if platform.engine == "my_engine":
        return MyEngine()
    ...
```

### 4. Add Schema Entry

Add the engine name to `VALID_ENGINES` in `eosim/core/schema.py`.

## Available Integration Bridges

| Bridge | File | Protocol | External Tool |
|--------|------|----------|---------------|
| CARLAConnection | `carla.py` | TCP | CARLA Simulator |
| AirSimConnection | `airsim.py` | TCP/msgpack | Microsoft AirSim |
| ROS2Bridge | `ros2.py` | rclpy | ROS 2 |
| VerilatorBridge | `verilator.py` | File I/O | Verilator RTL sim |
| MATLABBridge | `matlab.py` | matlab.engine | MATLAB/Simulink |
| NS3Bridge | `ns3.py` | subprocess | ns-3 network sim |
| DockerSimRunner | `docker_sim.py` | Docker API | Containerized sims |
| XPlaneConnection | `xplane.py` | UDP | X-Plane |
| GazeboConnection | `gazebo.py` | TCP | Gazebo |
| OpenFOAMRunner | `openfoam.py` | subprocess | OpenFOAM |
