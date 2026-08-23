"""
Data Ingestion API Router
Handles micro-batch dataset uploads, schema detection, type overrides, and dynamic partition registration into Delta Lake / Hive.
"""

import os
import json
import time
import uuid
import re
import threading
import docker
import pandas as pd
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import spark_tuning_manager

router = APIRouter(prefix="/api/ingestion", tags=["Data Ingestion"])

INGESTION_JOBS_FILE = "ingestion_jobs.json"

def load_ingestion_jobs():
    if os.path.exists(INGESTION_JOBS_FILE):
        try:
            with open(INGESTION_JOBS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_ingestion_jobs(jobs):
    with open(INGESTION_JOBS_FILE, "w") as f:
        json.dump(jobs, f, indent=2)

def update_job_record(job_id, **updates):
    jobs = load_ingestion_jobs()
    for j in jobs:
        if j.get("job_id") == job_id:
            j.update(updates)
            break
    save_ingestion_jobs(jobs)

def copy_data_to_container(container, file_bytes: bytes, dest_dir: str, filename: str):
    import io, tarfile
    tar_stream = io.BytesIO()
    with tarfile.open(fileobj=tar_stream, mode='w') as tar:
        tarinfo = tarfile.TarInfo(name=filename)
        tarinfo.size = len(file_bytes)
        tarinfo.mtime = time.time()
        tar.addfile(tarinfo, io.BytesIO(file_bytes))
    tar_stream.seek(0)
    container.put_archive(dest_dir, tar_stream.read())

def run_ingestion_job_thread(job_id: str, spark_script: str, script_filename: str, chosen_params: dict):
    try:
        client = docker.from_env()
        spark_cont = client.containers.get("spark")
        copy_data_to_container(spark_cont, spark_script.encode('utf-8'), "/tmp", script_filename)
        
        tuning_flags = spark_tuning_manager.build_spark_submit_conf_args(chosen_params)
        cmd = f"/opt/spark/bin/spark-submit {tuning_flags} /tmp/{script_filename}"

        update_job_record(job_id, status="RUNNING", progress_pct=15, current_batch_msg="Spark submit launched...")
        
        res = spark_cont.exec_run(cmd)
        output = res.output.decode('utf-8', errors='ignore')
        
        if res.exit_code == 0:
            update_job_record(
                job_id,
                status="COMPLETED",
                progress_pct=100,
                current_batch_msg="Dataset successfully ingested into Delta Lake.",
                last_updated=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                recent_logs=output[-1500:]
            )
        else:
            update_job_record(
                job_id,
                status="FAILED",
                progress_pct=100,
                current_batch_msg="Ingestion failed.",
                last_updated=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                recent_logs=output[-1500:]
            )
    except Exception as ex:
        update_job_record(
            job_id,
            status="FAILED",
            progress_pct=100,
            current_batch_msg=f"Error: {ex}",
            last_updated=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            recent_logs=str(ex)
        )

@router.get("/jobs")
def get_ingestion_jobs():
    """Returns list of all active and historical ingestion jobs."""
    return {"jobs": load_ingestion_jobs()}

@router.post("/preview-schema")
async def preview_schema(file: UploadFile = File(...)):
    """Reads head of uploaded CSV/Parquet file and returns detected schema and sample rows."""
    try:
        content = await file.read()
        filename = file.filename.lower()
        import io
        if filename.endswith(".parquet") or filename.endswith(".pq"):
            df = pd.read_parquet(io.BytesIO(content))
        else:
            df = pd.read_csv(io.BytesIO(content), nrows=100)

        schema = []
        for col in df.columns:
            dtype_str = str(df[col].dtype)
            suggested = "STRING"
            if "int" in dtype_str:
                suggested = "BIGINT"
            elif "float" in dtype_str or "double" in dtype_str:
                suggested = "DOUBLE"
            elif "bool" in dtype_str:
                suggested = "BOOLEAN"
            elif "datetime" in dtype_str:
                suggested = "TIMESTAMP"
            schema.append({
                "column": col,
                "detected_type": dtype_str,
                "suggested_sql_type": suggested,
                "sample": str(df[col].iloc[0]) if not df.empty else ""
            })

        return {
            "columns": list(df.columns),
            "schema": schema,
            "rows_count": len(df),
            "preview_data": df.head(10).to_dict(orient="records")
        }
    except Exception as ex:
        raise HTTPException(status_code=400, detail=f"Failed to parse file schema: {ex}")

@router.post("/submit")
async def submit_ingestion_job(
    file: UploadFile = File(...),
    target_database: str = Form("default"),
    target_table: str = Form("sales_ingested"),
    table_format: str = Form("delta"),
    write_mode: str = Form("append"),
    partition_cols: Optional[str] = Form("")
):
    """Submits a dataset file for chunked ingestion and metadata registration."""
    try:
        content = await file.read()
        filename = file.filename
        job_id = f"ingest_{int(time.time())}_{uuid.uuid4().hex[:6]}"

        # Copy data file to spark container
        client = docker.from_env()
        spark_cont = client.containers.get("spark")
        copy_data_to_container(spark_cont, content, "/tmp", filename)

        # Build PySpark Ingestion Script
        partition_expr = ""
        if partition_cols and partition_cols.strip():
            cols = [f'"{c.strip()}"' for c in partition_cols.split(",") if c.strip()]
            if cols:
                partition_expr = f".partitionBy({', '.join(cols)})"

        dest_path = f"s3a://warehouse/{target_database}.db/{target_table}"
        spark_script = f"""#!/usr/bin/env python3
from pyspark.sql import SparkSession

spark = SparkSession.builder \\
    .appName("Ingest_{job_id}") \\
    .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000") \\
    .config("spark.hadoop.fs.s3a.access.key", "minioadmin") \\
    .config("spark.hadoop.fs.s3a.secret.key", "minioadmin123") \\
    .config("spark.hadoop.fs.s3a.path.style.access", "true") \\
    .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false") \\
    .enableHiveSupport() \\
    .getOrCreate()

print("--> 🚀 [Batch 1/1] Reading /tmp/{filename}...")
df = spark.read.option("header", "true").option("inferSchema", "true").csv("/tmp/{filename}")

print(f"--> [Batch 1/1] Writing {{df.count()}} rows to {dest_path}...")
df.write.format("{table_format}").mode("{write_mode}"){partition_expr}.saveAsTable("{target_database}.{target_table}")

print("--> ✅ [Batch 1/1] Ingestion completed.")
spark.stop()
"""
        tuning_cfg = spark_tuning_manager.load_tuning_config()
        params = tuning_cfg.get("params", spark_tuning_manager.PROFILES.get("🟢 Light (Small Files / Interactive)"))

        # Save initial job record
        job_record = {
            "job_id": job_id,
            "target_database": target_database,
            "target_table": target_table,
            "format": table_format,
            "write_mode": write_mode,
            "partition_cols": partition_cols,
            "status": "QUEUED",
            "progress_pct": 5,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "current_batch_msg": "Job submitted to Spark worker..."
        }
        jobs = load_ingestion_jobs()
        jobs.insert(0, job_record)
        save_ingestion_jobs(jobs)

        # Spawn background execution thread
        t = threading.Thread(
            target=run_ingestion_job_thread,
            args=(job_id, spark_script, f"script_{job_id}.py", params),
            daemon=True
        )
        t.start()

        return {"status": "SUCCESS", "job_id": job_id, "message": "Ingestion job launched in background."}
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))
