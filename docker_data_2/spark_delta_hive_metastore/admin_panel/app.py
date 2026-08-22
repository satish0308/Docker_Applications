import streamlit as st
import docker
import pandas as pd
import subprocess
import urllib.request
import json
import gc
import os
import re
import time
import io
import tarfile
import tempfile
import psycopg2
import pyarrow.parquet as pq
import spark_tuning_manager
import ui_components
import threading
import uuid
from datetime import datetime

# Configure Streamlit Page
st.set_page_config(
    page_title="BDP Platform Studio v2 • Cloud-Native Data Engine",
    layout="wide",
    page_icon="⚡",
    initial_sidebar_state="expanded"
)

# Inject Modern Glassmorphic Design System
ui_components.inject_v2_theme()

# Connect to Docker Daemon
try:
    client = docker.from_env()
except Exception as e:
    st.error(f"Failed to connect to Docker daemon: {e}")
    st.stop()

# -------------------------------------------------------------
# Persistent Ingestion Jobs Registry (Survives Hard Refresh)
# -------------------------------------------------------------
INGESTION_JOBS_FILE = "/app/ingestion_jobs.json"

def load_ingestion_jobs():
    """Loads persistent ingestion jobs registry from disk."""
    if os.path.exists(INGESTION_JOBS_FILE):
        try:
            with open(INGESTION_JOBS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return []

def save_ingestion_jobs(jobs):
    """Saves persistent ingestion jobs registry to disk."""
    try:
        with open(INGESTION_JOBS_FILE, "w") as f:
            json.dump(jobs, f, indent=2)
    except Exception:
        pass

def update_job_record(job_id, **updates):
    """Atomically updates fields of a specific job record."""
    jobs = load_ingestion_jobs()
    for j in jobs:
        if j.get("job_id") == job_id:
            j.update(updates)
            break
    save_ingestion_jobs(jobs)

def run_ingestion_job_thread(job_id, spark_script, script_filename, chosen_ingest_params, dest_path, target_db, target_table, total_chunks, total_source_files, is_s3, selected_partitions):
    """Background worker thread executing Spark ingestion with persistent progress streaming."""
    try:
        client_local = docker.from_env()
        spark_cont = client_local.containers.get("spark")
        copy_data_to_container(spark_cont, spark_script.encode('utf-8'), "/tmp", script_filename)
        
        tuning_flags = spark_tuning_manager.build_spark_submit_conf_args(chosen_ingest_params)
        
        exec_stream = spark_cont.exec_run(
            f"/opt/spark/bin/spark-submit {tuning_flags} /tmp/{script_filename}",
            stream=True
        )
        
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
                recent_logs="\n".join(full_output_lines[-50:])
            )
        else:
            err_snip = output[-2000:] if len(output) > 2000 else output
            update_job_record(
                job_id,
                status="FAILED",
                finished_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                error_msg=err_snip,
                progress_pct=100,
                recent_logs="\n".join(full_output_lines[-50:])
            )
    except Exception as ex:
        update_job_record(
            job_id,
            status="FAILED",
            finished_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            error_msg=str(ex),
            progress_pct=100
        )

# -------------------------------------------------------------
# Persistent SQL Query Jobs Registry (Survives Hard Refresh)
# -------------------------------------------------------------
SQL_QUERY_JOBS_FILE = "/app/sql_query_jobs.json"
QUERY_RESULTS_DIR = "/app/query_results"

