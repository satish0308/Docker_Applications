"""
Orchestrator API Router
Provides endpoints for service lifecycle, topological dependency resolution, operational presets, and SSE streaming pipeline execution.
"""

import json
import asyncio
import docker
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
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

@router.post("/stream-start")
async def stream_start_services(req: StartRequest):
    """
    Streams step-by-step startup milestones in topological sequence via SSE (Server-Sent Events).
    """
    async def event_generator():
        resolved_order = service_orchestrator.resolve_dependencies(req.services)
        total = len(resolved_order)

        # 1. Send initial topological sequence graph
        initial_nodes = []
        for k in resolved_order:
            meta = service_orchestrator.SERVICE_REGISTRY.get(k, {})
            initial_nodes.append({
                "key": k,
                "name": meta.get("name", k),
                "icon": meta.get("icon", "📦"),
                "compose_service": meta.get("compose_service", k),
                "status": "PENDING",
                "msg": "Queued in dependency order..."
            })

        yield f"data: {json.dumps({'type': 'INIT', 'total': total, 'nodes': initial_nodes})}\n\n"
        await asyncio.sleep(0.3)

        # 2. Iterate step by step
        for idx, svc_key in enumerate(resolved_order):
            meta = service_orchestrator.SERVICE_REGISTRY.get(svc_key, {})
            svc_name = meta.get("name", svc_key)
            
            # Step STARTING
            yield f"data: {json.dumps({'type': 'STEP_UPDATE', 'key': svc_key, 'status': 'STARTING', 'step': idx + 1, 'total': total, 'msg': f'Triggering {svc_name}...'})}\n\n"
            await asyncio.sleep(0.4)

            # Execute container start in thread pool
            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(None, service_orchestrator.start_services_sequential, [svc_key])
            
            step_res = res[0] if res else {"status": "UNKNOWN", "msg": ""}
            final_status = "RUNNING" if step_res.get("status") in ["STARTED", "RUNNING"] else ("WARNING" if step_res.get("status") == "WARNING" else "FAILED")

            yield f"data: {json.dumps({'type': 'STEP_UPDATE', 'key': svc_key, 'status': final_status, 'step': idx + 1, 'total': total, 'msg': step_res.get('msg', '')})}\n\n"
            await asyncio.sleep(0.6)

        yield f"data: {json.dumps({'type': 'COMPLETE', 'msg': 'All requested pods in sequence launched successfully.'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.post("/stream-stop")
async def stream_stop_services(req: StopRequest):
    """
    Streams step-by-step shutdown milestones in reverse topological sequence via SSE.
    """
    async def event_generator():
        matrix = service_orchestrator.get_service_status_matrix()
        running_keys = [m["key"] for m in matrix if m["is_running"]]

        targets_to_stop = set(req.services)
        if req.cascade:
            for svc in req.services:
                downstream = service_orchestrator.get_downstream_dependents(svc, running_keys)
                targets_to_stop.update(downstream)

        stop_order = service_orchestrator.resolve_dependencies(list(targets_to_stop))
        stop_order.reverse()
        total = len(stop_order)

        initial_nodes = []
        for k in stop_order:
            meta = service_orchestrator.SERVICE_REGISTRY.get(k, {})
            initial_nodes.append({
                "key": k,
                "name": meta.get("name", k),
                "icon": meta.get("icon", "📦"),
                "compose_service": meta.get("compose_service", k),
                "status": "PENDING",
                "msg": "Queued for shutdown..."
            })

        yield f"data: {json.dumps({'type': 'INIT', 'total': total, 'nodes': initial_nodes})}\n\n"
        await asyncio.sleep(0.3)

        for idx, svc_key in enumerate(stop_order):
            meta = service_orchestrator.SERVICE_REGISTRY.get(svc_key, {})
            svc_name = meta.get("name", svc_key)
            yield f"data: {json.dumps({'type': 'STEP_UPDATE', 'key': svc_key, 'status': 'STOPPING', 'step': idx + 1, 'total': total, 'msg': f'Stopping {svc_name}...'})}\n\n"
            await asyncio.sleep(0.3)

            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(None, service_orchestrator.stop_services_cascade, [svc_key], False)
            step_res = res[0] if res else {"status": "STOPPED", "msg": "Stopped"}

            yield f"data: {json.dumps({'type': 'STEP_UPDATE', 'key': svc_key, 'status': 'STOPPED', 'step': idx + 1, 'total': total, 'msg': step_res.get('msg', '')})}\n\n"
            await asyncio.sleep(0.4)

        yield f"data: {json.dumps({'type': 'COMPLETE', 'msg': 'Requested services stopped.'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.post("/start")
async def start_services(req: StartRequest):
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
