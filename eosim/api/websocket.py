# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""WebSocket support for live simulation data streaming."""
import json
import asyncio


class SimulationWebSocket:
    """WebSocket handler for real-time simulation state updates."""

    def __init__(self, server):
        self.server = server
        self.clients = set()

    def register(self, app):
        try:
            from fastapi import WebSocket, WebSocketDisconnect

            @app.websocket("/ws/simulations/{name}")
            async def websocket_endpoint(websocket: WebSocket, name: str):
                await websocket.accept()
                self.clients.add(websocket)
                sim = self.server.get_simulation(name)
                try:
                    while True:
                        data = await websocket.receive_text()
                        if data == "tick" and sim:
                            sim.tick()
                        if sim:
                            state = sim.get_state()
                            await websocket.send_json(state)
                        await asyncio.sleep(0.01)
                except Exception:
                    self.clients.discard(websocket)
        except ImportError:
            pass
