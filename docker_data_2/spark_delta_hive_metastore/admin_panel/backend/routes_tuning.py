"""
Spark Tuning & Cluster Scaling API Router
Provides endpoints for workload sizing profiles, dynamic resource allocation (DRA), custom parameter compilation,
horizontal worker fleet scaling, and live Spark Master telemetry.
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

class CompileCommandRequest(BaseModel):
    params: Dict[str, Any]
    script_name: Optional[str] = "<job_script.py>"

@router.get("/config")
def get_tuning_config():
    """Returns the current active tuning profile, active params, worker fleet scaling settings, cluster metrics, presets, and connection strings."""
    cfg = spark_tuning_manager.load_tuning_config()
    metrics = spark_tuning_manager.get_spark_master_metrics()
    active_profile_name = cfg.get("active_profile", "🔴 Heavy (Large Big Data / >10M Rows)")
    active_params = cfg.get("params", spark_tuning_manager.PROFILES.get("🔴 Heavy (Large Big Data / >10M Rows)", {}))
    
    worker_scaling = cfg.get("worker_scaling", {
        "worker_count": metrics.get("alive_workers", 4) or 4,
        "worker_ram": "4G",
        "worker_cores": 4
    })

    connections = {
        "spark_rpc": "spark://spark:7077",
        "spark_master_ui": "http://localhost:8089",
        "spark_history_ui": "http://localhost:18080",
        "spark_thriftserver": "localhost:10000",
        "livy_rest_api": "http://localhost:8998",
        "hdfs_namenode": "hdfs://namenode:9000"
    }

    return {
        "active_profile": active_profile_name,
        "active_params": active_params,
        "config": cfg,
        "worker_scaling": worker_scaling,
        "metrics": metrics,
        "presets": spark_tuning_manager.PROFILES,
        "connections": connections
    }

@router.post("/scale-workers")
def scale_workers(req: ScalingRequest):
    """Horizontally scales the Spark worker container fleet on-demand and persists settings."""
    msg, exit_code = spark_tuning_manager.scale_cluster_workers(
        target_count=req.worker_count,
        worker_memory=req.worker_ram,
        worker_cores=req.worker_cores
    )
    if exit_code != 0:
        raise HTTPException(status_code=500, detail=msg)
    return {"status": "SUCCESS", "message": msg}

@router.post("/apply-profile")
def apply_profile(req: ProfileApplyRequest):
    """Applies a workload sizing profile or custom parameters across spark-defaults, Livy, and Hue."""
    if req.custom_params:
        profile_data = req.custom_params
    else:
        profile_data = spark_tuning_manager.PROFILES.get(req.profile_name)
        if not profile_data:
            raise HTTPException(status_code=400, detail="Profile not found.")
    
    spark_tuning_manager.save_tuning_config({"active_profile": req.profile_name, "params": profile_data})
    cmd_flags = spark_tuning_manager.build_spark_submit_conf_args(profile_data)
    
    return {
        "status": "SUCCESS",
        "message": f"Profile '{req.profile_name}' applied successfully across Spark, Livy, and Hue!",
        "generated_command": f"/opt/spark/bin/spark-submit {cmd_flags} <job_script.py>"
    }

@router.post("/compile-command")
def compile_command(req: CompileCommandRequest):
    """Compiles spark-submit CLI flags from parameter dictionary."""
    cmd_flags = spark_tuning_manager.build_spark_submit_conf_args(req.params)
    return {
        "flags": cmd_flags,
        "full_command": f"/opt/spark/bin/spark-submit {cmd_flags} {req.script_name}"
    }
