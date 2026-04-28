# Plugin Development Guide

EoSim includes a plugin system for extending simulation behavior.

## Plugin Architecture

```
PluginLoader
├── discover()          — Scan directories for plugin modules
├── load_all()          — Call on_load() on all discovered plugins
├── unload_all()        — Call on_unload() on all plugins
├── get_plugin(name)    — Get a specific plugin instance
└── list_plugins()      — List all plugins with info

PluginBase (abstract)
├── NAME                — Plugin name string
├── VERSION             — Plugin version string
├── DESCRIPTION         — Plugin description
├── on_load()           — Called when plugin is loaded (required)
├── on_unload()         — Called when plugin is unloaded
├── on_tick()           — Called each simulation tick
└── on_scenario_load()  — Called when a scenario is loaded
```

## Creating a Plugin

### 1. Create Plugin File

```python
# my_plugins/data_logger.py
from eosim.plugins.base import PluginBase
import json

class DataLoggerPlugin(PluginBase):
    NAME = "data-logger"
    VERSION = "1.0.0"
    DESCRIPTION = "Logs simulation state to JSON file each tick"

    def __init__(self, context=None):
        super().__init__(context)
        self._log = []
        self._output_file = "sim_log.json"

    def on_load(self):
        self._log = []
        print(f"[{self.NAME}] Plugin loaded, logging to {self._output_file}")

    def on_tick(self, simulator, state):
        self._log.append(dict(state))

    def on_unload(self):
        with open(self._output_file, 'w') as f:
            json.dump(self._log, f, indent=2, default=str)
        print(f"[{self.NAME}] Wrote {len(self._log)} entries to {self._output_file}")
```

### 2. Load Plugins

```python
from eosim.plugins.loader import PluginLoader

loader = PluginLoader(plugin_dirs=['./my_plugins'])
loader.discover()
loader.load_all()

# List discovered plugins
for name, info in loader.list_plugins().items():
    print(f"  {name} v{info['version']} — {info['description']}")

# Get a specific plugin
logger = loader.get_plugin('data-logger')
```

### 3. Integrate with Simulation Loop

```python
# In your simulation loop:
for tick in range(1000):
    simulator.tick()
    state = simulator.get_state()
    for plugin in loader.plugins.values():
        plugin.on_tick(simulator, state)

# Cleanup
loader.unload_all()
```

## Plugin Ideas

- **Data Logger** — log state to CSV/JSON/Parquet
- **Fault Injector** — randomly inject sensor faults
- **Performance Monitor** — track tick rate and memory
- **Alert System** — trigger alerts on threshold violations
- **Remote Dashboard** — push state to web UI
- **Replay Recorder** — record/replay simulation sessions
