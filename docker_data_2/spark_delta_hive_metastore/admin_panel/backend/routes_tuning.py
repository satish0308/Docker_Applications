"""
Spark Tuning & Cluster Scaling API Router
Provides endpoints for workload sizing profiles, dynamic resource allocation (DRA), and horizontal worker fleet scaling.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
import spark_tuning_manager

router = APIRouter(prefix="/api/tuning", tags=["Spark Tuning & Scaling"])

class ScalingRequest(BaseModel):
    worker_count: int
    worker_ram: str
    worker_cores: int

class ProfileApplyRequest(BaseModel):
    profile_name: str
    custom_params: Optional[Dict[str, Any]] = None

@router.get("/config")
def get_tuning_config():
    """Returns the current active tuning profile, cluster metrics, and presets."""
    cfg = spark_tuning_manager.load_tuning_config()
    metrics = spark_tuning_manager.get_spark_master_metrics()
    workers = spark_tuning_manager.get_registered_workers_info()
    return {
        "active_profile": cfg.get("active_profile", "Heavy Analytical"),
        "config": cfg,
        "metrics": metrics,
        "workers": workers,
        "presets": spark_tuning_manager.PRESET_PROFILES
    }

@router.post("/scale-workers")
def scale_workers(req: ScalingRequest):
    """Horizontally scales the Spark worker container fleet on-demand."""
    success, msg = spark_tuning_manager.scale_spark_workers(
        target_worker_count=req.worker_count,
        worker_ram=req.worker_ram,
        worker_cores=req.worker_cores
    )
    if not success:
        raise HTTPException(status_code=500, detail=msg)
    return {"status": "SUCCESS", "message": msg}

@router.post("/apply-profile")
def apply_profile(req: ProfileApplyRequest):
    """Applies a workload sizing profile across spark-defaults, Livy, and Hue."""
    success, msg = spark_tuning_manager.apply_profile(
        profile_name=req.profile_name,
        custom_params=req.custom_params
    )
    if not success:
        raise HTTPException(status_code=500, detail=msg)
    return {"status": "SUCCESS", "message": msg}
