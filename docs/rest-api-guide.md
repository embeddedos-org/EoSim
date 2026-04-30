# REST API Guide

EoSim includes a FastAPI-based REST API for remote simulation control.

## Prerequisites

```bash
pip install "eosim[api]"
# or
pip install fastapi uvicorn
```

## Starting the Server

```python
from eosim.api.server import EoSimAPIServer

server = EoSimAPIServer(host='0.0.0.0', port=8080)
server.run()
```

Or via CLI:
```bash
python -m eosim.api.server
```

## API Endpoints

### Platforms

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/platforms` | List all available platforms |
| GET | `/api/v1/domains` | List all domains |
| GET | `/api/v1/simulators` | List all simulator types |
| GET | `/api/v1/templates` | List all product templates |

### Simulations

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/simulations` | List active simulations |
| GET | `/api/v1/simulations/{name}/state` | Get simulation state |
| POST | `/api/v1/simulations/{name}/tick` | Advance one tick |
| POST | `/api/v1/simulations/{name}/reset` | Reset simulation |

### WebSocket

| Protocol | Endpoint | Description |
|----------|----------|-------------|
| WS | `/ws/simulations/{name}` | Real-time state streaming |

## WebSocket Usage

```javascript
const ws = new WebSocket('ws://localhost:8080/ws/simulations/ecu1');
ws.onmessage = (event) => {
    const state = JSON.parse(event.data);
    console.log('State:', state);
};
ws.send('tick');  // Advance simulation
```

## Interactive Docs

When the server is running, visit:
- Swagger UI: `http://localhost:8080/docs`
- ReDoc: `http://localhost:8080/redoc`