def load_sql_query_jobs():
    """Loads persistent SQL query jobs registry from disk."""
    if os.path.exists(SQL_QUERY_JOBS_FILE):
        try:
            with open(SQL_QUERY_JOBS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return []

def save_sql_query_jobs(jobs):
    """Saves persistent SQL query jobs registry to disk."""
    try:
        os.makedirs(os.path.dirname(os.path.abspath(SQL_QUERY_JOBS_FILE)), exist_ok=True)
        with open(SQL_QUERY_JOBS_FILE, "w") as f:
            json.dump(jobs, f, indent=2)
    except Exception:
        pass

def update_sql_query_record(query_id, **updates):
    """Atomically updates fields of a specific SQL query job record."""
    jobs = load_sql_query_jobs()
    for j in jobs:
        if j.get("query_id") == query_id:
            j.update(updates)
            break
    save_sql_query_jobs(jobs)

def run_async_sql_query_thread(query_id, sql_query, tuning_profile_name, chosen_tuning_params, max_rows=1000):
    """Background worker thread executing Spark SQL query asynchronously with persistent result caching."""
    try:
        os.makedirs(QUERY_RESULTS_DIR, exist_ok=True)
        client_local = docker.from_env()
        spark_cont = client_local.containers.get("spark")
        
        # Escape triple quotes in SQL query
        escaped_sql = sql_query.replace('"""', '\\"\\"\\"')
        
        script_content = f'''import json
import time
import os
from pyspark.sql import SparkSession

start_t = time.time()
spark = SparkSession.builder \\
    .appName("PersistentSQL_{query_id}") \\
    .enableHiveSupport() \\
    .getOrCreate()

result_payload = {{"status": "pending", "query_id": "{query_id}"}}

try:
    print("--> 🚀 [Spark Engine] Executing SQL Query across cluster...")
    df = spark.sql("""{escaped_sql}""")
    
    schema_info = [{{"name": f.name, "type": str(f.dataType)}} for f in df.schema.fields]
    if len(schema_info) > 0:
        row_count = df.count()
        limited_df = df.limit({max_rows})
        records_json = limited_df.toJSON().collect()
        records = [json.loads(r) for r in records_json]
    else:
        row_count = 0
        records = []
    
    elapsed = time.time() - start_t
    print(f"--> ✅ [Spark Engine] Query completed! Total Rows: {{row_count}}, Returned: {{len(records)}}, Time: {{elapsed:.2f}}s")
    
    result_payload = {{
        "status": "success",
        "query_id": "{query_id}",
        "sql_query": """{escaped_sql}""",
        "total_rows": row_count,
        "returned_rows": len(records),
        "elapsed_sec": round(elapsed, 2),
        "schema": schema_info,
        "records": records
    }}
except Exception as e:
    elapsed = time.time() - start_t
    print(f"--> ❌ [Spark Engine] Query Error: {{str(e)}}")
    result_payload = {{
        "status": "error",
        "query_id": "{query_id}",
        "error": str(e),
        "elapsed_sec": round(elapsed, 2)
    }}
finally:
    try:
        with open("/tmp/result_{query_id}.json", "w") as f:
            json.dump(result_payload, f)
    except Exception:
        pass
    spark.stop()
'''
        script_filename = f"sql_run_{query_id}.py"
        copy_data_to_container(spark_cont, script_content.encode('utf-8'), "/tmp", script_filename)
        
        tuning_flags = spark_tuning_manager.build_spark_submit_conf_args(chosen_tuning_params)
        
        exec_stream = spark_cont.exec_run(
            f"/opt/spark/bin/spark-submit {tuning_flags} /tmp/{script_filename}",
            stream=True
        )
        
        full_output_lines = []
        for stream_bytes in exec_stream.output:
            chunk_str = stream_bytes.decode('utf-8', errors='ignore')
            full_output_lines.append(chunk_str)
            
        full_log_text = "".join(full_output_lines)
        
        # Read back result JSON from container
        result_file_host = os.path.join(QUERY_RESULTS_DIR, f"{query_id}.json")
        try:
            bits, stat = spark_cont.get_archive(f"/tmp/result_{query_id}.json")
            tar_bytes = b"".join(bits)
            tar = tarfile.open(fileobj=io.BytesIO(tar_bytes))
            f_member = tar.extractfile(tar.getmembers()[0])
            result_json_str = f_member.read().decode('utf-8')
            res_dict = json.loads(result_json_str)
            
            with open(result_file_host, "w") as f:
                f.write(result_json_str)
                
            if res_dict.get("status") == "success":
                update_sql_query_record(
                    query_id,
                    status="SUCCESS",
                    finished_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    total_rows=f"{res_dict.get('total_rows', 0):,}",
                    elapsed_seconds=f"{res_dict.get('elapsed_sec', 0)}s",
                    result_file=result_file_host,
                    recent_logs=full_log_text[-3000:]
                )
            else:
                update_sql_query_record(
                    query_id,
                    status="FAILED",
                    finished_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    error_msg=res_dict.get("error", "Unknown error"),
                    elapsed_seconds=f"{res_dict.get('elapsed_sec', 0)}s",
                    recent_logs=full_log_text[-3000:]
                )
        except Exception as e_res:
            err_details = str(e_res)
            if "Could not find the file" in err_details and full_log_text:
                error_lines = [l for l in full_log_text.splitlines() if "Exception:" in l or "Error:" in l or "Caused by:" in l or "ERROR" in l]
                if error_lines:
                    err_details = "\n".join(error_lines[-5:])
            update_sql_query_record(
                query_id,
                status="FAILED",
                finished_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                error_msg=f"Query Execution Interrupted / Error: {err_details}",
                recent_logs=full_log_text[-3000:]
            )
            
        spark_cont.exec_run(f"rm -f /tmp/{script_filename} /tmp/result_{query_id}.json")
        
    except Exception as ex:
        update_sql_query_record(
            query_id,
            status="FAILED",
            finished_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            error_msg=str(ex)
        )

def _livy_auto_cleaner_worker():
    """Background daemon periodically pruning idle or dead Livy sessions to protect cluster memory."""
    while True:
        try:
            req = urllib.request.Request("http://livy:8998/sessions", headers={"User-Agent": "LivyAutoPruner/1.0"})
            with urllib.request.urlopen(req, timeout=4) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                for s in data.get("sessions", []):
                    sid = s["id"]
                    state = s.get("state")
                    if state in ["dead", "error", "killed", "shutting_down"]:
                        del_req = urllib.request.Request(f"http://livy:8998/sessions/{sid}", method="DELETE")
                        urllib.request.urlopen(del_req, timeout=3)
        except Exception:
            pass
        time.sleep(60)

# Start background Livy session auto-pruner once
if "livy_auto_pruner_active" not in st.session_state:
    st.session_state["livy_auto_pruner_active"] = True
    t_cleaner = threading.Thread(target=_livy_auto_cleaner_worker, daemon=True)
    t_cleaner.start()

# Helper Functions
def copy_data_to_container(container, file_bytes, dest_dir, filename):
    """Copies in-memory bytes directly to any container path using Docker API."""
    tar_stream = io.BytesIO()
    with tarfile.TarFile(fileobj=tar_stream, mode='w') as tar:
        tarinfo = tarfile.TarInfo(name=filename)
        tarinfo.size = len(file_bytes)
        tar.addfile(tarinfo, io.BytesIO(file_bytes))
    tar_stream.seek(0)
    container.put_archive(dest_dir, tar_stream.read())

def sanitize_table_name(name):
    name = re.sub(r'[^a-zA-Z0-9_]', '_', str(name).lower())
    name = re.sub(r'_+', '_', name).strip('_')
    if name and name[0].isdigit():
        name = f"tbl_{name}"
    return name if name else "new_table"

def sanitize_column_name(col_name):
    clean = re.sub(r'[^a-zA-Z0-9_]', '_', str(col_name).strip()).lower()
    clean = re.sub(r'_+', '_', clean).strip('_')
    if clean and clean[0].isdigit():
        clean = f"col_{clean}"
    return clean if clean else "unnamed_col"

def get_hive_metastore_tables():
    """Fetches real-time registered tables from PostgreSQL Hive Metastore."""
    try:
        conn = psycopg2.connect(
            host="postgres",
            port=5432,
            dbname="metastore",
            user="hiveuser",
            password="hivepassword",
            connect_timeout=3
        )
        cursor = conn.cursor()
        query = """
            SELECT 
                d."NAME" AS db_name,
                t."TBL_NAME" AS table_name,
                t."TBL_TYPE" AS table_type,
                s."LOCATION" AS storage_location,
                to_timestamp(t."CREATE_TIME") AS created_at
            FROM "TBLS" t
            JOIN "DBS" d ON t."DB_ID" = d."DB_ID"
            LEFT JOIN "SDS" s ON t."SD_ID" = s."SD_ID"
            ORDER BY t."CREATE_TIME" DESC;
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        
        tables = []
        for r in rows:
            loc = str(r[3]) if r[3] else ""
            is_delta = "delta" in loc.lower() or "tbl_type" in str(r[2]).lower()
            tables.append({
                "Database": r[0],
                "Table Name": r[1],
                "Table Type": r[2],
                "Format": "Delta Lake" if is_delta else "Parquet / External",
                "Storage Location": loc,
                "Created At": str(r[4]) if r[4] else "N/A"
            })
        return pd.DataFrame(tables)
    except Exception:
        return pd.DataFrame()

def execute_spark_sql(sql_query, app_name="UI_Spark_Query"):
    """Executes a SparkSQL command in the Spark cluster and returns (output_text, exit_code)."""
    spark_cont = client.containers.get("spark")
    script = f"""
from pyspark.sql import SparkSession
spark = SparkSession.builder \\
    .appName("{app_name}") \\
    .config("spark.driver.memory", "2g") \\
    .config("spark.executor.memory", "3g") \\
    .enableHiveSupport() \\
    .getOrCreate()

try:
    df = spark.sql(\"\"\"{sql_query}\"\"\")
    df.show(50, truncate=False)
except Exception as e:
    print(f"__ERROR__|{{e}}")
spark.stop()
"""
    script_fname = f"/tmp/query_{int(time.time())}.py"
    copy_data_to_container(spark_cont, script.encode('utf-8'), "/tmp", os.path.basename(script_fname))
    res = spark_cont.exec_run(f"/opt/spark/bin/spark-submit {script_fname}")
    spark_cont.exec_run(f"rm -f {script_fname}")
    return res.output.decode('utf-8', errors='ignore'), res.exit_code

def fetch_table_inspector_data(table_name, limit=50, custom_sql=None):
    """Fetches structured columns, types, metrics, and sample records via Spark JSON serialization."""
    spark_cont = client.containers.get("spark")
    sql_to_run = custom_sql if custom_sql else f"SELECT * FROM {table_name} LIMIT {limit}"
    
    script = f"""
import json
import time
from pyspark.sql import SparkSession

spark = SparkSession.builder \\
    .appName("Inspector_{sanitize_table_name(table_name)}") \\
    .config("spark.driver.memory", "2g") \\
    .config("spark.executor.memory", "3g") \\
    .enableHiveSupport() \\
    .getOrCreate()

t0 = time.time()
try:
    df_full = spark.table("{table_name}")
    fields = []
    for idx, f in enumerate(df_full.schema.fields):
        fields.append({{
            "Index": idx + 1,
            "Column Name": f.name,
            "Data Type": f.dataType.simpleString().upper(),
            "Nullable": "YES" if f.nullable else "NO"
        }})
    
    # Run query
    df_sample = spark.sql(\"\"\"{sql_to_run}\"\"\")
    sample_records = [row.asDict(recursive=True) for row in df_sample.collect()]
    
    # Fast row count or full count
    total_count = df_full.count()
    elapsed = time.time() - t0

    result = {{
        "status": "success",
        "schema": fields,
        "records": sample_records,
        "total_rows": total_count,
        "columns_count": len(fields),
        "elapsed_sec": round(elapsed, 2)
    }}
    print("__JSON_RES_START__" + json.dumps(result, default=str) + "__JSON_RES_END__")
except Exception as ex:
    print("__JSON_RES_START__" + json.dumps({{"status": "error", "error": str(ex)}}) + "__JSON_RES_END__")
spark.stop()
"""
    sf = f"/tmp/insp_{int(time.time())}.py"
    copy_data_to_container(spark_cont, script.encode('utf-8'), "/tmp", os.path.basename(sf))
    res = spark_cont.exec_run(f"/opt/spark/bin/spark-submit {sf}")
    spark_cont.exec_run(f"rm -f {sf}")
    out = res.output.decode('utf-8', errors='ignore')
    if "__JSON_RES_START__" in out:
        jstr = out.split("__JSON_RES_START__")[1].split("__JSON_RES_END__")[0]
        return json.loads(jstr)
    return {"status": "error", "error": out}

def get_service_health(container):
    if container.status != 'running':
        return "❌ Down"
    state = container.attrs.get('State', {})
    health = state.get('Health', {})
    if health:
        status = health.get('Status')
        if status == 'healthy':
            return "✅ Healthy"
        elif status == 'starting':
            return "⏳ Starting"
        elif status == 'unhealthy':
            return "❌ Unhealthy"
    return "🟢 Running"

def get_container_stats():
    containers = client.containers.list(all=True)
    data = []
    for c in containers:
        labels = c.labels or {}
        project = labels.get("com.docker.compose.project", "")
        if project == "spark_delta_hive_metastore" or c.name in [
            "namenode", "datanode", "hive-server", "hue", "spark", "spark-worker",
            "resourcemanager", "nodemanager", "minio", "jupyter-notebook", "livy",
            "admin-panel", "hive-metastore-postgres", "pgadmin", "keycloak", "spark-thriftserver"
        ]:
            health = get_service_health(c)
            data.append({
                "Container Name": c.name,
                "Status": c.status.upper(),
                "Health State": health,
                "Container ID": c.short_id
            })
    return pd.DataFrame(data)

def purge_hanging_state_and_memory():
    logs = []
    # 1. Clear Livy Sessions
    try:
        req = urllib.request.urlopen("http://livy:8998/sessions", timeout=4)
        data = json.loads(req.read().decode('utf-8'))
        sessions = data.get("sessions", [])
        cleared_livy = 0
        for s in sessions:
            sid = s["id"]
            del_req = urllib.request.Request(f"http://livy:8998/sessions/{sid}", method="DELETE")
            urllib.request.urlopen(del_req, timeout=4)
            cleared_livy += 1
        logs.append(f"✅ Cleared {cleared_livy} hanging/abandoned Livy sessions.")
    except Exception as ex:
        logs.append(f"ℹ️ Livy Session Check: {ex}")

    # 2. Terminate Idle PostgreSQL Connections
    try:
        pg_container = client.containers.get("hive-metastore-postgres")
        sql_cmd = (
            "psql -U hiveuser -d metastore -c "
            "\"SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            "WHERE state = 'idle' AND state_change < NOW() - INTERVAL '2 minutes' AND pid <> pg_backend_pid();\""
        )
        pg_container.exec_run(f"sh -c '{sql_cmd}'")
        logs.append("✅ Terminated idle PostgreSQL database connections.")
    except Exception as ex:
        logs.append(f"ℹ️ PostgreSQL Cleanup: {ex}")

    # 3. Ensure HDFS Out of SafeMode and Self-Heal Missing Blocks
    try:
        nn_container = client.containers.get("namenode")
        res = nn_container.exec_run("hdfs dfsadmin -safemode leave")
        out = res.output.decode('utf-8').strip()
        logs.append(f"✅ HDFS SafeMode Status: {out}")
        
        # Self-heal orphaned/missing blocks
        fsck_res = nn_container.exec_run("hdfs fsck / -delete", environment={"HADOOP_USER_NAME": "hdfs"})
        logs.append("✅ HDFS Filesystem Health Checked & Missing/Orphaned Blocks Self-Healed.")
    except Exception as ex:
        logs.append(f"ℹ️ HDFS Check: {ex}")

    # 4. Trigger Admin Panel Garbage Collector
    collected = gc.collect()
    logs.append(f"✅ Python Garbage Collection completed ({collected} objects freed).")
    return logs

# Load / Save Scheduled Jobs Registry
SCHEDULED_JOBS_FILE = "/app/scheduled_jobs.json"

def load_scheduled_jobs():
    if os.path.exists(SCHEDULED_JOBS_FILE):
        try:
            with open(SCHEDULED_JOBS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_scheduled_jobs(jobs):
    try:
        with open(SCHEDULED_JOBS_FILE, "w") as f:
            json.dump(jobs, f, indent=2)
    except Exception as e:
        st.error(f"Failed to save jobs: {e}")

# Backup & Restore Helper Functions
BACKUP_DIR = "/backups"

def list_local_backups():
    backups = []
    if not os.path.exists(BACKUP_DIR):
        try:
            os.makedirs(BACKUP_DIR, exist_ok=True)
        except Exception:
            pass
        return backups
    for item in sorted(os.listdir(BACKUP_DIR), reverse=True):
        bpath = os.path.join(BACKUP_DIR, item)
        mpath = os.path.join(bpath, "backup_manifest.json")
        if os.path.isdir(bpath) and os.path.exists(mpath):
            try:
                with open(mpath, "r") as f:
                    data = json.load(f)
                    backups.append(data)
            except Exception:
                pass
    return backups

def execute_backup_job(mode="table", db_name="default", table_name=None, custom_id=None):
    spark_cont = client.containers.get("spark")
    with open("python_scripts/backup_restore_table.py", "rb") as f:
        copy_data_to_container(spark_cont, f.read(), "/opt/spark", "backup_restore_table.py")
    if mode == "database":
        cmd = f"/opt/spark/bin/spark-submit /opt/spark/backup_restore_table.py backup-db --database {db_name}"
    else:
        cmd = f"/opt/spark/bin/spark-submit /opt/spark/backup_restore_table.py backup --table {db_name}.{table_name}"
    if custom_id:
        cmd += f" --backup-id {custom_id}"
    res = spark_cont.exec_run(cmd)
    return res.output.decode('utf-8', errors='ignore'), res.exit_code

def execute_restore_job(backup_id, mode="table", target_db="default", target_table=None, storage_dest="s3a://warehouse/"):
    spark_cont = client.containers.get("spark")
    with open("python_scripts/backup_restore_table.py", "rb") as f:
        copy_data_to_container(spark_cont, f.read(), "/opt/spark", "backup_restore_table.py")
    if mode == "database":
        cmd = f"/opt/spark/bin/spark-submit /opt/spark/backup_restore_table.py restore-db --backup-id {backup_id} --database {target_db} --storage-dest {storage_dest}"
    else:
        cmd = f"/opt/spark/bin/spark-submit /opt/spark/backup_restore_table.py restore --backup-id {backup_id} --target-table {target_table if target_table else ''} --storage-dest {storage_dest}"
    res = spark_cont.exec_run(cmd)
    return res.output.decode('utf-8', errors='ignore'), res.exit_code

# -------------------------------------------------------------
# DYNAMIC CLUSTER HEALTH PROBE & EXECUTIVE TOP HEADER
# -------------------------------------------------------------
ESSENTIAL_CONTAINERS = [
    "namenode", "datanode", "hive-server", "spark", "spark-worker",
    "resourcemanager", "nodemanager", "minio", "livy",
    "hive-metastore-postgres", "keycloak", "spark-thriftserver"
]

all_containers_live = client.containers.list(all=True)
down_services_list = []

for svc_name in ESSENTIAL_CONTAINERS:
    matching = [c for c in all_containers_live if svc_name in c.name]
    if not matching:
        down_services_list.append(svc_name)
    else:
        for c in matching:
            if c.status != "running":
                down_services_list.append(c.name)
            else:
                health_stat = c.attrs.get('State', {}).get('Health', {}).get('Status')
                if health_stat in ['unhealthy', 'dead']:
                    down_services_list.append(f"{c.name} (unhealthy)")

is_cluster_healthy = (len(down_services_list) == 0)

ui_components.render_top_header(is_healthy=is_cluster_healthy, down_services=down_services_list)
ui_components.render_portal_shortcuts()

# Fetch Cluster Telemetry for Hero Stats
metrics = spark_tuning_manager.get_spark_master_metrics()
df_tables_all = get_hive_metastore_tables()
total_tables_count = len(df_tables_all) if not df_tables_all.empty else 0
all_p_jobs = load_ingestion_jobs()
all_q_jobs = load_sql_query_jobs()
active_workloads = len([j for j in all_p_jobs if j.get("status") == "RUNNING"]) + len([q for q in all_q_jobs if q.get("status") == "RUNNING"])

ui_components.render_hero_stats(
    active_workers=metrics.get('alive_workers', 2),
    total_cores=metrics.get('total_cores', 12),
    total_memory=f"{metrics.get('total_memory_mb', 20480) / 1024:.1f} GB",
    tables_count=total_tables_count,
    active_jobs=active_workloads
)

# -------------------------------------------------------------
# SIDEBAR NAVIGATION (Modern Categorized Hub)
# -------------------------------------------------------------
ui_components.render_html("""
<div style="padding: 10px 0 16px 0; border-bottom: 1px solid rgba(255,255,255,0.08); margin-bottom: 15px;">
    <div style="font-size: 1.15rem; font-weight: 800; color: #ffffff; letter-spacing: -0.02em;">⚡ BDP Control Center</div>
    <div style="font-size: 0.78rem; color: #cbd5e1; font-weight: 600;">Version 2.0 • Enterprise Edition</div>
</div>
""")

nav_section = st.sidebar.selectbox(
    "Select Suite:",
    [
        "🚀 DATA OPS & INGESTION",
        "⚡ COMPUTE & SQL STUDIO",
        "📦 STORAGE & METASTORE",
        "📊 SYSTEM OBSERVABILITY"
    ],
    index=0
)

if nav_section == "🚀 DATA OPS & INGESTION":
    menu = st.sidebar.radio(
        "Module Selection",
        [
            "📥 Data Ingestion & Partitioning",
            "⏰ Scheduled Ingestion Jobs",
            "⏳ Delta Time-Travel & Maintenance"
        ]
    )
elif nav_section == "⚡ COMPUTE & SQL STUDIO":
    menu = st.sidebar.radio(
        "Module Selection",
        [
            "⚡ Persistent SQL Studio & Tracer",
            "⚙️ Spark Tuning & Cluster Scaling",
            "🔍 Cluster Diagnostics"
        ]
    )
elif nav_section == "📦 STORAGE & METASTORE":
    menu = st.sidebar.radio(
        "Module Selection",
        [
            "🗄️ Metastore Table Explorer",
            "📦 Table Backup & Restore"
        ]
    )
else:
    menu = st.sidebar.radio(
        "Module Selection",
        [
            "📊 Cluster Health & Links",
            "📜 Container Logs Viewer",
            "🧹 One-Click Cleanup",
            "📚 Platform Docs & Guide Center"
        ]
    )

# Active Tuning Profile Pill in Sidebar
current_cfg = spark_tuning_manager.load_tuning_config()
active_prof_disp = current_cfg.get("active_profile", "Heavy")
st.sidebar.markdown("---")
ui_components.render_html(f"""
<div class="glass-card-sm" style="background: rgba(99, 102, 241, 0.15); border: 1px solid rgba(99, 102, 241, 0.35);">
    <div style="font-size: 0.75rem; text-transform: uppercase; color: #a5b4fc; font-weight: 700;">Active Tuning Profile</div>
    <div style="font-size: 1.05rem; font-weight: 800; color: #ffffff; margin-top: 2px;">{active_prof_disp.split(' ')[0]}</div>
    <div style="font-size: 0.80rem; color: #e2e8f0; margin-top: 4px;">Dynamic Allocation: <b style="color: #38bdf8;">{'Enabled' if current_cfg.get('params', {}).get('dynamic_allocation', True) else 'Disabled (Monolithic)'}</b></div>
</div>
""")


# =============================================================
# MODULE 1: DATA INGESTION & PARTITIONING
# =============================================================
if menu == "📥 Data Ingestion & Partitioning":
    ui_components.render_html("""
    <div class="glass-card">
        <h2 style="margin: 0; font-weight: 800; font-size: 1.4rem; color: #ffffff;">📥 Data Ingestion, Dynamic Partitioning & Table Registration</h2>
        <p style="margin: 6px 0 0 0; color: #cbd5e1; font-size: 0.90rem;">
            Ingest large datasets (up to 1,000 GB), auto-detect schemas, override column data types, configure dynamic partition keys, 
            and register high-speed <b>Delta Lake / Parquet tables</b> directly into <b>Hue & Hive Metastore</b>.
        </p>
    </div>
    """)

    # Ingestion Status & Job Tracker
    all_persistent_jobs = load_ingestion_jobs()
    active_jobs = [j for j in all_persistent_jobs if j.get("status") == "RUNNING"]
    
    if active_jobs:
        curr_j = active_jobs[0]
        ui_components.render_html(f"""
        <div class="glass-card" style="border-left: 4px solid #6366f1;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <div class="badge-info">Active Ingestion In Progress</div>
                    <h3 style="margin: 6px 0; font-size: 1.15rem; color: #ffffff;">Target: <code>{curr_j.get('target_db')}.{curr_j.get('target_table')}</code></h3>
                    <p style="margin: 0; color: #cbd5e1; font-size: 0.84rem;">{curr_j.get('current_batch_msg', 'Processing micro-batches in Spark cluster...')}</p>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 1.3rem; font-weight: 800; color: #38bdf8; font-family: monospace;">Chunk {curr_j.get('current_chunk', 1)} / {curr_j.get('total_chunks', 1)}</div>
                    <div style="font-size: 0.78rem; color: #94a3b8;">Started: {curr_j.get('started_at')}</div>
                </div>
            </div>
        </div>
        """)
        st.progress(curr_j.get('progress_pct', 10))
        
        col_act_a, col_act_b = st.columns([1, 4])
        with col_act_a:
            if st.button("🔄 Refresh Ingestion Progress", use_container_width=True):
                st.rerun()
        with col_act_b:
            with st.expander("📜 Live Background Cluster Logs (Tail 40 lines)", expanded=False):
                st.code(curr_j.get("recent_logs", "Awaiting cluster output..."), language="text")

    elif all_persistent_jobs and all_persistent_jobs[0].get("status") == "SUCCESS":
        last_succ = all_persistent_jobs[0]
        with st.expander(f"🎉 Latest Successful Ingestion: `{last_succ.get('target_db')}.{last_succ.get('target_table')}`", expanded=False):
            col_s1, col_s2, col_s3, col_s4 = st.columns(4)
            col_s1.metric("Rows Ingested", f"{last_succ.get('total_rows', 'N/A')}")
            col_s2.metric("Processing Time", f"{last_succ.get('elapsed_seconds', 'N/A')}")
            col_s3.metric("Total Chunks", f"{last_succ.get('total_chunks', 1)} Chunks ({last_succ.get('total_source_files', 1)} files)")
            col_s4.metric("Storage Destination", "MinIO S3 Delta" if last_succ.get("is_s3") else "HDFS")
            st.link_button("🎨 Query Table in Hue Editor", "http://localhost:8888")

    if all_persistent_jobs:
        with st.expander("📜 Ingestion Audit & History Registry", expanded=False):
            history_rows = []
            for j in all_persistent_jobs[:15]:
                status_icon = "🟢 SUCCESS" if j.get("status") == "SUCCESS" else ("🔴 FAILED" if j.get("status") == "FAILED" else "🟡 RUNNING")
                history_rows.append({
                    "Started At": j.get("started_at"),
                    "Target Table": f"{j.get('target_db')}.{j.get('target_table')}",
                    "Status": status_icon,
                    "Rows Ingested": j.get("total_rows", "N/A"),
                    "Duration": j.get("elapsed_seconds", "N/A"),
                    "Chunks": f"{j.get('total_chunks', 1)} Chunks ({j.get('total_source_files', 1)} files)",
                    "Storage": "MinIO S3" if j.get("is_s3") else "HDFS"
                })
            st.dataframe(pd.DataFrame(history_rows), use_container_width=True, hide_index=True)

    st.markdown('<div class="section-title">📂 1. Select Ingestion Source</div>', unsafe_allow_html=True)
    source_type = st.radio(
        "Source Method:",
        [
            "📁 Multi-File Browser Upload (Drag & Drop CSV / Parquet / JSON up to 1000GB)",
            "🐘 Direct Path Ingestion (Host File / Windows Mount / HDFS Path / Wildcards)"
        ],
        horizontal=True
    )

    uploaded_files = []
    input_file_paths = []
    file_format = "csv"
    df_preview = None
    base_table_name = "new_table"

    if "Multi-File Browser Upload" in source_type:
        uploaded_files = st.file_uploader(
            "Drop your data files here:",
            type=["csv", "parquet", "pq", "json", "tsv", "txt"],
            accept_multiple_files=True,
            help="Files up to 1,000 GB each are supported."
        )

        if uploaded_files:
            st.markdown(f'<div class="badge-success">📁 {len(uploaded_files)} file(s) selected</div>', unsafe_allow_html=True)
            preview_file = uploaded_files[0]
            if len(uploaded_files) > 1:
                file_names = [f.name for f in uploaded_files]
                selected_preview_name = st.selectbox("Select file to preview schema:", file_names)
                preview_file = next(f for f in uploaded_files if f.name == selected_preview_name)
            
            base_table_name = sanitize_table_name(os.path.splitext(uploaded_files[0].name)[0])
            
            preview_file.seek(0)
            data_bytes = preview_file.read()
            preview_file.seek(0)

            ext_suffix = os.path.splitext(preview_file.name)[1]
            tmp_f = tempfile.NamedTemporaryFile(delete=False, suffix=ext_suffix)
            tmp_f.write(data_bytes)
            tmp_f.flush()
            tmp_f.close()
            tmp_path = tmp_f.name

            try:
                if preview_file.name.lower().endswith(('.parquet', '.pq')) or data_bytes.startswith(b'PAR1'):
                    file_format = "parquet"
                    try:
                        tbl = pq.read_table(tmp_path)
                        df_preview = tbl.to_pandas().head(50)
                    except Exception:
                        df_preview = pd.read_parquet(tmp_path).head(50)
                elif preview_file.name.lower().endswith('.json') or data_bytes.strip().startswith((b'{', b'[')):
                    file_format = "json"
                    try:
                        df_preview = pd.read_json(tmp_path, lines=True, nrows=50)
                    except Exception:
                        df_preview = pd.read_json(tmp_path, nrows=50)
                else:
                    file_format = "csv"
                    try:
                        if preview_file.name.lower().endswith(('.tsv', '.tab')):
                            df_preview = pd.read_csv(tmp_path, sep='\t', nrows=50)
                        else:
                            df_preview = pd.read_csv(tmp_path, nrows=50)
                    except Exception:
                        df_preview = pd.read_csv(tmp_path, sep=None, engine='python', nrows=50)
            finally:
                if os.path.exists(tmp_path):
                    try:
                        os.unlink(tmp_path)
                    except Exception:
                        pass
    else:
        st.info("💡 **Direct Path Mode**: Ingest large files (5GB, 20GB, 50GB+) directly from your local `./data` folder or HDFS without browser upload overhead.")
        local_data_files = []
        if os.path.exists("/data"):
            try:
                for root, dirs, files in os.walk("/data"):
                    for f in files:
                        if not f.startswith(".") and f != "README.md":
                            local_data_files.append(os.path.join(root, f))
            except Exception:
                pass

        default_path = "hdfs://namenode:9000/data/benchmark/sales_train_evaluation.csv"
        if local_data_files:
            col_sel1, col_sel2 = st.columns([3, 1])
            with col_sel1:
                selected_data_file = st.selectbox("Quick-Select local data file:", ["-- Custom / HDFS Path --"] + local_data_files)
            if selected_data_file != "-- Custom / HDFS Path --":
                default_path = selected_data_file

        path_input = st.text_input(
            "Host Path, Local `./data` Path, or HDFS Wildcard:",
            value=default_path,
            help="Example: /data/sales.csv or hdfs://namenode:9000/data/raw/*.csv"
        )
        if path_input:
            input_file_path = path_input.strip()
            if input_file_path.startswith("data/"):
                input_file_path = "/" + input_file_path
            
            if re.match(r'^[a-zA-Z]:\\', input_file_path):
                drive_letter = input_file_path[0].lower()
                rel_path = input_file_path[2:].replace('\\', '/')
                input_file_path = f"/mnt/{drive_letter}{rel_path}"
            
            input_file_paths = [input_file_path]
            base_filename = os.path.basename(input_file_path.rstrip('/').replace('*', ''))
            base_table_name = sanitize_table_name(os.path.splitext(base_filename)[0])
            
            preview_sample_path = input_file_path
            if os.path.isdir(input_file_path):
                valid_files = [f for f in os.listdir(input_file_path) if not f.startswith('.') and ':Zone.Identifier' not in f and f != '_SUCCESS']
                if any(f.endswith(('.parquet', '.pq')) for f in valid_files):
                    file_format = "parquet"
                    parquet_samples = [f for f in valid_files if f.endswith(('.parquet', '.pq'))]
                    if parquet_samples:
                        preview_sample_path = os.path.join(input_file_path, parquet_samples[0])
                elif any(f.endswith('.json') for f in valid_files):
                    file_format = "json"
                    json_samples = [f for f in valid_files if f.endswith('.json')]
                    if json_samples:
                        preview_sample_path = os.path.join(input_file_path, json_samples[0])
                else:
                    file_format = "csv"
                    csv_samples = [f for f in valid_files if f.endswith(('.csv', '.tsv', '.txt'))]
                    if csv_samples:
                        preview_sample_path = os.path.join(input_file_path, csv_samples[0])
            else:
                if input_file_path.endswith((".parquet", ".pq")):
                    file_format = "parquet"
                elif input_file_path.endswith(".json"):
                    file_format = "json"
                else:
                    file_format = "csv"

            if os.path.exists(preview_sample_path) and os.path.isfile(preview_sample_path):
                try:
                    if file_format == "parquet":
                        df_preview = pd.read_parquet(preview_sample_path).head(50)
                    elif file_format == "json":
                        df_preview = pd.read_json(preview_sample_path, lines=True, nrows=50)
                    else:
                        df_preview = pd.read_csv(preview_sample_path, nrows=50)
                except Exception:
                    pass

    # Schema Preview & Overrides
    type_overrides = {}
    detected_cols = []
    if df_preview is not None:
        st.markdown('<div class="section-title">🔍 2. Schema Discovery & Column Overrides</div>', unsafe_allow_html=True)
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Columns Detected", len(df_preview.columns))
        col_m2.metric("Sample Rows Loaded", len(df_preview))
        col_m3.metric("Detected File Format", file_format.upper())
        
        st.dataframe(df_preview.head(15), use_container_width=True, hide_index=True)
        detected_cols = [sanitize_column_name(c) for c in df_preview.columns]

        with st.expander("🛠️ Custom Column Data Type Overrides (Optional)", expanded=False):
            available_types = ["Auto (Inferred)", "STRING", "INT", "BIGINT", "DOUBLE", "FLOAT", "DECIMAL(18,2)", "BOOLEAN", "DATE", "TIMESTAMP"]
            cols_per_row = 3
            col_list = list(df_preview.columns)
            for i in range(0, len(col_list), cols_per_row):
                grid_cols = st.columns(cols_per_row)
                for j in range(cols_per_row):
                    if i + j < len(col_list):
                        cname = col_list[i + j]
                        s_name = sanitize_column_name(cname)
                        inferred_type = str(df_preview[cname].dtype)
                        with grid_cols[j]:
                            selected_t = st.selectbox(f"`{cname}` ({inferred_type}):", available_types, key=f"type_override_{cname}", index=0)
                            if selected_t != "Auto (Inferred)":
                                type_overrides[s_name] = selected_t

    # Destination & Partitioning
    st.markdown('<div class="section-title">⚙️ 3. Target Table & Partitioning Configuration</div>', unsafe_allow_html=True)
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        target_db = st.text_input("Target Hive Database", value="default")
        target_table = st.text_input("Target Table Name", value=base_table_name)
        target_table = sanitize_table_name(target_table)
    
    with col_c2:
        output_format = st.selectbox(
            "Target Storage Format",
            ["Delta Lake (ACID, Time-Travel & Z-Order)", "Parquet (Universal - Recommended for Hive & Hue)", "CSV Text"],
            index=0
        )
        storage_dest = st.selectbox(
            "Storage Destination",
            ["MinIO S3 Bucket (s3a://warehouse/)", "HDFS (hdfs://namenode:9000/user/hive/warehouse/)"],
            index=0
        )

    selected_partitions = []
    if detected_cols:
        selected_partitions = st.multiselect(
            "🗂️ Select Dynamic Partition Column(s):",
            options=detected_cols,
            help="Partitioning by columns like date, season, or store speeds up downstream queries by 10x-100x."
        )

    col_w1, col_w2 = st.columns(2)
    with col_w1:
        write_mode = st.radio("Write Mode", ["Overwrite (Replace existing table)", "Append (Add to existing data)"], horizontal=True)
    with col_w2:
        multi_file_strategy = "Single Table" if len(uploaded_files) <= 1 else st.radio("Multi-File Strategy", ["Merge All into Single Table (Union)", "Create Separate Table per File"], horizontal=True)

    # Execution Tuning
    total_est_bytes = sum(f.size for f in uploaded_files) if uploaded_files else 100 * 1024 * 1024
    rec_prof_name, rec_mb = spark_tuning_manager.recommend_profile_for_filesize(total_est_bytes)
    
    with st.expander(f"⚡ Spark Execution Sizing & Compute Tuning (Recommended: {rec_prof_name})", expanded=True):
        col_sz1, col_sz2 = st.columns([1.5, 2])
        with col_sz1:
            profile_keys = list(spark_tuning_manager.PROFILES.keys()) + ["🛠️ Custom Engine Tuning"]
            default_idx = profile_keys.index(rec_prof_name) if rec_prof_name in profile_keys else 1
            selected_ingest_profile = st.selectbox("Select Execution Profile:", profile_keys, index=default_idx, key="ingest_sizing_profile")
        with col_sz2:
            if selected_ingest_profile != "🛠️ Custom Engine Tuning":
                p_meta = spark_tuning_manager.PROFILES[selected_ingest_profile]
                st.markdown(f"**Driver**: `{p_meta['driver_memory']}` | **Executor**: `{p_meta['executor_memory']}` | **Cores**: `{p_meta['executor_cores']}` | **Shuffle Partitions**: `{p_meta['shuffle_partitions']}`")
            else:
                st.caption("Customized JVM parameters.")

        if selected_ingest_profile == "🛠️ Custom Engine Tuning":
            col_cust1, col_cust2, col_cust3, col_cust4 = st.columns(4)
            with col_cust1:
                c_driver_mem = st.selectbox("Driver Memory", ["1g", "2g", "4g", "8g", "16g"], index=1, key="c_drv_mem")
            with col_cust2:
                c_exec_mem = st.selectbox("Executor Memory", ["2g", "4g", "6g", "8g", "12g", "16g"], index=2, key="c_exe_mem")
            with col_cust3:
                c_exec_cores = st.number_input("Executor Cores", min_value=1, max_value=16, value=4, key="c_exe_cores")
            with col_cust4:
                c_shuffle_parts = st.number_input("Shuffle Partitions", min_value=1, max_value=800, value=200, key="c_shuf_parts")
            
            chosen_ingest_params = {
                "driver_memory": c_driver_mem,
                "executor_memory": c_exec_mem,
                "executor_cores": c_exec_cores,
                "max_cores": c_exec_cores * 2,
                "shuffle_partitions": c_shuffle_parts,
                "aqe_enabled": True,
                "aqe_coalesce": True,
                "memory_fraction": 0.75,
                "storage_fraction": 0.4
            }
        else:
            chosen_ingest_params = spark_tuning_manager.PROFILES[selected_ingest_profile]

    can_proceed = (len(uploaded_files) > 0) or (len(input_file_paths) > 0)
    if st.button("🚀 Start High-Speed Cluster Ingestion", type="primary", disabled=not can_proceed, use_container_width=True):
        try:
            namenode_cont = client.containers.get("namenode")
            namenode_cont.exec_run("hdfs dfs -mkdir -p /data/uploads")
            staged_source_paths = []

            if uploaded_files:
                for idx, ufile in enumerate(uploaded_files):
                    staging_hdfs_path = f"/data/uploads/{ufile.name}"
                    ufile.seek(0)
                    file_bytes = ufile.read()
                    copy_data_to_container(namenode_cont, file_bytes, "/tmp", ufile.name)
                    put_res = namenode_cont.exec_run(f"hdfs dfs -put -f /tmp/{ufile.name} {staging_hdfs_path}")
                    if put_res.exit_code != 0:
                        raise Exception("Failed to stage to HDFS")
                    namenode_cont.exec_run(f"rm -f /tmp/{ufile.name}")
                    staged_source_paths.append(f"hdfs://namenode:9000{staging_hdfs_path}")
            elif input_file_paths:
                for ipath in input_file_paths:
                    staged_source_paths.append(ipath)

            is_s3 = "MinIO" in storage_dest
            dest_path = f"s3a://warehouse/{target_table}/" if is_s3 else f"hdfs://namenode:9000/user/hive/warehouse/{target_table}/"
            save_mode = "overwrite" if "Overwrite" in write_mode else "append"
            is_delta = "Delta Lake" in output_format

            spark_script = f"""
import time
import re
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

spark = SparkSession.builder \\
    .appName("UI_Ingestion_{target_table}") \\
    .config("spark.driver.memory", "{chosen_ingest_params.get('driver_memory', '4g')}") \\
    .config("spark.executor.memory", "{chosen_ingest_params.get('executor_memory', '6g')}") \\
    .config("spark.executor.cores", "{chosen_ingest_params.get('executor_cores', 4)}") \\
    .config("spark.cores.max", "{chosen_ingest_params.get('max_cores', 12)}") \\
    .config("spark.sql.shuffle.partitions", "{chosen_ingest_params.get('shuffle_partitions', 200)}") \\
    .config("spark.sql.adaptive.enabled", "true") \\
    .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \\
    .enableHiveSupport() \\
    .getOrCreate()

t0 = time.time()
source_paths = {json.dumps(staged_source_paths)}
total_files = len(source_paths)
CHUNK_SIZE = 100
total_batches = (total_files + CHUNK_SIZE - 1) // CHUNK_SIZE if total_files > 0 else 1
total_rows_ingested = 0
type_overrides = {json.dumps(type_overrides)}
partitions = {json.dumps(selected_partitions)}

for batch_idx in range(total_batches):
    batch_files = source_paths[batch_idx * CHUNK_SIZE : (batch_idx + 1) * CHUNK_SIZE]
    batch_files = [f"file://{{f}}" if not f.startswith("file://") and not f.startswith("hdfs://") and not f.startswith("s3a://") else f for f in batch_files]
    print(f"\\n--> 🚀 [Batch {{batch_idx+1}}/{{total_batches}}] Reading {{len(batch_files)}} files...")
    
    if "{file_format}" == "parquet":
        df_batch = spark.read.parquet(*batch_files)
    elif "{file_format}" == "json":
        df_batch = spark.read.json(batch_files)
    else:
        df_batch = spark.read.option("header", "true").option("inferSchema", "true").csv(batch_files)

    for c in df_batch.columns:
        clean_c = re.sub(r'[^a-zA-Z0-9_]', '_', c.strip()).lower()
        clean_c = re.sub(r'_+', '_', clean_c).strip('_')
        if clean_c and clean_c[0].isdigit():
            clean_c = f"col_{{clean_c}}"
        clean_c = clean_c if clean_c else "unnamed_col"
        if clean_c != c:
            df_batch = df_batch.withColumnRenamed(c, clean_c)

    for col_name, target_type in type_overrides.items():
        if col_name in df_batch.columns:
            df_batch = df_batch.withColumn(col_name, F.col(col_name).cast(target_type))

    if batch_idx == 0 and "{save_mode}" == "overwrite":
        try:
            spark.sql("DROP TABLE IF EXISTS {target_db}.{target_table}")
        except Exception:
            pass

    current_mode = "{save_mode}" if batch_idx == 0 else "append"
    if partitions:
        df_batch = df_batch.repartition(*partitions)
    
    writer = df_batch.write.mode(current_mode).option("path", "{dest_path}")
    if partitions:
        writer = writer.partitionBy(*partitions)

    if {is_delta}:
        writer.format("delta").saveAsTable("{target_db}.{target_table}")
    else:
        writer.format("parquet").saveAsTable("{target_db}.{target_table}")

    batch_rows = df_batch.count()
    total_rows_ingested += batch_rows
    print(f"--> ✅ [Batch {{batch_idx+1}}/{{total_batches}}] Committed {{batch_rows:,}} rows (Total: {{total_rows_ingested:,}})")

if partitions and not {is_delta}:
    try:
        spark.sql("MSCK REPAIR TABLE {target_db}.{target_table}")
    except Exception:
        pass

elapsed = time.time() - t0
print(f"\\n🏆 Ingestion Complete: {{total_rows_ingested:,}} rows in {{elapsed:.2f}}s")
print(f"__RESULT_SUCCESS__|{{total_rows_ingested}}|{{elapsed:.2f}}")
spark.stop()
"""
            total_source_files = len(staged_source_paths)
            total_chunks = (total_source_files + 99) // 100 if total_source_files > 0 else 1
            job_id = f"job_{target_table}_{int(time.time())}"
            script_filename = f"ingest_{target_table}.py"

            new_job_record = {
                "job_id": job_id,
                "target_db": target_db,
                "target_table": target_table,
                "dest_path": dest_path,
                "is_s3": is_s3,
                "storage_format": output_format,
                "status": "RUNNING",
                "started_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "total_chunks": total_chunks,
                "current_chunk": 1,
                "current_batch_msg": f"Starting Spark cluster for {total_chunks} batches...",
                "total_source_files": total_source_files,
                "total_rows": "0",
                "elapsed_seconds": "0s",
                "progress_pct": 10,
                "recent_logs": "Initializing Spark cluster session..."
            }
            
            jobs = load_ingestion_jobs()
            jobs.insert(0, new_job_record)
            save_ingestion_jobs(jobs)

            threading.Thread(
                target=run_ingestion_job_thread,
                args=(job_id, spark_script, script_filename, chosen_ingest_params, dest_path, target_db, target_table, total_chunks, total_source_files, is_s3, selected_partitions),
                daemon=True
            ).start()

            st.success(f"🚀 Ingestion job `{job_id}` successfully started in background!")
            time.sleep(0.5)
            st.rerun()

        except Exception as ex:
            st.error(f"❌ Ingestion failed: {ex}")


# =============================================================
# MODULE 2: PERSISTENT SQL STUDIO & TRACER
# =============================================================
elif menu == "⚡ Persistent SQL Studio & Tracer":
    ui_components.render_html("""
    <div class="glass-card">
        <h2 style="margin: 0; font-weight: 800; font-size: 1.4rem; color: #ffffff;">⚡ Persistent Spark SQL Studio & Live DAG Tracer</h2>
        <p style="margin: 6px 0 0 0; color: #cbd5e1; font-size: 0.90rem;">
            Execute heavy analytical queries asynchronously across the distributed Spark cluster. 
            Queries run decoupled in the background and <b>survive browser hard-refreshes (<code>Ctrl+F5</code>), tab closures, and network drops</b>.
        </p>
    </div>
    """, unsafe_allow_html=True)

    all_sql_jobs = load_sql_query_jobs()
    running_sql_jobs = [j for j in all_sql_jobs if j.get("status") == "RUNNING"]

    if running_sql_jobs:
        st.markdown('<div class="section-title">🏃‍♂️ Active Queries In Flight</div>', unsafe_allow_html=True)
        for r_job in running_sql_jobs:
            q_id = r_job.get("query_id")
            ui_components.render_html(f"""
            <div class="glass-card" style="border-left: 4px solid #38bdf8;">
                <div style="display: flex; justify-content: space-between;">
                    <div>
                        <div class="badge-warning">RUNNING IN SPARK CLUSTER</div>
                        <h4 style="margin: 6px 0 2px 0; color: #ffffff;">Query ID: <code>{q_id}</code></h4>
                        <div style="font-size: 0.78rem; color: #94a3b8;">Submitted at {r_job.get('submitted_at')}</div>
                    </div>
                </div>
            </div>
            """)
            col_c1, col_c2 = st.columns([1, 4])
            with col_c1:
                if st.button("🔄 Check Live Status", key=f"ref_{q_id}"):
                    st.rerun()
            with col_c2:
                with st.expander("📜 Live DAG Scheduler Logs", expanded=False):
                    st.code(r_job.get("recent_logs", "Processing in Spark DAG Scheduler..."), language="bash")

    st.markdown('<div class="section-title">📝 SQL Query Studio</div>', unsafe_allow_html=True)
    
    # Pre-canned Quick Templates
    col_t1, col_t2, col_t3 = st.columns(3)
    with col_t1:
        if st.button("⚡ Broadcast Hash Join (Fastest)", use_container_width=True):
            st.session_state["sql_editor_val"] = (
                "CREATE TABLE inv_item_fast\n"
                "USING DELTA\n"
                "PARTITIONED BY (season)\n"
                "AS SELECT /*+ BROADCAST(t1) */\n"
                "    t2.*,\n"
                "    t1.genericmaterialcode,\n"
                "    t1.familycode,\n"
                "    t1.divisioncode,\n"
                "    t1.producttypecode\n"
                "FROM default.itemmaster t1\n"
                "JOIN default.df_inv_2 t2\n"
                "    ON t1.variantmaterialcode = t2.itemid\n"
                "   AND t1.seasonid = t2.seasonid;"
            )
    with col_t2:
        if st.button("📊 Inventory Summary by Season", use_container_width=True):
            st.session_state["sql_editor_val"] = (
                "SELECT season, COUNT(*) as total_records, SUM(stockuds) as total_units, ROUND(SUM(stockuds * stockcost), 2) as total_valuation\n"
                "FROM default.df_inv_2\n"
                "GROUP BY season\n"
                "ORDER BY total_valuation DESC\n"
                "LIMIT 25;"
            )
    with col_t3:
        if st.button("🔍 Explore Hive Catalog Tables", use_container_width=True):
            st.session_state["sql_editor_val"] = "SHOW TABLES IN default;"

    default_sql = st.session_state.get(
        "sql_editor_val",
        "SELECT * FROM default.inv_item_4 LIMIT 25;"
    )

    sql_input_text = st.text_area("SQL Statement (SparkSQL / HiveQL / Delta):", value=default_sql, height=140)

    col_q1, col_q2, col_q3 = st.columns(3)
    with col_q1:
        prof_keys = list(spark_tuning_manager.PROFILES.keys())
        sel_q_profile = st.selectbox("Compute Resource Profile:", prof_keys, index=1)
    with col_q2:
        sel_max_rows = st.number_input("Max Result Rows to Cache:", min_value=10, max_value=10000, value=500, step=100)
    with col_q3:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        btn_launch_query = st.button("🚀 Launch Persistent Async Query", type="primary", use_container_width=True)

    if btn_launch_query:
        if not sql_input_text.strip():
            st.error("Please provide a valid SQL statement.")
        else:
            try:
                new_q_id = f"query_{int(time.time())}_{uuid.uuid4().hex[:6]}"
                chosen_params = spark_tuning_manager.PROFILES[sel_q_profile]
                
                new_sql_record = {
                    "query_id": new_q_id,
                    "sql_query": sql_input_text.strip(),
                    "tuning_profile": sel_q_profile,
                    "submitted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "finished_at": "In Progress...",
                    "status": "RUNNING",
                    "total_rows": "Calculating...",
                    "elapsed_seconds": "0s",
                    "result_file": "",
                    "recent_logs": "Initializing Spark cluster session..."
                }
                
                jobs = load_sql_query_jobs()
                jobs.insert(0, new_sql_record)
                save_sql_query_jobs(jobs)

                threading.Thread(
                    target=run_async_sql_query_thread,
                    args=(new_q_id, sql_input_text.strip(), sel_q_profile, chosen_params, sel_max_rows),
                    daemon=True
                ).start()

                st.success(f"🎉 Query `{new_q_id}` launched in background! You can safely refresh the page.")
                time.sleep(0.5)
                st.rerun()
            except Exception as e_launch:
                st.error(f"Failed to launch query: {e_launch}")

    st.markdown('<div class="section-title">📚 Persistent Query History & Results Browser</div>', unsafe_allow_html=True)
    if all_sql_jobs:
        col_hist1, col_hist2 = st.columns([3, 1])
        with col_hist1:
            status_filter = st.selectbox("Filter History by Status:", ["All Queries", "🟢 SUCCESS", "🏃‍♂️ RUNNING", "🔴 FAILED"])
        with col_hist2:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            if st.button("🧹 Clear Finished Queries", use_container_width=True):
                keep_jobs = [j for j in all_sql_jobs if j.get("status") == "RUNNING"]
                save_sql_query_jobs(keep_jobs)
                st.rerun()

        filtered_jobs = all_sql_jobs
        if status_filter == "🟢 SUCCESS":
            filtered_jobs = [j for j in all_sql_jobs if j.get("status") == "SUCCESS"]
        elif status_filter == "🏃‍♂️ RUNNING":
            filtered_jobs = [j for j in all_sql_jobs if j.get("status") == "RUNNING"]
        elif status_filter == "🔴 FAILED":
            filtered_jobs = [j for j in all_sql_jobs if j.get("status") == "FAILED"]

        for job in filtered_jobs:
            j_id = job.get("query_id")
            j_status = job.get("status", "UNKNOWN")
            j_sql = job.get("sql_query", "")
            j_time = job.get("elapsed_seconds", "-")
            j_rows = job.get("total_rows", "-")
            j_finished = job.get("finished_at", "-")
            j_res_file = job.get("result_file", "")
            j_err = job.get("error_msg", "")
            badge = "🟢 SUCCESS" if j_status == "SUCCESS" else ("🏃‍♂️ RUNNING" if j_status == "RUNNING" else "🔴 FAILED")

            with st.expander(f"{badge} | `{j_id}` | Rows: **{j_rows}** | Time: **{j_time}** | Finished: {j_finished}", expanded=(j_status == "RUNNING")):
                st.code(j_sql, language="sql")
                
                col_k1, col_k2, col_k3 = st.columns(3)
                col_k1.metric("Status", j_status)
                col_k2.metric("Total Rows", str(j_rows))
                col_k3.metric("Elapsed Time", str(j_time))

                if j_status == "SUCCESS" and j_res_file and os.path.exists(j_res_file):
                    try:
                        with open(j_res_file, "r") as rf:
                            res_payload = json.load(rf)
                            records = res_payload.get("records", [])
                            schema = res_payload.get("schema", [])
                            
                            if records:
                                df_res = pd.DataFrame(records)
                                st.dataframe(df_res, use_container_width=True)
                                
                                col_d1, col_d2 = st.columns(2)
                                with col_d1:
                                    st.download_button("📥 Export to CSV", df_res.to_csv(index=False).encode('utf-8'), f"result_{j_id}.csv", "text/csv", key=f"dl_csv_{j_id}")
                                with col_d2:
                                    st.download_button("📥 Export to JSON", json.dumps(res_payload, indent=2), f"result_{j_id}.json", "application/json", key=f"dl_json_{j_id}")
                            else:
                                st.info("Query executed successfully but returned 0 rows.")

                            if schema:
                                with st.expander("📐 Result Schema & Data Types", expanded=False):
                                    st.dataframe(pd.DataFrame(schema), use_container_width=True, hide_index=True)
                    except Exception as e_read:
                        st.error(f"Error loading result cache: {e_read}")

                elif j_status == "FAILED":
                    st.error(f"❌ **Execution Error**: {j_err}")
                    with st.expander("📜 Full Error Traceback", expanded=False):
                        st.code(job.get("recent_logs", "No logs available."), language="bash")
    else:
        st.info("No queries have been executed yet.")


# =============================================================
# MODULE 3: SPARK TUNING & CLUSTER SCALING
# =============================================================
elif menu == "⚙️ Spark Tuning & Cluster Scaling":
    ui_components.render_html("""
    <div class="glass-card">
        <h2 style="margin: 0; font-weight: 800; font-size: 1.4rem; color: #ffffff;">⚙️ Spark Dynamic Tuning & Elastic Worker Node Scaling</h2>
        <p style="margin: 6px 0 0 0; color: #cbd5e1; font-size: 0.90rem;">
            Scale worker fleet horizontally on-demand, fine-tune JVM heap allocations, CPU cores, shuffle partition counts, 
            and Dynamic Resource Allocation (DRA) to guarantee zero-OOM execution across multi-billion-row workloads.
        </p>
    </div>
    """, unsafe_allow_html=True)

    t_tab_scaling, t_tab_profiles, t_tab_active_apps = st.tabs([
        "🖥️ Cluster Compute & Worker Scaling",
        "⚙️ Workload Sizing & Parameter Tuning",
        "📈 Active Applications & Master Telemetry"
    ])

    metrics = spark_tuning_manager.get_spark_master_metrics()

    with t_tab_scaling:
        st.markdown('<div class="section-title">🖥️ Real-Time Cluster Capacity</div>', unsafe_allow_html=True)
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        col_m1.metric("Active Worker Nodes", f"{metrics['alive_workers']} / {metrics['total_workers']}")
        col_m2.metric("Total CPU Cores", f"{metrics['total_cores']} Cores", f"{metrics['cores_free']} Free")
        col_m3.metric("Total Cluster RAM", f"{metrics['total_memory_mb'] / 1024:.1f} GB", f"{metrics['memory_free_mb'] / 1024:.1f} GB Free")
        col_m4.metric("Active Spark Apps", metrics['active_apps_count'])

        st.markdown('<div class="section-title">🚀 Horizontal Elastic Worker Fleet Management</div>', unsafe_allow_html=True)
        cur_cfg = spark_tuning_manager.load_tuning_config()
        saved_scale = cur_cfg.get("worker_scaling", {})
        live_workers = [w for w in metrics.get("worker_list", []) if "ALIVE" in w.get("State", "")]
        live_cores = int(live_workers[0].get("Cores", 6)) if live_workers else 6
        live_mem_mb = int(live_workers[0].get("Memory (MB)", 10240)) if live_workers else 10240
        live_ram = f"{live_mem_mb // 1024}g"

        default_target_scale = saved_scale.get("worker_count", max(1, metrics['alive_workers']))
        default_ram = saved_scale.get("worker_ram", live_ram)
        default_cores = saved_scale.get("worker_cores", live_cores)

        col_sc1, col_sc2 = st.columns([2, 1])
        with col_sc1:
            target_scale = st.slider("Target Worker Node Count:", 1, 8, int(default_target_scale) if 1 <= int(default_target_scale) <= 8 else max(1, metrics['alive_workers']))
            col_ns1, col_ns2 = st.columns(2)
            with col_ns1:
                worker_ram_options = ["2g", "4g", "6g", "8g", "10g", "12g", "16g", "20g", "24g", "32g"]
                sel_worker_ram = st.selectbox("RAM per Worker Node", worker_ram_options, index=worker_ram_options.index(default_ram) if default_ram in worker_ram_options else 4)
            with col_ns2:
                worker_core_options = [1, 2, 4, 6, 8, 12, 16]
                sel_worker_cores = st.selectbox("CPU Cores per Worker Node", worker_core_options, index=worker_core_options.index(default_cores) if default_cores in worker_core_options else 3)

            ram_int = int(re.sub(r'[^0-9]', '', sel_worker_ram))
            st.info(f"📊 Projected Cluster Capacity: **{target_scale * sel_worker_cores} Total Cores** & **{target_scale * ram_int} GB Total RAM** across **{target_scale} Worker(s)**")
        with col_sc2:
            st.write("")
            st.write("")
            st.write("")
            if st.button("🚀 Apply Worker Scale & Node Sizing", type="primary", key="btn_apply_scale", use_container_width=True):
                with st.spinner(f"Provisioning {target_scale} worker node(s)..."):
                    out, code = spark_tuning_manager.scale_cluster_workers(target_scale, sel_worker_ram, sel_worker_cores)
                    if code == 0:
                        st.success(f"🎉 {out}")
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error(f"❌ Failed to scale workers: {out}")

        st.markdown('<div class="section-title">📋 Active Registered Worker Fleet</div>', unsafe_allow_html=True)
        if metrics["worker_list"]:
            st.dataframe(pd.DataFrame(metrics["worker_list"]), use_container_width=True, hide_index=True)

    with t_tab_profiles:
        st.markdown('<div class="section-title">⚙️ Workload Sizing Presets & Engine Parameters</div>', unsafe_allow_html=True)
        current_config = spark_tuning_manager.load_tuning_config()
        active_prof_name = current_config.get("active_profile", "🟡 Medium (Standard ETL / Daily Batches)")
        active_params = current_config.get("params", {})
        profile_keys = list(spark_tuning_manager.PROFILES.keys()) + ["🛠️ Custom Engine Override"]
        default_index = profile_keys.index(active_prof_name) if active_prof_name in profile_keys else 1

        selected_prof = st.selectbox("Select Active Workload Profile:", profile_keys, index=default_index, key="tuning_prof_sel")

        if selected_prof in spark_tuning_manager.PROFILES:
            prof_data = spark_tuning_manager.PROFILES[selected_prof]
            st.info(f"📋 **Description**: {prof_data['description']}")
            source_dict = active_params if (selected_prof == active_prof_name and active_params) else prof_data
            drv_mem_val = source_dict.get("driver_memory", prof_data["driver_memory"])
            exe_mem_val = source_dict.get("executor_memory", prof_data["executor_memory"])
            exe_cores_val = source_dict.get("executor_cores", prof_data["executor_cores"])
            max_cores_val = source_dict.get("max_cores", prof_data["max_cores"])
            shuf_parts_val = source_dict.get("shuffle_partitions", prof_data["shuffle_partitions"])
            aqe_val = source_dict.get("aqe_enabled", prof_data["aqe_enabled"])
            aqe_coal_val = source_dict.get("aqe_coalesce", prof_data["aqe_coalesce"])
            mem_frac_val = source_dict.get("memory_fraction", prof_data["memory_fraction"])
            offheap_val = source_dict.get("offheap_enabled", prof_data["offheap_enabled"])
            offheap_sz_val = source_dict.get("offheap_size", prof_data["offheap_size"])
            kryo_val = source_dict.get("kryo_serializer", prof_data["kryo_serializer"])
            dra_val = source_dict.get("dynamic_allocation", True)
        else:
            st.info("🛠️ Custom Mode active.")
            drv_mem_val = active_params.get("driver_memory", "4g")
            exe_mem_val = active_params.get("executor_memory", "6g")
            exe_cores_val = active_params.get("executor_cores", 4)
            max_cores_val = active_params.get("max_cores", 12)
            shuf_parts_val = active_params.get("shuffle_partitions", 200)
            aqe_val = active_params.get("aqe_enabled", True)
            aqe_coal_val = active_params.get("aqe_coalesce", True)
            mem_frac_val = active_params.get("memory_fraction", 0.75)
            offheap_val = active_params.get("offheap_enabled", False)
            offheap_sz_val = active_params.get("offheap_size", "0")
            kryo_val = active_params.get("kryo_serializer", True)
            dra_val = active_params.get("dynamic_allocation", False)

        col_t1, col_t2 = st.columns(2)
        with col_t1:
            st.markdown("#### 🧠 JVM Memory Allocation")
            drv_options = ["1g", "2g", "3g", "4g", "6g", "8g", "12g", "16g"]
            in_drv_mem = st.selectbox("Driver Memory", drv_options, index=drv_options.index(drv_mem_val) if drv_mem_val in drv_options else 3)
            exe_options = ["2g", "3g", "4g", "5g", "6g", "7g", "8g", "10g", "12g", "16g"]
            in_exe_mem = st.selectbox("Executor Memory", exe_options, index=exe_options.index(exe_mem_val) if exe_mem_val in exe_options else 4)
            in_mem_frac = st.slider("Memory Fraction", 0.5, 0.95, float(mem_frac_val), 0.05)

        with col_t2:
            st.markdown("#### ⚡ CPU Cores & Parallelism")
            in_exe_cores = st.number_input("Cores Per Executor", 1, 16, int(exe_cores_val))
            in_max_cores = st.number_input("Max Global Cores", 1, 64, int(max_cores_val))
            in_shuf_parts = st.number_input("Shuffle Partitions", 2, 1000, int(shuf_parts_val), step=8)

        st.markdown("#### 🚀 Dynamic Allocation & Optimizations")
        col_o1, col_o2, col_o3 = st.columns(3)
        with col_o1:
            in_dra = st.checkbox("Enable Dynamic Resource Allocation (DRA)", value=bool(dra_val))
            in_aqe = st.checkbox("Enable Adaptive Query Execution (AQE)", value=bool(aqe_val))
        with col_o2:
            in_aqe_coal = st.checkbox("AQE Dynamic Partition Coalescing", value=bool(aqe_coal_val), disabled=not in_aqe)
            in_kryo = st.checkbox("Enable Kryo Fast Serialization", value=bool(kryo_val))
        with col_o3:
            in_offheap = st.checkbox("Enable Off-Heap Memory", value=bool(offheap_val))

        compiled_params = {
            "driver_memory": in_drv_mem,
            "executor_memory": in_exe_mem,
            "executor_cores": in_exe_cores,
            "max_cores": in_max_cores,
            "dynamic_allocation": in_dra,
            "shuffle_partitions": in_shuf_parts,
            "aqe_enabled": in_aqe,
            "aqe_coalesce": in_aqe_coal,
            "memory_fraction": in_mem_frac,
            "storage_fraction": 0.5,
            "offheap_enabled": in_offheap,
            "offheap_size": "1g" if in_offheap else "0",
            "kryo_serializer": in_kryo
        }

        generated_flags = spark_tuning_manager.build_spark_submit_conf_args(compiled_params)
        st.code(f"/opt/spark/bin/spark-submit {generated_flags} <job_script.py>", language="bash")

        if st.button("💾 Apply & Save Tuning Profile as Cluster Default", type="primary", key="btn_save_tuning", use_container_width=True):
            spark_tuning_manager.save_tuning_config({
                "active_profile": selected_prof,
                "params": compiled_params
            })
            st.success(f"🎉 Tuning profile successfully saved and applied to Spark Master, Livy, and Hue!")

    with t_tab_active_apps:
        st.markdown('<div class="section-title">📈 Live Master Telemetry</div>', unsafe_allow_html=True)
        active_apps = metrics.get("active_apps", [])
        if active_apps:
            apps_data = []
            for a in active_apps:
                apps_data.append({
                    "App ID": a.get("id"),
                    "Name": a.get("name"),
                    "User": a.get("user"),
                    "Cores": a.get("cores"),
                    "Memory / Slave": f"{a.get('memoryperslave')} MB",
                    "State": a.get("state"),
                    "Duration": f"{a.get('duration', 0) / 1000:.1f}s"
                })
            st.dataframe(pd.DataFrame(apps_data), use_container_width=True, hide_index=True)
        else:
            st.info("ℹ️ No applications currently running.")


# =============================================================
# MODULE 4: METASTORE TABLE EXPLORER
# =============================================================
elif menu == "🗄️ Metastore Table Explorer":
    ui_components.render_html("""
    <div class="glass-card">
        <h2 style="margin: 0; font-weight: 800; font-size: 1.4rem; color: #ffffff;">🗄️ Hive Metastore Catalog & Interactive Table Inspector</h2>
        <p style="margin: 6px 0 0 0; color: #cbd5e1; font-size: 0.90rem;">
            Browse databases, inspect schemas, query partition distributions, and load interactive data grids with instant CSV export.
        </p>
    </div>
    """, unsafe_allow_html=True)

    df_tables = get_hive_metastore_tables()
    if not df_tables.empty:
        st.dataframe(df_tables, use_container_width=True, hide_index=True)

        st.markdown('<div class="section-title">🔍 Interactive Table Inspector</div>', unsafe_allow_html=True)
        table_options = [f"{r['Database']}.{r['Table Name']}" for _, r in df_tables.iterrows()]
        selected_tbl = st.selectbox("Select Table to Inspect:", table_options)
        
        if selected_tbl:
            tbl_meta = df_tables[df_tables.apply(lambda r: f"{r['Database']}.{r['Table Name']}" == selected_tbl, axis=1)].iloc[0]
            col_m1, col_m2, col_m3 = st.columns(3)
            col_m1.metric("Table Identifier", selected_tbl)
            col_m2.metric("Storage Format", tbl_meta["Format"])
            col_m3.metric("Storage Location", tbl_meta["Storage Location"])

            insp_tab_grid, insp_tab_schema, insp_tab_sql = st.tabs([
                "📊 Interactive Data Grid",
                "📋 Visual Schema & Types",
                "⚡ Custom SQL Query Runner"
            ])

            with insp_tab_grid:
                col_row_opt1, col_row_opt2 = st.columns([1, 3])
                with col_row_opt1:
                    row_limit = st.selectbox("Rows Limit:", [10, 25, 50, 100, 250], index=1, key=f"limit_{selected_tbl}")
                with col_row_opt2:
                    st.write("")
                    fetch_clicked = st.button("🔄 Load Sample Records", type="primary", key=f"fetch_{selected_tbl}")

                if fetch_clicked or f"data_{selected_tbl}_{row_limit}" in st.session_state:
                    with st.spinner(f"Loading records from `{selected_tbl}`..."):
                        if fetch_clicked or f"data_{selected_tbl}_{row_limit}" not in st.session_state:
                            insp_data = fetch_table_inspector_data(selected_tbl, limit=row_limit)
                            st.session_state[f"data_{selected_tbl}_{row_limit}"] = insp_data
                        else:
                            insp_data = st.session_state[f"data_{selected_tbl}_{row_limit}"]

                        if insp_data.get("status") == "success":
                            records = insp_data.get("records", [])
                            if records:
                                sample_df = pd.DataFrame(records)
                                st.dataframe(sample_df, use_container_width=True, hide_index=True)
                                col_st1, col_st2 = st.columns([2, 1])
                                with col_st1:
                                    st.caption(f"✅ Loaded {len(sample_df)} sample rows (Total: {insp_data.get('total_rows', 0):,} rows) in {insp_data.get('elapsed_sec', 0)}s.")
                                with col_st2:
                                    st.download_button("📥 Export to CSV", sample_df.to_csv(index=False).encode('utf-8'), f"{selected_tbl}_sample.csv", "text/csv")
                            else:
                                st.info(f"Table `{selected_tbl}` is empty.")
                        else:
                            st.error(f"Failed to load records: {insp_data.get('error')}")

            with insp_tab_schema:
                if st.button("🔍 Fetch Schema", key=f"load_schema_{selected_tbl}"):
                    insp_data = fetch_table_inspector_data(selected_tbl, limit=1)
                    if insp_data.get("status") == "success":
                        st.dataframe(pd.DataFrame(insp_data.get("schema", [])), use_container_width=True, hide_index=True)

            with insp_tab_sql:
                custom_sql_input = st.text_area("SQL Query:", value=f"SELECT * FROM {selected_tbl} LIMIT 25;", height=100)
                if st.button("▶️ Execute Inline", key=f"run_sql_{selected_tbl}", type="primary"):
                    with st.spinner("Running query..."):
                        custom_res = fetch_table_inspector_data(selected_tbl, custom_sql=custom_sql_input)
                        if custom_res.get("status") == "success":
                            c_records = custom_res.get("records", [])
                            if c_records:
                                st.dataframe(pd.DataFrame(c_records), use_container_width=True, hide_index=True)
                        else:
                            st.error(f"Error: {custom_res.get('error')}")
    else:
        st.info("No tables currently registered in Hive Metastore.")


# =============================================================
# MODULE 5: TABLE BACKUP & DISASTER RECOVERY
# =============================================================
elif menu == "📦 Table Backup & Restore":
    ui_components.render_html("""
    <div class="glass-card">
        <h2 style="margin: 0; font-weight: 800; font-size: 1.4rem; color: #ffffff;">📦 Enterprise Table & Full Database Disaster Recovery</h2>
        <p style="margin: 6px 0 0 0; color: #cbd5e1; font-size: 0.90rem;">
            Take bit-for-bit verified backups of single tables or entire databases with SHA-256 integrity checksums to guarantee zero data corruption.
        </p>
    </div>
    """, unsafe_allow_html=True)

    df_tables = get_hive_metastore_tables()
    all_table_names = [f"{r['Database']}.{r['Table Name']}" for _, r in df_tables.iterrows()] if not df_tables.empty else []
    all_dbs = sorted(list(set([r['Database'] for _, r in df_tables.iterrows()]))) if not df_tables.empty else ["default"]

    b_tab_create, b_tab_list, b_tab_restore = st.tabs(["💾 Create Backup", "📂 Local Backups Explorer", "🔄 Restore Table/Database"])

    with b_tab_create:
        bk_scope = st.radio("Backup Scope:", ["📁 Single Table Backup", "🗄️ Complete Database Backup"], horizontal=True)
        if "Single Table" in bk_scope and all_table_names:
            col_bk1, col_bk2 = st.columns(2)
            with col_bk1:
                selected_bk_table = st.selectbox("Select Table to Backup:", all_table_names, key="bk_sel_table")
            with col_bk2:
                custom_bk_id = st.text_input("Custom Backup Identifier (Optional):", value="", key="bk_custom_id")

            if st.button("🚀 Create Full Table Backup", type="primary"):
                parts = selected_bk_table.split(".")
                out, code = execute_backup_job(mode="table", db_name=parts[0], table_name=parts[1], custom_id=custom_bk_id.strip() if custom_bk_id else None)
                if code == 0 and "__BACKUP_RESULT__|" in out:
                    st.success("🎉 Backup completed with 100% integrity!")
                else:
                    st.error(f"❌ Backup failed: {out}")
        else:
            selected_bk_db = st.selectbox("Select Database to Backup:", all_dbs, key="bk_sel_db")
            if st.button("🚀 Create Complete Database Backup", type="primary"):
                out, code = execute_backup_job(mode="database", db_name=selected_bk_db)
                if code == 0:
                    st.success("🎉 Complete database backup created successfully!")
                else:
                    st.error(f"❌ Database backup failed: {out}")

    with b_tab_list:
        local_bks = list_local_backups()
        if local_bks:
            bk_summary_list = []
            for b in local_bks:
                bk_summary_list.append({
                    "Backup ID": b.get("backup_id"),
                    "Target": f"{b.get('database')}.{b.get('table', 'ALL')}",
                    "Total Rows": f"{b.get('total_rows', 0):,}",
                    "Size": f"{b.get('total_size_mb', 0)} MB",
                    "Created At": b.get("created_at")
                })
            st.dataframe(pd.DataFrame(bk_summary_list), use_container_width=True, hide_index=True)
        else:
            st.info("No backups currently stored in `/backups/`.")

    with b_tab_restore:
        local_bks = list_local_backups()
        if local_bks:
            b_options = [b['backup_id'] for b in local_bks]
            selected_res_id = st.selectbox("Select Backup to Restore:", b_options)
            chosen_b = next(b for b in local_bks if b["backup_id"] == selected_res_id)
            is_db_restore = chosen_b.get("backup_type") == "database"
            
            res_target_db = st.text_input("Restore Target Database", value=chosen_b.get("database", "default"), key="res_db")
            res_target_tbl = st.text_input("Restore Target Table Name", value=chosen_b.get("table", "restored_table"), key="res_tbl") if not is_db_restore else None

            if st.button("🔄 Execute Full Restore", type="primary"):
                out, code = execute_restore_job(selected_res_id, mode="database" if is_db_restore else "table", target_db=res_target_db, target_table=res_target_tbl)
                if code == 0:
                    st.success("🎉 Restore completed and verified successfully!")
                else:
                    st.error(f"❌ Restore failed: {out}")
        else:
            st.info("No backups found.")


# =============================================================
# MODULE 6: DELTA TIME-TRAVEL & MAINTENANCE
# =============================================================
elif menu == "⏳ Delta Time-Travel & Maintenance":
    ui_components.render_html("""
    <div class="glass-card">
        <h2 style="margin: 0; font-weight: 800; font-size: 1.4rem; color: #ffffff;">⏳ Delta Lake Time-Travel, Z-Ordering & VACUUM Maintenance</h2>
        <p style="margin: 6px 0 0 0; color: #cbd5e1; font-size: 0.90rem;">
            Inspect transaction history, query historical snapshots (<code>VERSION AS OF</code>), execute 1-click in-place rollbacks, 
            and trigger <b>Z-Order Compaction (<code>OPTIMIZE</code>)</b> and <b>Storage Vacuuming</b>.
        </p>
    </div>
    """, unsafe_allow_html=True)

    df_tables = get_hive_metastore_tables()
    if not df_tables.empty:
        all_table_names = [f"{r['Database']}.{r['Table Name']}" for _, r in df_tables.iterrows()]
        selected_tbl = st.selectbox("Select Table to Manage:", options=all_table_names)

        tab_hist, tab_opt, tab_vac, tab_rb = st.tabs([
            "📜 Commit History & Time-Travel",
            "⚡ Compaction & Z-Order (OPTIMIZE)",
            "🧹 Storage Reclamation (VACUUM)",
            "⏪ Table Rollback / Restore"
        ])

        with tab_hist:
            if st.button(f"🔍 Fetch History for `{selected_tbl}`", type="primary"):
                out, code = execute_spark_sql(f"DESCRIBE HISTORY {selected_tbl};")
                st.code(out)

            st.markdown("---")
            ver_input = st.number_input("Version As Of (Integer Version ID):", min_value=0, max_value=1000, value=0)
            if st.button(f"👁️ Preview `{selected_tbl}` at Version {ver_input}"):
                out, code = execute_spark_sql(f"SELECT * FROM {selected_tbl} VERSION AS OF {ver_input} LIMIT 20;")
                st.code(out)

        with tab_opt:
            zorder_col_input = st.text_input("Z-Order Columns (Optional, e.g. `season, itemid`):", value="")
            if st.button("🚀 Run OPTIMIZE Compaction", type="primary"):
                opt_sql = f"OPTIMIZE {selected_tbl} ZORDER BY ({zorder_col_input.strip()});" if zorder_col_input.strip() else f"OPTIMIZE {selected_tbl};"
                out, code = execute_spark_sql(opt_sql)
                st.code(out)

        with tab_vac:
            retention_hours = st.number_input("Retention Period (Hours):", min_value=0, max_value=720, value=168, step=24)
            if st.button("🧹 Run VACUUM Storage Cleanup", type="primary"):
                vac_sql = f"SET spark.databricks.delta.vacuum.parallelDelete.enabled = true; VACUUM {selected_tbl} RETAIN {retention_hours} HOURS;"
                out, code = execute_spark_sql(vac_sql)
                st.code(out)

        with tab_rb:
            restore_version = st.number_input("Target Version to Restore to:", min_value=0, max_value=1000, value=0, key="rb_ver")
            if st.button(f"⚠️ Restore `{selected_tbl}` to Version {restore_version}", type="primary"):
                rest_sql = f"RESTORE TABLE {selected_tbl} TO VERSION AS OF {restore_version};"
                out, code = execute_spark_sql(rest_sql)
                st.code(out)
    else:
        st.info("No tables available.")


# =============================================================
# MODULE 7: SCHEDULED INGESTION JOBS
# =============================================================
elif menu == "⏰ Scheduled Ingestion Jobs":
    ui_components.render_html("""
    <div class="glass-card">
        <h2 style="margin: 0; font-weight: 800; font-size: 1.4rem; color: #ffffff;">⏰ Recurring Batch Ingestion & Folder Watchers</h2>
        <p style="margin: 6px 0 0 0; color: #cbd5e1; font-size: 0.90rem;">
            Automate recurring batch pipelines to monitor directories and append delta updates into Hive tables.
        </p>
    </div>
    """)

    jobs = load_scheduled_jobs()
    col_j1, col_j2 = st.columns([1, 1])
    with col_j1:
        st.markdown('<div class="section-title">➕ Create Ingestion Pipeline</div>', unsafe_allow_html=True)
        job_name = st.text_input("Job Name", value="hourly_sales_ingest")
        watch_path = st.text_input("Watch Folder / HDFS Wildcard", value="hdfs://namenode:9000/data/incoming/*.csv")
        target_db_j = st.text_input("Target Database", value="default", key="job_db")
        target_tbl_j = st.text_input("Target Table", value="sales_stream", key="job_tbl")
        target_fmt_j = st.selectbox("Format", ["Delta Lake", "Parquet"], key="job_fmt")
        job_interval = st.selectbox("Interval", ["Every 15 Minutes", "Hourly", "Daily at Midnight", "Manual / On-Demand"])

        if st.button("💾 Save Scheduled Pipeline", type="primary", use_container_width=True):
            new_job = {
                "id": str(int(time.time())),
                "name": job_name,
                "watch_path": watch_path,
                "database": target_db_j,
                "table": target_tbl_j,
                "format": target_fmt_j,
                "interval": job_interval,
                "status": "Active",
                "last_run": "Never",
                "rows_processed": 0
            }
            jobs.append(new_job)
            save_scheduled_jobs(jobs)
            st.success(f"🎉 Pipeline `{job_name}` registered!")
            st.rerun()

    with col_j2:
        st.markdown('<div class="section-title">📋 Active Ingestion Pipelines</div>', unsafe_allow_html=True)
        if jobs:
            for j in jobs:
                with st.expander(f"⚙️ **{j['name']}** ➔ `{j['database']}.{j['table']}` ({j['interval']})", expanded=True):
                    st.write(f"📁 Path: `{j['watch_path']}` | Rows: {j['rows_processed']:,}")
                    if st.button(f"🗑️ Delete", key=f"del_{j['id']}"):
                        jobs = [x for x in jobs if x['id'] != j['id']]
                        save_scheduled_jobs(jobs)
                        st.rerun()
        else:
            st.info("No recurring batch jobs registered yet.")


# =============================================================
# MODULE 8: CLUSTER HEALTH & TOPOLOGIES
# =============================================================
elif menu == "📊 Cluster Health & Links":
    ui_components.render_html("""
    <div class="glass-card">
        <h2 style="margin: 0; font-weight: 800; font-size: 1.4rem; color: #ffffff;">📊 BDP Cluster Health & Infrastructure Topology</h2>
        <p style="margin: 6px 0 0 0; color: #cbd5e1; font-size: 0.90rem;">
            Real-time health status, endpoints, and telemetry for all distributed Big Data containers.
        </p>
    </div>
    """)

    df_containers = get_container_stats()
    if not df_containers.empty:
        st.dataframe(df_containers, use_container_width=True, hide_index=True)
    else:
        st.warning("No containers detected.")


# =============================================================
# MODULE 9: CONTAINER LOGS STREAMER
# =============================================================
elif menu == "📜 Container Logs Viewer":
    ui_components.render_html("""
    <div class="glass-card">
        <h2 style="margin: 0; font-weight: 800; font-size: 1.4rem; color: #ffffff;">📜 Real-Time Container Log Streamer</h2>
        <p style="margin: 6px 0 0 0; color: #cbd5e1; font-size: 0.90rem;">
            Inspect live stdout and stderr streams directly from any cluster service container.
        </p>
    </div>
    """)

    all_containers = [c.name for c in client.containers.list(all=True)]
    if all_containers:
        selected_container = st.selectbox("Select Container to Inspect", sorted(all_containers))
        lines = st.slider("Tail Line Count", 50, 1000, 150, step=50)
        if selected_container:
            try:
                container = client.containers.get(selected_container)
                logs = container.logs(tail=lines).decode('utf-8', errors='ignore')
                st.markdown(f'<div class="terminal-container">{logs.replace(chr(10), "<br>")}</div>', unsafe_allow_html=True)
            except Exception as ex:
                st.error(f"Error fetching logs: {ex}")


# =============================================================
# MODULE 10: ONE-CLICK STATE PURGE
# =============================================================
elif menu == "🧹 One-Click Cleanup":
    ui_components.render_html("""
    <div class="glass-card">
        <h2 style="margin: 0; font-weight: 800; font-size: 1.4rem; color: #ffffff;">🧹 One-Click Cluster State & Memory Purge</h2>
        <p style="margin: 6px 0 0 0; color: #cbd5e1; font-size: 0.90rem;">
            Instantly terminate orphaned Livy sessions, clear idle PostgreSQL metastore connections, and self-heal HDFS missing blocks.
        </p>
    </div>
    """)

    if st.button("🚀 Run Full Memory & Session Cleanup", type="primary", use_container_width=True):
        with st.spinner("Purging hanging sessions and memory..."):
            results = purge_hanging_state_and_memory()
            st.success("Cluster Cleanup Action Completed!")
            for log_msg in results:
                st.write(log_msg)


# =============================================================
# MODULE 11: CLUSTER DIAGNOSTICS
# =============================================================
elif menu == "🔍 Cluster Diagnostics":
    ui_components.render_html("""
    <div class="glass-card">
        <h2 style="margin: 0; font-weight: 800; font-size: 1.4rem; color: #ffffff;">🔍 Automated Multi-Port Cluster Network Diagnostics</h2>
        <p style="margin: 6px 0 0 0; color: #cbd5e1; font-size: 0.90rem;">
            Perform full-mesh port connectivity probing across Spark Master, Workers 1-4, Livy, NameNode, YARN, MinIO, and HiveServer2.
        </p>
    </div>
    """)

    if st.button("▶️ Run Automated Multi-Port Diagnostics", type="primary", use_container_width=True):
        with st.spinner("Diagnosing cluster network endpoints..."):
            result = subprocess.run(["/app/diagnose_cluster.sh"], capture_output=True, text=True)
            st.markdown(f'<div class="terminal-container">{result.stdout.replace(chr(10), "<br>")}</div>', unsafe_allow_html=True)


# =============================================================
# MODULE 12: PLATFORM DOCS & GUIDE CENTER
# =============================================================
elif menu == "📚 Platform Docs & Guide Center":
    ui_components.render_html("""
    <div class="glass-card">
        <h2 style="margin: 0; font-weight: 800; font-size: 1.4rem; color: #ffffff;">📚 Big Data Platform Documentation & Feature Catalog</h2>
        <p style="margin: 6px 0 0 0; color: #cbd5e1; font-size: 0.90rem;">
            Architecture guides, connection strings, tuning formulas, and disaster recovery blueprints.
        </p>
    </div>
    """)

    doc_files = {
        "⚡ Spark Performance Tuning Benchmark (59.18M Rows)": "/app/docs/spark_performance_tuning_benchmark.md",
        "⚡ Spark Dynamic Tuning & Cluster Scaling Guide": "/app/docs/spark_tuning_scaling_guide.md",
        "📦 Table & Full Database Disaster Recovery Guide": "/app/docs/table_backup_restore_guide.md",
        "🚀 Production Data Pipeline & Delta Performance Guide": "/app/docs/data_pipeline_delta_guide.md",
        "📖 Platform Architecture & Quickstart (README.md)": "/app/README.md"
    }

    available_docs = {}
    for title, path in doc_files.items():
        alt_paths = [path, path.replace("/app/", ""), path.replace("/app/docs/", "docs/")]
        for ap in alt_paths:
            if os.path.exists(ap):
                available_docs[title] = ap
                break

    if available_docs:
        selected_doc_title = st.selectbox("Select Documentation Guide:", list(available_docs.keys()))
        selected_path = available_docs[selected_doc_title]
        try:
            with open(selected_path, "r", encoding="utf-8") as f:
                doc_content = f.read()
            st.markdown("---")
            st.markdown(doc_content)
        except Exception as e:
            st.error(f"Error reading doc: {e}")
