"""
Data Ingestion API Router
Supports chunked multi-file ingestion from server datasets (e.g. /data/df_inv_3),
micro-batch uploads, schema detection, type overrides, dynamic partitioning, and S3A/HDFS destinations.
"""

import os
import json
import time
import uuid
import re
import glob
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

def run_chunked_ingestion_job_thread(
    job_id: str,
    spark_script: str,
    script_filename: str,
    chosen_params: dict,
    total_chunks: int = 1
):
    """Background worker thread executing Spark ingestion with streaming progress parsing."""
    try:
        client = docker.from_env()
        spark_cont = client.containers.get("spark")
        copy_data_to_container(spark_cont, spark_script.encode('utf-8'), "/tmp", script_filename)
        
        tuning_flags = spark_tuning_manager.build_spark_submit_conf_args(chosen_params)
        cmd = f"/opt/spark/bin/spark-submit {tuning_flags} /tmp/{script_filename}"

        update_job_record(job_id, status="RUNNING", progress_pct=10, current_batch_msg="Spark submit launched...")

        exec_stream = spark_cont.exec_run(cmd, stream=True)
        full_output_lines = []
        for stream_bytes in exec_stream.output:
            chunk_str = stream_bytes.decode('utf-8', errors='ignore')
            full_output_lines.append(chunk_str)
            for line in chunk_str.splitlines():
                if "--> 🚀 [Batch" in line:
                    clean_msg = line.replace('--> ', '').strip()
                    match = re.search(r'\[Batch (\d+)/(\d+)\]', line)
                    curr_b = int(match.group(1)) if match else 1
                    max_b = int(match.group(2)) if match else total_chunks
                    update_job_record(
                        job_id,
                        current_chunk=curr_b,
                        current_batch_msg=clean_msg,
                        progress_pct=min(10 + int((curr_b / max_b) * 85), 95),
                        last_updated=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        recent_logs="\n".join(full_output_lines[-40:])
                    )
                elif "--> ✅ [Batch" in line:
                    clean_msg = line.replace('--> ', '').strip()
                    update_job_record(
                        job_id,
                        last_committed_msg=clean_msg,
                        last_updated=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        recent_logs="\n".join(full_output_lines[-40:])
                    )

        output = "".join(full_output_lines)
        
        if "__RESULT_SUCCESS__" in output:
            row_count_res = "N/A"
            time_taken_res = "N/A"
            for line in output.splitlines():
                if "__RESULT_SUCCESS__" in line:
                    parts = line.split("|")
                    if len(parts) >= 3:
                        try:
                            row_count_res = f"{int(parts[1]):,}"
                        except Exception:
                            row_count_res = parts[1]
                        try:
                            time_taken_res = f"{float(parts[2]):.2f}s"
                        except Exception:
                            time_taken_res = f"{parts[2]}s"

            update_job_record(
                job_id,
                status="SUCCESS",
                finished_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                total_rows=row_count_res,
                elapsed_seconds=time_taken_res,
                progress_pct=100,
                current_batch_msg=f"Ingestion complete ({row_count_res} rows in {time_taken_res})",
                recent_logs="\n".join(full_output_lines[-50:])
            )
        else:
            err_snip = output[-2000:] if len(output) > 2000 else output
            update_job_record(
                job_id,
                status="FAILED",
                finished_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                error_msg=err_snip,
                current_batch_msg="Ingestion failed. Check logs.",
                progress_pct=100,
                recent_logs="\n".join(full_output_lines[-50:])
            )
    except Exception as ex:
        update_job_record(
            job_id,
            status="FAILED",
            finished_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            error_msg=str(ex),
            current_batch_msg=f"Error: {ex}",
            progress_pct=100
        )

