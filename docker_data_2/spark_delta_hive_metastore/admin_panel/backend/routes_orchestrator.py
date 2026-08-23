"""
Orchestrator API Router
Provides endpoints for service lifecycle, topological dependency resolution, and operational presets.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
import service_orchestrator
from backend.events_streamer import ws_manager

router = APIRouter(prefix="/api/orchestrator", tags=["Orchestrator"])

class StartRequest(BaseModel):
    services: List[str]

class StopRequest(BaseModel):
    services: List[str]
    cascade: bool = True

class ResolveRequest(BaseModel):
    services: List[str]

@router.get("/matrix")
def get_service_matrix():
    """Returns the live status matrix of all cluster containers."""
    return {
        "services": service_orchestrator.get_service_status_matrix(),
        "presets": service_orchestrator.OPERATIONAL_PRESETS
    }

@router.post("/resolve")
def resolve_dependencies(req: ResolveRequest):
    """Computes topological dependency order for selected services."""
    resolved = service_orchestrator.resolve_dependencies(req.services)
    resolved_meta = [service_orchestrator.SERVICE_REGISTRY[k] for k in resolved if k in service_orchestrator.SERVICE_REGISTRY]
    return {
        "selected": req.services,
        "resolved_order": resolved,
        "resolved_services": resolved_meta
    }

@router.post("/start")
async def start_services(req: StartRequest, bg_tasks: BackgroundTasks):
    """Starts services in topological order."""
    results = service_orchestrator.start_services_sequential(req.services)
    await ws_manager.broadcast({
        "type": "ORCHESTRATOR_ACTION",
        "action": "START",
        "results": results
    })
    return {"status": "SUCCESS", "results": results}

@router.post("/stop")
async def stop_services(req: StopRequest):
    """Stops services with optional downstream cascade."""
    results = service_orchestrator.stop_services_cascade(req.services, cascade=req.cascade)
    await ws_manager.broadcast({
        "type": "ORCHESTRATOR_ACTION",
        "action": "STOP",
        "results": results
    })
    return {"status": "SUCCESS", "results": results}

@router.post("/restart/{service_key}")
async def restart_service(service_key: str):
    """Restarts a single container."""
    success, msg = service_orchestrator.restart_single_service(service_key)
    await ws_manager.broadcast({
        "type": "ORCHESTRATOR_ACTION",
        "action": "RESTART",
        "service": service_key,
        "success": success
    })
    return {"success": success, "message": msg}
