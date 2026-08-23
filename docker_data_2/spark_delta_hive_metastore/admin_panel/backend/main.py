"""
BDP Control Center FastAPI Master Application
Serves REST APIs, WebSocket streaming hubs, and mounts compiled React 18 frontend static assets.
"""

import asyncio
import os
import docker
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.events_streamer import ws_manager, start_docker_event_listener
from backend.routes_orchestrator import router as orchestrator_router
from backend.routes_sql import router as sql_router
from backend.routes_ingestion import router as ingestion_router
from backend.routes_tuning import router as tuning_router
from backend.routes_metastore import router as metastore_router
from backend.routes_diagnostics import router as diagnostics_router
from backend.routes_delta import router as delta_router
from backend.routes_backup import router as backup_router
from backend.routes_schedule import router as schedule_router
from backend.routes_cleanup import router as cleanup_router

app = FastAPI(
    title="BDP Platform Studio • Enterprise SaaS Control Engine",
    version="3.0.0",
    description="React 18 + FastAPI + WebSockets Control Center for Spark, Delta Lake, Hive, and YARN."
)

# Enable CORS for local Vite development and Docker networking
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include All Functional API Routers
app.include_router(orchestrator_router)
app.include_router(sql_router)
app.include_router(ingestion_router)
app.include_router(tuning_router)
app.include_router(metastore_router)
app.include_router(diagnostics_router)
app.include_router(delta_router)
app.include_router(backup_router)
app.include_router(schedule_router)
app.include_router(cleanup_router)

@app.on_event("startup")
async def startup_event():
    """Starts background threads for Docker daemon event streaming."""
    loop = asyncio.get_running_loop()
    start_docker_event_listener(loop)

@app.websocket("/api/ws/events")
async def websocket_events_endpoint(websocket: WebSocket):
    """Real-time bi-directional event stream for live cluster notifications."""
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep-alive heartbeat & client command receiver
            data = await websocket.receive_text()
            # Echo or process client events
            await websocket.send_json({"type": "PONG", "received": data})
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)

@app.websocket("/api/ws/logs/{container_name}")
async def websocket_container_logs(websocket: WebSocket, container_name: str):
    """Streams live line-by-line container logs asynchronously with non-blocking producer-consumer queue."""
    await websocket.accept()
    try:
        client = docker.from_env()
        # Resolve container by exact name or substring matching
        container = None
        try:
            container = client.containers.get(container_name)
        except Exception:
            for c in client.containers.list(all=True):
                if container_name.lower() in c.name.lower():
                    container = c
                    break
        
        if not container:
            await websocket.send_text(f"⚠️ Container '{container_name}' not found on host.\n")
            await websocket.close()
            return

        if container.status.lower() != "running":
            prev_logs = container.logs(tail=100).decode('utf-8', errors='ignore')
            await websocket.send_text(f"ℹ️ Container '{container.name}' is currently {container.status.upper()}.\n--- Previous Logs (Tail 100) ---\n")
            await websocket.send_text(prev_logs)
            return

        # Running container: stream logs asynchronously without blocking event loop
        queue = asyncio.Queue(maxsize=500)
        loop = asyncio.get_running_loop()
        stop_event = threading.Event()

        def log_producer():
            try:
                log_stream = container.logs(stream=True, follow=True, tail=100)
                for chunk in log_stream:
                    if stop_event.is_set():
                        break
                    text = chunk.decode('utf-8', errors='ignore')
                    asyncio.run_coroutine_threadsafe(queue.put(text), loop)
            except Exception:
                pass
            finally:
                asyncio.run_coroutine_threadsafe(queue.put(None), loop)

        producer_thread = threading.Thread(target=log_producer, daemon=True)
        producer_thread.start()

        try:
            while True:
                line = await queue.get()
                if line is None:
                    break
                await websocket.send_text(line)
        finally:
            stop_event.set()

    except WebSocketDisconnect:
        pass
    except Exception as ex:
        try:
            await websocket.send_text(f"[Log Stream Notice]: {ex}\n")
        except Exception:
            pass

# -------------------------------------------------------------
# FRONTEND STATIC ASSETS MOUNTING
# -------------------------------------------------------------
DIST_DIR = "/frontend_dist" if os.path.exists("/frontend_dist") else ("/app/dist" if os.path.exists("/app/dist") else os.path.abspath("frontend/dist"))

if os.path.exists(DIST_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(DIST_DIR, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_react_app(full_path: str):
        """Catches all non-API routes and returns index.html for client-side routing."""
        file_path = os.path.join(DIST_DIR, full_path)
        if full_path and os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(DIST_DIR, "index.html"))
else:
    @app.get("/")
    def root_fallback():
        return {
            "message": "BDP Control Center API is live (FastAPI + WebSockets). Frontend build in progress.",
            "docs": "/docs",
            "orchestrator": "/api/orchestrator/matrix",
            "metastore": "/api/metastore/tables"
        }