@router.get("/jobs")
def get_ingestion_jobs():
    """Returns list of all active and historical ingestion jobs, automatically reconciling stale jobs."""
    jobs = load_ingestion_jobs()
    
    try:
        client = docker.from_env()
        spark_cont = client.containers.get("spark")
        res = spark_cont.exec_run("ps aux")
        ps_output = res.output.decode('utf-8', errors='ignore') if res.exit_code == 0 else ""
        
        dirty = False
        for j in jobs:
            if j.get("status") in ["RUNNING", "QUEUED"]:
                job_id = j.get("job_id", "")
                script_pattern = f"script_{job_id}"
                if script_pattern not in ps_output:
                    j["status"] = "INTERRUPTED"
                    j["current_batch_msg"] = "Process terminated or container restarted."
                    j["finished_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    dirty = True
        if dirty:
            save_ingestion_jobs(jobs)
    except Exception:
        pass

    return {"jobs": jobs}

@router.post("/jobs/{job_id}/cancel")
def cancel_ingestion_job(job_id: str):
    """Cancels a running ingestion job and terminates any active Spark process."""
    try:
        client = docker.from_env()
        spark_cont = client.containers.get("spark")
        spark_cont.exec_run(f"pkill -f script_{job_id}")
    except Exception:
        pass

    update_job_status(
        job_id,
        status="CANCELLED",
        finished_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        current_batch_msg="Ingestion job cancelled by user.",
        progress_pct=100
    )
    return {"status": "SUCCESS", "message": f"Job {job_id} cancelled."}

@router.delete("/jobs/clear-completed")
def clear_completed_ingestion_jobs():
    """Removes all finished, failed, cancelled, and interrupted jobs from history."""
    jobs = load_ingestion_jobs()
    jobs = [j for j in jobs if j.get("status") in ["RUNNING", "QUEUED"]]
    save_ingestion_jobs(jobs)
    return {"status": "SUCCESS", "message": "Cleared non-running jobs."}

@router.delete("/jobs/{job_id}")
def delete_ingestion_job(job_id: str):
    """Deletes a job record from history."""
    jobs = load_ingestion_jobs()
    jobs = [j for j in jobs if j.get("job_id") != job_id]
    save_ingestion_jobs(jobs)
    return {"status": "SUCCESS", "message": f"Job {job_id} deleted."}

def resolve_data_dir():
    for candidate in ["/data", "/workspace/data", "/home/satish/Docker_Applications/docker_data_2/spark_delta_hive_metastore/data", "data"]:
        if os.path.exists(candidate) and os.path.isdir(candidate):
            return candidate
    return "/data"

@router.get("/server-datasets")
def list_server_datasets():
    """Lists pre-staged datasets available in /data directory."""
    data_dir = resolve_data_dir()
    datasets = []
    if os.path.exists(data_dir):
        for item in os.listdir(data_dir):
            item_path = os.path.join(data_dir, item)
            if os.path.isdir(item_path) and not item.startswith("."):
                files = [f for f in os.listdir(item_path) if not f.startswith(".")]
                parquet_files = [f for f in files if f.endswith(".parquet") or f.endswith(".pq")]
                total_bytes = sum(os.path.getsize(os.path.join(item_path, f)) for f in files if os.path.isfile(os.path.join(item_path, f)))
                mb = round(total_bytes / (1024 * 1024), 2)
                datasets.append({
                    "name": item,
                    "container_path": f"/data/{item}",
                    "file_count": len(files),
                    "parquet_count": len(parquet_files),
                    "size_mb": mb,
                    "is_parquet": len(parquet_files) > 0
                })
    return {"datasets": datasets}

@router.get("/dataset-columns/{dataset_name}")
def get_dataset_columns(dataset_name: str):
    """Inspects a sample file from a pre-staged server dataset and returns column names."""
    data_dir = resolve_data_dir()
    ds_path = os.path.join(data_dir, dataset_name)
    if not os.path.exists(ds_path):
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    files = [f for f in os.listdir(ds_path) if not f.startswith(".") and not f.startswith("_")]
    if not files:
        return {"columns": []}
    
    sample_file = os.path.join(ds_path, files[0])
    columns = []
    try:
        if sample_file.endswith(".parquet") or sample_file.endswith(".pq") or "parquet" in sample_file:
            import pyarrow.parquet as pq
            schema = pq.read_schema(sample_file)
            columns = schema.names
        elif sample_file.endswith(".json") or sample_file.endswith(".jsonl"):
            df = pd.read_json(sample_file, lines=True, nrows=5)
            columns = list(df.columns)
        else:
            df = pd.read_csv(sample_file, nrows=5)
            columns = list(df.columns)
    except Exception:
        pass
    
    return {"columns": columns}

class ServerDatasetIngestRequest(BaseModel):
    dataset_name: str
    target_database: str = "default"
    target_table: str = "inventory_ingested"
    table_format: str = "delta" # "delta" or "parquet"
    write_mode: str = "overwrite" # "overwrite" or "append"
    dest_storage: str = "s3" # "s3" or "hdfs"
    chunk_size: int = 100
    partition_cols: Optional[str] = ""

@router.post("/submit-server-dataset")
def submit_server_dataset_ingestion(req: ServerDatasetIngestRequest):
    """Initiates high-throughput chunked ingestion for pre-staged datasets in /data/."""
    job_id = f"ingest_{req.target_table}_{int(time.time())}_{uuid.uuid4().hex[:4]}"
    
    data_dir = resolve_data_dir()
    dataset_fs_path = os.path.join(data_dir, req.dataset_name)
    
    if not os.path.exists(dataset_fs_path):
        raise HTTPException(status_code=404, detail=f"Dataset folder '{req.dataset_name}' not found in /data.")
    
    files = sorted([
        f"/data/{req.dataset_name}/{f}"
        for f in os.listdir(dataset_fs_path)
        if not f.startswith(".") and not f.startswith("_") and (f.endswith(".parquet") or f.endswith(".csv") or f.endswith(".json"))
    ])
    
    if not files:
        raise HTTPException(status_code=400, detail="No readable Parquet/CSV/JSON files found in dataset folder.")
    
    total_files = len(files)
    chunk_size = max(10, req.chunk_size)
    total_batches = (total_files + chunk_size - 1) // chunk_size

    is_s3 = req.dest_storage == "s3"
    dest_path = f"s3a://warehouse/{req.target_table}/" if is_s3 else f"hdfs://namenode:9000/user/hive/warehouse/{req.target_table}/"
    is_delta = req.table_format == "delta"

    part_cols_list = [f'"{c.strip()}"' for c in (req.partition_cols or "").split(",") if c.strip()]
    partition_expr = f".partitionBy({', '.join(part_cols_list)})" if part_cols_list else ""

    spark_script = f"""#!/usr/bin/env python3
import time
import re
import json
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

spark = SparkSession.builder \\
    .appName("Ingest_{req.target_table}") \\
    .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000") \\
    .config("spark.hadoop.fs.s3a.access.key", "minioadmin") \\
    .config("spark.hadoop.fs.s3a.secret.key", "minioadmin123") \\
    .config("spark.hadoop.fs.s3a.path.style.access", "true") \\
    .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false") \\
    .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \\
    .config("spark.hadoop.fs.s3a.aws.credentials.provider", "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider") \\
    .enableHiveSupport() \\
    .getOrCreate()

t0 = time.time()
source_paths = {json.dumps(files)}
total_files = len(source_paths)
CHUNK_SIZE = {chunk_size}
total_batches = (total_files + CHUNK_SIZE - 1) // CHUNK_SIZE if total_files > 0 else 1
total_rows_ingested = 0

for batch_idx in range(total_batches):
    batch_files = source_paths[batch_idx * CHUNK_SIZE : (batch_idx + 1) * CHUNK_SIZE]
    batch_files = [f"file://{{f}}" if not f.startswith("file://") and not f.startswith("hdfs://") and not f.startswith("s3a://") else f for f in batch_files]
    print(f"\\n--> 🚀 [Batch {{batch_idx+1}}/{{total_batches}}] Reading {{len(batch_files)}} files (Files {{batch_idx*CHUNK_SIZE+1}} to {{min((batch_idx+1)*CHUNK_SIZE, total_files)}})...")
    
    if batch_files[0].endswith(".parquet") or "parquet" in batch_files[0]:
        df_batch = spark.read.parquet(*batch_files)
    elif batch_files[0].endswith(".json"):
        df_batch = spark.read.json(batch_files)
    else:
        df_batch = spark.read.option("header", "true").option("inferSchema", "true").csv(batch_files)

    cleaned_cols = []
    for c in df_batch.columns:
        clean_c = re.sub(r'[^a-zA-Z0-9_]', '_', c.strip()).lower()
        clean_c = re.sub(r'_+', '_', clean_c).strip('_')
        if clean_c and clean_c[0].isdigit():
            clean_c = f"col_{{clean_c}}"
        cleaned_cols.append(clean_c if clean_c else "unnamed_col")
    
    seen = {{}}
    deduped = []
    for c in cleaned_cols:
        if c in seen:
            seen[c] += 1
            deduped.append(f"{{c}}_{{seen[c]}}")
        else:
            seen[c] = 0
            deduped.append(c)

    df_batch = df_batch.toDF(*deduped)

    df_batch = df_batch.coalesce(4)
    batch_row_count = df_batch.count()
    total_rows_ingested += batch_row_count

    mode_to_use = "{req.write_mode}" if batch_idx == 0 else "append"

    if {is_delta}:
        writer = df_batch.write.format("delta").mode(mode_to_use){partition_expr}
        if "{dest_path}".startswith("s3a://") or "{dest_path}".startswith("hdfs://"):
            writer.option("path", "{dest_path}")
        writer.saveAsTable("{req.target_database}.{req.target_table}")
    else:
        writer = df_batch.write.format("parquet").mode(mode_to_use){partition_expr}
        if "{dest_path}".startswith("s3a://") or "{dest_path}".startswith("hdfs://"):
            writer.option("path", "{dest_path}")
        writer.saveAsTable("{req.target_database}.{req.target_table}")

    print(f"--> ✅ [Batch {{batch_idx+1}}/{{total_batches}}] Finished committing {{batch_row_count:,}} rows (Cumulative: {{total_rows_ingested:,}} rows)")

elapsed = time.time() - t0
print(f"\\n🏆 Ingestion Complete: {{total_rows_ingested:,}} total rows across {{total_files}} files in {{elapsed:.2f}}s")
print(f"__RESULT_SUCCESS__|{{total_rows_ingested}}|{{elapsed:.2f}}")
spark.stop()
"""
    tuning_cfg = spark_tuning_manager.load_tuning_config()
    params = dict(tuning_cfg.get("params", spark_tuning_manager.PROFILES.get("🔴 Heavy (Large Big Data / >10M Rows)")))
    params["driver_memory"] = "4g"
    params["executor_memory"] = "4g"

    job_record = {
        "job_id": job_id,
        "target_database": req.target_database,
        "target_table": req.target_table,
        "format": req.table_format,
        "write_mode": req.write_mode,
        "dest_storage": req.dest_storage,
        "total_source_files": total_files,
        "total_chunks": total_batches,
        "current_chunk": 0,
        "partition_cols": req.partition_cols,
        "status": "QUEUED",
        "progress_pct": 5,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "current_batch_msg": f"Queued {total_files} files in {total_batches} batches..."
    }
    jobs = load_ingestion_jobs()
    jobs.insert(0, job_record)
    save_ingestion_jobs(jobs)

    t = threading.Thread(
        target=run_chunked_ingestion_job_thread,
        args=(job_id, spark_script, f"script_{job_id}.py", params, total_batches),
        daemon=True
    )
    t.start()

    return {"status": "SUCCESS", "job_id": job_id, "total_files": total_files, "total_batches": total_batches}

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
    dest_storage: str = Form("s3"),
    partition_cols: Optional[str] = Form("")
):
    """Submits an uploaded dataset file for chunked ingestion and metadata registration."""
    try:
        content = await file.read()
        filename = file.filename
        job_id = f"ingest_{target_table}_{int(time.time())}_{uuid.uuid4().hex[:4]}"

        client = docker.from_env()
        spark_cont = client.containers.get("spark")
        copy_data_to_container(spark_cont, content, "/tmp", filename)

        part_cols_list = [f'"{c.strip()}"' for c in (partition_cols or "").split(",") if c.strip()]
        partition_expr = f".partitionBy({', '.join(part_cols_list)})" if part_cols_list else ""

        is_s3 = dest_storage == "s3"
        dest_path = f"s3a://warehouse/{target_table}/" if is_s3 else f"hdfs://namenode:9000/user/hive/warehouse/{target_table}/"
        is_delta = table_format == "delta"

        # Determine reader code based on file format extension
        fn_lower = filename.lower()
        if fn_lower.endswith(".parquet") or fn_lower.endswith(".pq") or "parquet" in fn_lower:
            reader_code = f'spark.read.parquet("file:///tmp/{filename}")'
        elif fn_lower.endswith(".json") or fn_lower.endswith(".jsonl"):
            reader_code = f'spark.read.json("file:///tmp/{filename}")'
        else:
            reader_code = f'spark.read.option("header", "true").option("inferSchema", "true").csv("file:///tmp/{filename}")'

        spark_script = f"""#!/usr/bin/env python3
import time
import re
from pyspark.sql import SparkSession

spark = SparkSession.builder \\
    .appName("Ingest_{job_id}") \\
    .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000") \\
    .config("spark.hadoop.fs.s3a.access.key", "minioadmin") \\
    .config("spark.hadoop.fs.s3a.secret.key", "minioadmin123") \\
    .config("spark.hadoop.fs.s3a.path.style.access", "true") \\
    .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false") \\
    .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \\
    .config("spark.hadoop.fs.s3a.aws.credentials.provider", "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider") \\
    .enableHiveSupport() \\
    .getOrCreate()

t0 = time.time()
print("--> 🚀 [Batch 1/1] Reading /tmp/{filename}...")
df = {reader_code}

cleaned_cols = []
for c in df.columns:
    clean_c = re.sub(r'[^a-zA-Z0-9_]', '_', c.strip()).lower()
    clean_c = re.sub(r'_+', '_', clean_c).strip('_')
    if clean_c and clean_c[0].isdigit():
        clean_c = f"col_{{clean_c}}"
    cleaned_cols.append(clean_c if clean_c else "unnamed_col")

seen = {{}}
deduped = []
for c in cleaned_cols:
    if c in seen:
        seen[c] += 1
        deduped.append(f"{{c}}_{{seen[c]}}")
    else:
        seen[c] = 0
        deduped.append(c)

df = df.toDF(*deduped).coalesce(4)

row_count = df.count()
print(f"--> Ingesting {{row_count:,}} rows into '{target_database}.{target_table}' ({table_format})...")

if {is_delta}:
    writer = df.write.format("delta").mode("{write_mode}"){partition_expr}
    if "{dest_path}".startswith("s3a://") or "{dest_path}".startswith("hdfs://"):
        writer.option("path", "{dest_path}")
    writer.saveAsTable("{target_database}.{target_table}")
else:
    writer = df.write.format("parquet").mode("{write_mode}"){partition_expr}
    if "{dest_path}".startswith("s3a://") or "{dest_path}".startswith("hdfs://"):
        writer.option("path", "{dest_path}")
    writer.saveAsTable("{target_database}.{target_table}")

elapsed = time.time() - t0
print(f"--> ✅ [Batch 1/1] Finished committing {{row_count:,}} rows.")
print(f"\\n🏆 Ingestion Complete: {{row_count:,}} total rows in {{elapsed:.2f}}s")
print(f"__RESULT_SUCCESS__|{{row_count}}|{{elapsed:.2f}}")
spark.stop()
"""
        tuning_cfg = spark_tuning_manager.load_tuning_config()
        params = tuning_cfg.get("params", spark_tuning_manager.PROFILES.get("🟢 Light (Small Files / Interactive)"))

        job_record = {
            "job_id": job_id,
            "target_database": target_database,
            "target_table": target_table,
            "format": table_format,
            "write_mode": write_mode,
            "dest_storage": dest_storage,
            "total_source_files": 1,
            "total_chunks": 1,
            "current_chunk": 0,
            "partition_cols": partition_cols,
            "status": "QUEUED",
            "progress_pct": 5,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "current_batch_msg": "Job submitted to Spark cluster..."
        }
        jobs = load_ingestion_jobs()
        jobs.insert(0, job_record)
        save_ingestion_jobs(jobs)

        t = threading.Thread(
            target=run_chunked_ingestion_job_thread,
            args=(job_id, spark_script, f"script_{job_id}.py", params, 1),
            daemon=True
        )
        t.start()

        return {"status": "SUCCESS", "job_id": job_id, "message": "Ingestion job launched in background."}
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))
