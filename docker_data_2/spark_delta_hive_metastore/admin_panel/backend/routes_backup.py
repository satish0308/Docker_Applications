"""
Table & Database Disaster Recovery and Backup API Router
Provides endpoints for table backup execution, database dump, backup inventory listing, 1-click restore,
automated disaster recovery scheduling, and automated retention / pruning.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import subprocess
import os
import shutil
import json
import time
import uuid
import threading
from datetime import datetime, timedelta
import docker

router = APIRouter(prefix="/api/backup", tags=["Backup & Disaster Recovery"])

BACKUP_PATHS = ["/workspace/backups", "/backups", "./backups"]
BACKUP_SCHEDULES_FILE = "backup_schedules.json"

FREQUENCY_INTERVAL_MAP = {
    "1h": 3600,
    "2h": 7200,
    "6h": 21600,
    "10h": 36000,
    "24h": 86400,
    "1 Hour": 3600,
    "2 Hours": 7200,
    "6 Hours": 21600,
    "10 Hours": 36000,
    "Every Day": 86400,
    "Daily": 86400
}

class BackupRequest(BaseModel):
    mode: str = "table" # "table" | "database"
    database: str = "default"
    table: Optional[str] = None
    custom_backup_id: Optional[str] = None
    retention_count: Optional[int] = None

class RestoreRequest(BaseModel):
    backup_id: str
    mode: str = "table" # "table" | "database"
    target_database: str = "default"
    target_table: Optional[str] = None
    storage_dest: str = "s3a://warehouse/"

class BackupScheduleRequest(BaseModel):
    name: str
    mode: str = "table" # "table" | "database"
    database: str = "default"
    table: Optional[str] = None
    frequency: str = "1h" # "1h" | "2h" | "6h" | "10h" | "24h"
    retention_count: int = 3 # Keep last N backups
    storage_dest: str = "s3a://warehouse/"

class PruneRequest(BaseModel):
    database: str = "default"
    table: Optional[str] = None
    mode: str = "table" # "table" | "database"
    retention_count: int = 3

def get_backups_dir() -> str:
    for p in BACKUP_PATHS:
        if os.path.exists(p):
            return p
    os.makedirs(BACKUP_PATHS[0], exist_ok=True)
    return BACKUP_PATHS[0]

def get_dir_size_mb(path: str) -> float:
    """Calculates recursive directory disk space in MB."""
    total_bytes = 0
    try:
        for dirpath, _, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if os.path.exists(fp):
                    total_bytes += os.path.getsize(fp)
    except Exception:
        pass
    return round(total_bytes / (1024 * 1024), 2)

def get_dir_mtime_str(path: str) -> str:
    """Gets formatted directory last modified timestamp."""
    try:
        mtime = os.path.getmtime(path)
        return datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def load_backup_schedules() -> List[Dict[str, Any]]:
    if os.path.exists(BACKUP_SCHEDULES_FILE):
        try:
            with open(BACKUP_SCHEDULES_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_backup_schedules(schedules: List[Dict[str, Any]]):
    with open(BACKUP_SCHEDULES_FILE, "w") as f:
        json.dump(schedules, f, indent=2)

def prune_old_backups(database: str, table: Optional[str], mode: str, retention_count: int) -> List[str]:
    """Prunes older backup archives for the specified table/database exceeding the retention limit."""
    if retention_count < 1:
        return []
    
    backup_dir = get_backups_dir()
    if not os.path.exists(backup_dir):
        return []
    
    matching_backups = []
    for entry in os.listdir(backup_dir):
        entry_path = os.path.join(backup_dir, entry)
        if not os.path.isdir(entry_path) or entry.startswith("."):
            continue
        
        # Determine if this backup matches target
        is_match = False
        if mode == "database":
            if entry.startswith("db_backup_") and f"_{database}" in entry:
                is_match = True
        else:
            tbl_target = table or ""
            if entry.startswith("backup_") and (f"_{database}_{tbl_target}" in entry or f"_{tbl_target}" in entry):
                is_match = True
        
        if is_match:
            mtime = os.path.getmtime(entry_path)
            matching_backups.append((entry, entry_path, mtime))
    
    # Sort newest first
    matching_backups.sort(key=lambda x: x[2], reverse=True)
    
    pruned = []
    # If count exceeds retention, delete older archives
    if len(matching_backups) > retention_count:
        to_delete = matching_backups[retention_count:]
        for entry_name, entry_path, _ in to_delete:
            try:
                shutil.rmtree(entry_path, ignore_errors=True)
                pruned.append(entry_name)
            except Exception as ex:
                print(f"Error pruning backup {entry_name}: {ex}")
    
    return pruned

@router.get("/list")
def list_backups():
    """Lists all available local table and database backups with checksum, size, and row count metadata."""
    backup_dir = get_backups_dir()
    backups = []
    
    if os.path.exists(backup_dir):
        for entry in sorted(os.listdir(backup_dir), reverse=True):
            entry_path = os.path.join(backup_dir, entry)
            if not os.path.isdir(entry_path) or entry.startswith("."):
                continue
            
            fallback_mtime = get_dir_mtime_str(entry_path)
            fallback_size_mb = get_dir_size_mb(entry_path)
            is_db_backup = entry.startswith("db_backup_") or os.path.isdir(os.path.join(entry_path, "tables"))
            
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
                    
                    calc_size = meta.get("total_size_mb")
                    if not calc_size or float(calc_size) == 0.0:
                        calc_size = fallback_size_mb
                    
                    time_val = meta.get("created_at") or meta.get("timestamp") or fallback_mtime
                    b_type = meta.get("backup_type") or ("database" if is_db_backup else "table")
                    
                    backups.append({
                        "backup_id": meta.get("backup_id", entry),
                        "backup_type": b_type,
                        "database_name": meta.get("database", meta.get("database_name", "default")),
                        "table_name": meta.get("table", meta.get("table_name", f"{meta.get('total_tables', 'Full')} Tables" if b_type == "database" else entry)),
                        "timestamp": time_val,
                        "size": f"{calc_size} MB",
                        "total_rows": meta.get("total_rows", "N/A"),
                        "total_tables": meta.get("total_tables", len(meta.get("tables", {})) if b_type == "database" else 1),
                        "format": meta.get("format", "Parquet"),
                        "original_location": meta.get("original_location", "")
                    })
                except Exception:
                    backups.append({
                        "backup_id": entry,
                        "backup_type": "database" if is_db_backup else "table",
                        "database_name": "default",
                        "table_name": "Full Database" if is_db_backup else entry,
                        "timestamp": fallback_mtime,
                        "size": f"{fallback_size_mb} MB",
                        "total_rows": "N/A",
                        "total_tables": 1,
                        "format": "Parquet",
                        "original_location": ""
                    })
            else:
                backups.append({
                    "backup_id": entry,
                    "backup_type": "database" if is_db_backup else "table",
                    "database_name": "default",
                    "table_name": "Full Database" if is_db_backup else entry,
                    "timestamp": fallback_mtime,
                    "size": f"{fallback_size_mb} MB",
                    "total_rows": "N/A",
                    "total_tables": 1,
                    "format": "Parquet",
                    "original_location": ""
                })
    return {"backups": backups}

@router.post("/execute")
def execute_backup(req: BackupRequest):
    """Triggers table or complete database backup inside the Spark container with optional retention pruning."""
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
    
    pruned_archives = []
    if req.retention_count and req.retention_count > 0:
        pruned_archives = prune_old_backups(req.database, req.table, req.mode, req.retention_count)

    return {
        "status": "SUCCESS",
        "command": cmd,
        "output": output,
        "pruned_archives": pruned_archives
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

@router.delete("/{backup_id}")
def delete_backup_archive(backup_id: str):
    """Deletes a specific backup snapshot directory from disk."""
    backup_dir = get_backups_dir()
    target_path = os.path.join(backup_dir, backup_id)
    if not os.path.exists(target_path):
        raise HTTPException(status_code=404, detail="Backup snapshot archive not found.")
    
    shutil.rmtree(target_path, ignore_errors=True)
    return {"status": "SUCCESS", "message": f"Backup snapshot '{backup_id}' deleted successfully."}

@router.post("/prune")
def trigger_manual_pruning(req: PruneRequest):
    """Manually prunes old backups according to specified retention count."""
    pruned = prune_old_backups(req.database, req.table, req.mode, req.retention_count)
    return {"status": "SUCCESS", "pruned_count": len(pruned), "pruned_archives": pruned}

# -------------------------------------------------------------
# AUTOMATED DISASTER RECOVERY & SCHEDULED POLICIES
# -------------------------------------------------------------

@router.get("/schedules")
def get_backup_schedules():
    """Lists all configured disaster recovery auto-backup policies."""
    return {"schedules": load_backup_schedules()}

@router.post("/schedules")
def create_backup_schedule(req: BackupScheduleRequest):
    """Creates or updates an automated backup schedule with auto-pruning retention."""
    interval_sec = FREQUENCY_INTERVAL_MAP.get(req.frequency, 3600)
    schedule_id = f"sched_bkp_{int(time.time())}_{uuid.uuid4().hex[:4]}"
    now = datetime.now()
    next_run_dt = now + timedelta(seconds=interval_sec)

    schedule_record = {
        "schedule_id": schedule_id,
        "name": req.name,
        "mode": req.mode,
        "database": req.database,
        "table": req.table if req.mode == "table" else None,
        "frequency": req.frequency,
        "interval_seconds": interval_sec,
        "retention_count": max(1, req.retention_count),
        "storage_dest": req.storage_dest,
        "enabled": True,
        "created_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "last_run": "Never",
        "last_status": "QUEUED",
        "next_run": next_run_dt.strftime("%Y-%m-%d %H:%M:%S")
    }

    schedules = load_backup_schedules()
    schedules.insert(0, schedule_record)
    save_backup_schedules(schedules)
    return {"status": "SUCCESS", "schedule": schedule_record}

@router.post("/schedules/{schedule_id}/toggle")
def toggle_backup_schedule(schedule_id: str):
    """Toggles active/paused status of an automated backup schedule."""
    schedules = load_backup_schedules()
    found = False
    for s in schedules:
        if s.get("schedule_id") == schedule_id:
            s["enabled"] = not s.get("enabled", True)
            if s["enabled"]:
                interval_sec = s.get("interval_seconds", 3600)
                s["next_run"] = (datetime.now() + timedelta(seconds=interval_sec)).strftime("%Y-%m-%d %H:%M:%S")
            found = True
            break
    if not found:
        raise HTTPException(status_code=404, detail="Schedule not found")
    save_backup_schedules(schedules)
    return {"status": "SUCCESS", "schedules": schedules}

@router.delete("/schedules/{schedule_id}")
def delete_backup_schedule(schedule_id: str):
    """Deletes an automated backup policy."""
    schedules = load_backup_schedules()
    new_scheds = [s for s in schedules if s.get("schedule_id") != schedule_id]
    save_backup_schedules(new_scheds)
    return {"status": "SUCCESS", "schedules": new_scheds}

@router.post("/schedules/{schedule_id}/run-now")
def run_backup_schedule_now(schedule_id: str):
    """Triggers immediate execution of a scheduled backup policy and applies retention pruning."""
    schedules = load_backup_schedules()
    for s in schedules:
        if s.get("schedule_id") == schedule_id:
            # Execute backup
            bkp_req = BackupRequest(
                mode=s.get("mode", "table"),
                database=s.get("database", "default"),
                table=s.get("table"),
                retention_count=s.get("retention_count", 3)
            )
            try:
                res = execute_backup(bkp_req)
                s["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                s["last_status"] = "SUCCESS"
                interval_sec = s.get("interval_seconds", 3600)
                s["next_run"] = (datetime.now() + timedelta(seconds=interval_sec)).strftime("%Y-%m-%d %H:%M:%S")
                save_backup_schedules(schedules)
                return {"status": "SUCCESS", "message": f"Backup policy '{s.get('name')}' executed successfully.", "details": res}
            except Exception as ex:
                s["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                s["last_status"] = "FAILED"
                save_backup_schedules(schedules)
                raise HTTPException(status_code=500, detail=str(ex))

    raise HTTPException(status_code=404, detail="Schedule not found")

# -------------------------------------------------------------
# BACKGROUND DISASTER RECOVERY SCHEDULER DAEMON
# -------------------------------------------------------------

def backup_scheduler_daemon_loop():
    """Lightweight background thread evaluating scheduled backup triggers every 30 seconds."""
    while True:
        try:
            time.sleep(30)
            schedules = load_backup_schedules()
            now = datetime.now()
            modified = False

            for s in schedules:
                if not s.get("enabled", True):
                    continue

                next_run_str = s.get("next_run")
                if not next_run_str:
                    continue

                try:
                    next_run_dt = datetime.strptime(next_run_str, "%Y-%m-%d %H:%M:%S")
                except Exception:
                    continue

                if now >= next_run_dt:
                    print(f"⏰ [DISASTER RECOVERY DAEMON] Triggering automated backup policy: {s.get('name')}")
                    try:
                        bkp_req = BackupRequest(
                            mode=s.get("mode", "table"),
                            database=s.get("database", "default"),
                            table=s.get("table"),
                            retention_count=s.get("retention_count", 3)
                        )
                        execute_backup(bkp_req)
                        s["last_status"] = "SUCCESS"
                    except Exception as ex:
                        print(f"⚠️ [DISASTER RECOVERY DAEMON] Auto backup policy failed: {ex}")
                        s["last_status"] = "FAILED"

                    s["last_run"] = now.strftime("%Y-%m-%d %H:%M:%S")
                    interval_sec = s.get("interval_seconds", 3600)
                    s["next_run"] = (now + timedelta(seconds=interval_sec)).strftime("%Y-%m-%d %H:%M:%S")
                    modified = True

            if modified:
                save_backup_schedules(schedules)
        except Exception as err:
            print(f"Error in backup scheduler daemon: {err}")

# Launch daemon thread
_daemon_thread = threading.Thread(target=backup_scheduler_daemon_loop, daemon=True)
_daemon_thread.start()
