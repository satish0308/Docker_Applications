"""
Table & Database Disaster Recovery and Backup API Router
Provides endpoints for table backup execution, database dump, backup inventory listing, 1-click restore,
persistent decoupled background execution jobs, automated disaster recovery scheduling, and automated retention / pruning.
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
BACKUP_JOBS_FILE = "backup_execution_jobs.json"

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

def load_backup_jobs() -> List[Dict[str, Any]]:
    if os.path.exists(BACKUP_JOBS_FILE):
        try:
            with open(BACKUP_JOBS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_backup_jobs(jobs: List[Dict[str, Any]]):
    with open(BACKUP_JOBS_FILE, "w") as f:
        json.dump(jobs, f, indent=2)

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

# -------------------------------------------------------------
# DYNAMIC SPARK TUNING RESOLUTION FOR BACKUP / RESTORE
# -------------------------------------------------------------

def get_backup_tuning_flags() -> str:
    """Reads active cluster dynamic tuning profile and constructs optimized spark-submit arguments."""
    p = {}
    config_paths = ["/app/spark_tuning_config.json", "spark_tuning_config.json", "admin_panel/spark_tuning_config.json"]
    for cp in config_paths:
        if os.path.exists(cp):
            try:
                with open(cp, "r") as f:
                    data = json.load(f)
                    p = data.get("params") or data.get("active_params") or {}
                    if p:
                        break
            except Exception:
                pass

    drv_mem = p.get("driver_memory", "4g")
    exe_mem = p.get("executor_memory", "6g")
    exe_cores = str(p.get("executor_cores", 2))
    max_cores = str(p.get("max_cores", 6))
    shuffle_parts = str(p.get("shuffle_partitions", 64))
    dra = "true" if p.get("dynamic_allocation", True) else "false"
    aqe = "true" if p.get("aqe_enabled", True) else "false"
    mem_frac = str(p.get("memory_fraction", 0.8))
    storage_frac = str(p.get("storage_fraction", 0.3))

    flags = [
        f"--driver-memory {drv_mem}",
        f"--conf spark.executor.memory={exe_mem}",
        f"--conf spark.executor.cores={exe_cores}",
        f"--conf spark.cores.max={max_cores}",
        f"--conf spark.sql.shuffle.partitions={shuffle_parts}",
        f"--conf spark.dynamicAllocation.enabled={dra}",
        f"--conf spark.sql.adaptive.enabled={aqe}",
        f"--conf spark.memory.fraction={mem_frac}",
        f"--conf spark.memory.storageFraction={storage_frac}",
        "--conf spark.sql.parquet.columnarReaderBatchSize=1024",
        "--conf spark.sql.files.maxPartitionBytes=67108864",
        "--conf spark.network.timeout=800s",
        "--conf spark.executor.heartbeatInterval=60s"
    ]

    if p.get("offheap_enabled", False) and str(p.get("offheap_size", "0")) not in ["0", "0g", "0m", ""]:
        flags.append("--conf spark.memory.offHeap.enabled=true")
        flags.append(f"--conf spark.memory.offHeap.size={p.get('offheap_size', '1g')}")

    if p.get("kryo_serializer", True):
        flags.append("--conf spark.serializer=org.apache.spark.serializer.KryoSerializer")

    return " ".join(flags)

# -------------------------------------------------------------
# ASYNCHRONOUS DECOUPLED EXECUTION RUNNERS
# -------------------------------------------------------------

def run_backup_background(job_id: str, mode: str, database: str, table: Optional[str], custom_backup_id: Optional[str], retention_count: Optional[int]):
    """Decoupled background worker executing backup inside Spark container using dynamic tuning specs."""
    t0 = time.time()
    try:
        client = docker.from_env()
        spark_cont = client.containers.get("spark")
        tuning_flags = get_backup_tuning_flags()

        if mode == "database":
            cmd = f"/opt/spark/bin/spark-submit {tuning_flags} /opt/spark/python_scripts/backup_restore_table.py backup-db --database {database}"
        else:
            table_name = table or "sales"
            cmd = f"/opt/spark/bin/spark-submit {tuning_flags} /opt/spark/python_scripts/backup_restore_table.py backup --table {database}.{table_name}"
        
        if custom_backup_id and custom_backup_id.strip():
            cmd += f" --backup-id {custom_backup_id.strip()}"

        res = spark_cont.exec_run(cmd)
        output = res.output.decode("utf-8", errors="ignore")
        elapsed = round(time.time() - t0, 2)

        pruned = []
        if res.exit_code == 0 and retention_count and retention_count > 0:
            pruned = prune_old_backups(database, table, mode, retention_count)

        jobs = load_backup_jobs()
        for j in jobs:
            if j.get("job_id") == job_id:
                j["status"] = "SUCCESS" if res.exit_code == 0 else "FAILED"
                j["completed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                j["elapsed_seconds"] = elapsed
                j["exit_code"] = res.exit_code
                j["output"] = output
                j["recent_logs"] = output[-4000:] if output else ""
                j["pruned_archives"] = pruned
                break
        save_backup_jobs(jobs)

    except Exception as ex:
        elapsed = round(time.time() - t0, 2)
        jobs = load_backup_jobs()
        for j in jobs:
            if j.get("job_id") == job_id:
                j["status"] = "FAILED"
                j["completed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                j["elapsed_seconds"] = elapsed
                j["error"] = str(ex)
                j["recent_logs"] = f"Execution Error: {ex}"
                break
        save_backup_jobs(jobs)

def run_restore_background(job_id: str, backup_id: str, mode: str, target_database: str, target_table: Optional[str], storage_dest: str):
    """Decoupled background worker executing restore inside Spark container using dynamic tuning specs."""
    t0 = time.time()
    try:
        client = docker.from_env()
        spark_cont = client.containers.get("spark")
        tuning_flags = get_backup_tuning_flags()

        if mode == "database":
            cmd = f"/opt/spark/bin/spark-submit {tuning_flags} /opt/spark/python_scripts/backup_restore_table.py restore-db --backup-id {backup_id} --database {target_database} --storage-dest {storage_dest}"
        else:
            target_tbl_arg = f"--target-table {target_table}" if target_table else ""
            cmd = f"/opt/spark/bin/spark-submit {tuning_flags} /opt/spark/python_scripts/backup_restore_table.py restore --backup-id {backup_id} --database {target_database} {target_tbl_arg} --storage-dest {storage_dest}"
        
        res = spark_cont.exec_run(cmd)
        output = res.output.decode("utf-8", errors="ignore")
        elapsed = round(time.time() - t0, 2)

        jobs = load_backup_jobs()
        for j in jobs:
            if j.get("job_id") == job_id:
                j["status"] = "SUCCESS" if res.exit_code == 0 else "FAILED"
                j["completed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                j["elapsed_seconds"] = elapsed
                j["exit_code"] = res.exit_code
                j["output"] = output
                j["recent_logs"] = output[-4000:] if output else ""
                break
        save_backup_jobs(jobs)

    except Exception as ex:
        elapsed = round(time.time() - t0, 2)
        jobs = load_backup_jobs()
        for j in jobs:
            if j.get("job_id") == job_id:
                j["status"] = "FAILED"
                j["completed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                j["elapsed_seconds"] = elapsed
                j["error"] = str(ex)
                j["recent_logs"] = f"Execution Error: {ex}"
                break
        save_backup_jobs(jobs)

# -------------------------------------------------------------
# API ROUTER ENDPOINTS
# -------------------------------------------------------------

@router.get("/jobs")
def get_backup_jobs():
    """Returns persistent list of all backup and restore execution jobs."""
    return {"jobs": load_backup_jobs()}

@router.delete("/jobs/clear-all")
def clear_all_backup_jobs():
    """Clears all historical backup/restore execution jobs."""
    save_backup_jobs([])
    return {"status": "SUCCESS", "message": "Backup job history cleared."}

@router.delete("/jobs/{job_id}")
def delete_backup_job(job_id: str):
    """Deletes a specific backup/restore job record from history."""
    if job_id == "clear-all":
        save_backup_jobs([])
        return {"status": "SUCCESS", "message": "Backup job history cleared."}
    jobs = load_backup_jobs()
    updated = [j for j in jobs if j.get("job_id") != job_id]
    save_backup_jobs(updated)
    return {"status": "DELETED", "job_id": job_id}

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
    """Triggers table or complete database backup asynchronously in background with persistent job tracking."""
    job_id = f"job_bkp_{int(time.time())}_{uuid.uuid4().hex[:4]}"
    target_label = f"Database: {req.database}" if req.mode == "database" else f"Table: {req.database}.{req.table or 'sales'}"

    new_job = {
        "job_id": job_id,
        "action_type": "BACKUP",
        "mode": req.mode,
        "database": req.database,
        "table": req.table if req.mode == "table" else None,
        "target_label": target_label,
        "custom_backup_id": req.custom_backup_id,
        "retention_count": req.retention_count,
        "status": "RUNNING",
        "submitted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "completed_at": None,
        "elapsed_seconds": None,
        "recent_logs": f"Initializing Spark backup job for {target_label}...",
        "output": "",
        "error": None
    }

    jobs = load_backup_jobs()
    jobs.insert(0, new_job)
    save_backup_jobs(jobs)

    t = threading.Thread(
        target=run_backup_background,
        args=(job_id, req.mode, req.database, req.table, req.custom_backup_id, req.retention_count),
        daemon=True
    )
    t.start()

    return {
        "status": "SUBMITTED",
        "job_id": job_id,
        "job": new_job
    }

@router.post("/restore")
def execute_restore(req: RestoreRequest):
    """Restores a table or database backup asynchronously in background with persistent job tracking."""
    job_id = f"job_rst_{int(time.time())}_{uuid.uuid4().hex[:4]}"
    target_label = f"Database: {req.target_database}" if req.mode == "database" else f"Table: {req.target_database}.{req.target_table or 'original'}"

    new_job = {
        "job_id": job_id,
        "action_type": "RESTORE",
        "backup_id": req.backup_id,
        "mode": req.mode,
        "target_database": req.target_database,
        "target_table": req.target_table,
        "storage_dest": req.storage_dest,
        "target_label": target_label,
        "status": "RUNNING",
        "submitted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "completed_at": None,
        "elapsed_seconds": None,
        "recent_logs": f"Initializing Spark table/db restore from snapshot {req.backup_id}...",
        "output": "",
        "error": None
    }

    jobs = load_backup_jobs()
    jobs.insert(0, new_job)
    save_backup_jobs(jobs)

    t = threading.Thread(
        target=run_restore_background,
        args=(job_id, req.backup_id, req.mode, req.target_database, req.target_table, req.storage_dest),
        daemon=True
    )
    t.start()

    return {
        "status": "SUBMITTED",
        "job_id": job_id,
        "job": new_job
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
            bkp_req = BackupRequest(
                mode=s.get("mode", "table"),
                database=s.get("database", "default"),
                table=s.get("table"),
                retention_count=s.get("retention_count", 3)
            )
            res = execute_backup(bkp_req)
            s["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            s["last_status"] = "TRIGGERED"
            interval_sec = s.get("interval_seconds", 3600)
            s["next_run"] = (datetime.now() + timedelta(seconds=interval_sec)).strftime("%Y-%m-%d %H:%M:%S")
            save_backup_schedules(schedules)
            return {"status": "SUCCESS", "message": f"Backup policy '{s.get('name')}' triggered successfully.", "job": res.get("job")}

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
