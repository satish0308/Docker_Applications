"""
Real-Time Event Streamer & WebSocket Hub
Broadcasts Docker daemon lifecycle events and pipeline state to connected React clients in real-time.
"""

import asyncio
import json
import threading
import docker
from typing import List, Set
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)

    async def broadcast(self, message: dict):
        dead_connections = set()
        payload = json.dumps(message)
        for connection in list(self.active_connections):
            try:
                await connection.send_text(payload)
            except Exception:
                dead_connections.add(connection)
        for dead in dead_connections:
            self.active_connections.discard(dead)

# Global Manager Instance
ws_manager = ConnectionManager()

def start_docker_event_listener(loop: asyncio.AbstractEventLoop):
    """
    Background worker that streams Docker daemon events and dispatches to WebSockets.
    """
    def listener():
        try:
            client = docker.from_env()
            for event in client.events(decode=True):
                evt_type = event.get("Type")
                action = event.get("Action", "")
                actor = event.get("Actor", {})
                attributes = actor.get("Attributes", {})
                cname = attributes.get("name", "")

                if evt_type == "container" and action in ["start", "stop", "die", "kill", "restart", "health_status: healthy", "health_status: unhealthy"]:
                    msg = {
                        "type": "DOCKER_CONTAINER_EVENT",
                        "action": action,
                        "container": cname,
                        "status": "RUNNING" if action in ["start", "health_status: healthy"] else "STOPPED",
                        "time": event.get("time")
                    }
                    asyncio.run_coroutine_threadsafe(ws_manager.broadcast(msg), loop)
        except Exception as ex:
            print(f"[Docker Event Streamer] Error: {ex}")

    t = threading.Thread(target=listener, daemon=True)
    t.start()
