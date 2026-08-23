"""
Table & Database Disaster Recovery and Backup API Router
Provides endpoints for table backup execution, database dump, backup inventory listing, and 1-click restore.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import subprocess
import os
import json
import docker

router = APIRouter(prefix="/api/backup", tags=["Backup & Disaster Recovery"])

BACKUP_PATHS = ["/workspace/backups", "/backups", "./backups"]

class BackupRequest(BaseModel):
    mode: str = "table" # "table" | "database"
    database: str = "default"
    table: Optional[str] = None
    custom_backup_id: Optional[str] = None

class RestoreRequest(BaseModel):
    backup_id: str
    mode: str = "table" # "table" | "database"
    target_database: str = "default"
    target_table: Optional[str] = None
    storage_dest: str = "s3a://warehouse/"

def get_backups_dir() -> str:
    for p in BACKUP_PATHS:
        if os.path.exists(p):
            return p
    os.makedirs(BACKUP_PATHS[0], exist_ok=True)
    return BACKUP_PATHS[0]

@router.get("/list")
def list_backups():
    """Lists all available local table and database backups with checksum and row count metadata."""
    backup_dir = get_backups_dir()
    backups = []
    
    if os.path.exists(backup_dir):
        for entry in sorted(os.listdir(backup_dir), reverse=True):
            entry_path = os.path.join(backup_dir, entry)
            meta_path = os.path.join(entry_path, "metadata.json")
            if os.path.isdir(entry_path) and os.path.exists(meta_path):
                try:
                    with open(meta_path, "r") as f:
                        meta = json.load(f)
                    backups.append(meta)
                except Exception:
                    backups.append({
                        "backup_id": entry,
                        "backup_type": "table",
                        "status": "VALID",
                        "created_at": "Unknown",
                        "source_table": entry
                    })
    return {"backups": backups}

@router.post("/execute")
def execute_backup(req: BackupRequest):
    """Triggers table or complete database backup inside the Spark container."""
    try:
        client = docker.from_env()
        spark_cont = client.containers.get("spark")
    except Exception as ex:
        raise HTTPException(status_code=500, detail=f"Failed to connect to Spark container: {ex}")

    if req.mode == "database":
        cmd = f"/opt/spark/bin/spark-submit /opt/spark/scripts/backup_restore_table.py backup-db --database {req.database}"
    else:
        table_name = req.table or "sales"
        cmd = f"/opt/spark/bin/spark-submit /opt/spark/scripts/backup_restore_table.py backup --table {req.database}.{table_name}"
    
    if req.custom_backup_id and req.custom_backup_id.strip():
        cmd += f" --backup-id {req.custom_backup_id.strip()}"

    res = spark_cont.exec_run(cmd)
    output = res.output.decode("utf-8", errors="ignore")
    
    if res.exit_code != 0:
        raise HTTPException(status_code=500, detail=output)
    
    return {
        "status": "SUCCESS",
        "command": cmd,
        "output": output
    }

@router.post("/restore")
def execute_restore(req: RestoreRequest):
    """Restores a table or database backup in-place or to a cloned target."""
    try:
        client = docker.from_env()
        spark_cont = client.containers.get("spark")
    except Exception as ex:
        raise HTTPException(status_code=500, detail=f"Failed to connect to Spark container: {ex}")

    if req.mode == "database":
        cmd = f"/opt/spark/bin/spark-submit /opt/spark/scripts/backup_restore_table.py restore-db --backup-id {req.backup_id} --database {req.target_database} --storage-dest {req.storage_dest}"
    else:
        target_tbl = req.target_table or ""
        cmd = f"/opt/spark/bin/spark-submit /opt/spark/scripts/backup_restore_table.py restore --backup-id {req.backup_id} --target-table {target_tbl} --storage-dest {req.storage_dest}"
    
    res = spark_cont.exec_run(cmd)
    output = res.output.decode("utf-8", errors="ignore")
    
    if res.exit_code != 0:
        raise HTTPException(status_code=500, detail=output)
    
    return {
        "status": "SUCCESS",
        "backup_id": req.backup_id,
        "command": cmd,
        "output": output
    }
