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
            if not os.path.isdir(entry_path) or entry.startswith("."):
                continue
            
            manifest_file = None
            for candidate in ["backup_manifest.json", "metadata.json", "manifest.json"]:
                p = os.path.join(entry_path, candidate)
                if os.path.exists(p):
                    manifest_file = p
                    break
            
            if manifest_file:
                try:
                    with open(manifest_file, "r") as f:
                        meta = json.load(f)
                    backups.append({
                        "backup_id": meta.get("backup_id", entry),
                        "database_name": meta.get("database", meta.get("database_name", "default")),
                        "table_name": meta.get("table", meta.get("table_name", "")),
                        "timestamp": meta.get("created_at", meta.get("timestamp", "Unknown")),
                        "size": f"{meta.get('total_size_mb', 0)} MB" if "total_size_mb" in meta else meta.get("size", "Unknown"),
                        "total_rows": meta.get("total_rows", "N/A"),
                        "format": meta.get("format", "Parquet"),
                        "original_location": meta.get("original_location", "")
                    })
                except Exception:
                    pass
            else:
                backups.append({
                    "backup_id": entry,
                    "database_name": "default",
                    "table_name": entry,
                    "timestamp": "Unknown",
                    "size": "Unknown",
                    "total_rows": "N/A",
                    "format": "Unknown",
                    "original_location": ""
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
        cmd = f"/opt/spark/bin/spark-submit --driver-memory 2g /opt/spark/python_scripts/backup_restore_table.py backup-db --database {req.database}"
    else:
        table_name = req.table or "sales"
        cmd = f"/opt/spark/bin/spark-submit --driver-memory 2g /opt/spark/python_scripts/backup_restore_table.py backup --table {req.database}.{table_name}"
    
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
        cmd = f"/opt/spark/bin/spark-submit --driver-memory 2g /opt/spark/python_scripts/backup_restore_table.py restore-db --backup-id {req.backup_id} --database {req.target_database} --storage-dest {req.storage_dest}"
    else:
        target_tbl_arg = f"--target-table {req.target_table}" if req.target_table else ""
        cmd = f"/opt/spark/bin/spark-submit --driver-memory 2g /opt/spark/python_scripts/backup_restore_table.py restore --backup-id {req.backup_id} --database {req.target_database} {target_tbl_arg} --storage-dest {req.storage_dest}"
    
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
