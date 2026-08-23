"""
SQL Studio API Router
Executes heavy Spark SQL analytical queries asynchronously and persists job state across client sessions.
"""

import os
import json
import time
import uuid
import threading
import docker
import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from backend.events_streamer import ws_manager

router = APIRouter(prefix="/api/sql", tags=["SQL Studio"])

SQL_JOBS_FILE = "sql_query_jobs.json"

def load_sql_query_jobs():
    if os.path.exists(SQL_JOBS_FILE):
        try:
            with open(SQL_JOBS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_sql_query_jobs(jobs):
    with open(SQL_JOBS_FILE, "w") as f:
        json.dump(jobs, f, indent=2)

def clean_spark_sql_output(raw_output: str) -> str:
    """Strips JVM startup notices, environment logs, and Spark noise, returning ONLY the clean SQL tabular result or execution notice."""
    if not raw_output:
        return "Query executed successfully. (0 output rows returned)"
    
    lines = raw_output.splitlines()
    clean_lines = []
    
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        # Skip JVM options notices & Spark log noise
        if stripped.startswith("NOTE: Picked up JDK_JAVA_OPTIONS:") or \
           stripped.startswith("Setting default log level to") or \
           stripped.startswith("To adjust logging level use") or \
           stripped.startswith("Spark Web UI available at") or \
           stripped.startswith("Spark master:") or \
           "WARN MetricsConfig:" in stripped or \
           "WARN SparkStringUtils:" in stripped or \
           "WARN Utils: Service 'SparkUI'" in stripped or \
           "WARN NativeCodeLoader:" in stripped or \
           "HiveConf of name" in stripped or \
           "WARN ObjectStore:" in stripped or \
           "INFO ObjectStore:" in stripped or \
           "INFO HiveMetaStore:" in stripped or \
           "INFO audit:" in stripped or \
           "INFO SparkContext:" in stripped or \
           "INFO MemoryStore:" in stripped or \
           "INFO BlockManager:" in stripped or \
           "WARN SparkConf:" in stripped:
            continue
        clean_lines.append(line)
    
    cleaned = "\n".join(clean_lines).strip()
    if not cleaned:
        return "Query executed successfully. (0 output rows returned)"
    return cleaned

def execute_query_background(query_id: str, query_sql: str):
    """Executes query inside Spark container decoupled in background."""
    try:
        client = docker.from_env()
        spark_cont = client.containers.get("spark")

        clean_sql = query_sql.replace('"', '\\"').replace('\n', ' ')
        cmd = f'/opt/spark/bin/spark-sql -e "{clean_sql}"'

        # Execute
        res = spark_cont.exec_run(cmd)
        output_str = res.output.decode('utf-8', errors='ignore')
        cleaned_preview = clean_spark_sql_output(output_str)

        jobs = load_sql_query_jobs()
        for j in jobs:
            if j["query_id"] == query_id:
                j["status"] = "SUCCESS" if res.exit_code == 0 else "FAILED"
                j["completed_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                j["exit_code"] = res.exit_code
                j["recent_logs"] = output_str[-4000:]
                j["result_preview"] = cleaned_preview
                break
        save_sql_query_jobs(jobs)

    except Exception as ex:
        jobs = load_sql_query_jobs()
        for j in jobs:
            if j["query_id"] == query_id:
                j["status"] = "FAILED"
                j["completed_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                j["recent_logs"] = str(ex)
                j["result_preview"] = f"Execution Error: {ex}"
                break
        save_sql_query_jobs(jobs)

class QueryRequest(BaseModel):
    sql: str
    target_table: Optional[str] = None

@router.get("/jobs")
def get_jobs():
    """Returns persistent list of all queries and execution states."""
    return {"jobs": load_sql_query_jobs()}

@router.post("/execute")
def submit_query(req: QueryRequest):
    """Submits an async Spark SQL query and returns immediately with query_id."""
    if not req.sql or not req.sql.strip():
        raise HTTPException(status_code=400, detail="SQL query cannot be empty.")

    query_id = f"q_{int(time.time())}_{str(uuid.uuid4())[:6]}"
    new_job = {
        "query_id": query_id,
        "query_sql": req.sql,
        "status": "RUNNING",
        "submitted_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "completed_at": None,
        "exit_code": None,
        "recent_logs": "Processing query across distributed Spark cluster...",
        "result_preview": ""
    }

    jobs = load_sql_query_jobs()
    jobs.insert(0, new_job)
    save_sql_query_jobs(jobs)

    # Launch in background thread
    t = threading.Thread(target=execute_query_background, args=(query_id, req.sql), daemon=True)
    t.start()

    return {"status": "SUBMITTED", "query_id": query_id, "job": new_job}

@router.delete("/jobs/{query_id}")
def delete_job(query_id: str):
    """Removes a query record from history."""
    jobs = load_sql_query_jobs()
    updated = [j for j in jobs if j["query_id"] != query_id]
    save_sql_query_jobs(updated)
    return {"status": "DELETED", "query_id": query_id}
