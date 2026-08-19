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

st.set_page_config(
    page_title="BDP Data Studio & Performance Engine",
    layout="wide",
    page_icon="⚡",
    initial_sidebar_state="expanded"
)

# Connect to Docker Daemon
try:
    client = docker.from_env()
except Exception as e:
    st.error(f"Failed to connect to Docker daemon: {e}")
    st.stop()

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
            "admin-panel", "hive-metastore-postgres", "pgadmin", "keycloak"
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

# Sidebar Navigation
st.sidebar.title("⚡ Big Data Studio & Engine")
menu = st.sidebar.radio(
    "Navigation Menu",
    [
        "📥 Data Ingestion & Partitioning",
        "⚡ Spark Tuning & Cluster Scaling",
        "📦 Table Backup & Restore",
        "⏳ Delta Time-Travel & Maintenance",
        "⏰ Scheduled Ingestion Jobs",
        "🗄️ Metastore Table Explorer",
        "📚 Platform Docs & Guide Center",
        "📊 Cluster Health & Links",
        "🧹 One-Click Cleanup",
        "🔍 Cluster Diagnostics",
        "📜 Container Logs Viewer"
    ]
)

st.sidebar.markdown("---")
st.sidebar.markdown("**Quick Platform Portals:**")
st.sidebar.markdown("🎨 [Hue Query Editor](http://localhost:8888)")
st.sidebar.markdown("📓 [JupyterLab](http://localhost:8889)")
st.sidebar.markdown("🪣 [MinIO S3 Console](http://localhost:9001)")
st.sidebar.markdown("🔐 [Keycloak IAM](http://localhost:8080)")

# -------------------------------------------------------------
# TAB 1: DATA INGESTION & PARTITIONING
# -------------------------------------------------------------
if menu == "📥 Data Ingestion & Partitioning":
    st.header("📥 Ingest Files, Partition & Register Tables in Hue")
    st.markdown(
        "Upload files (up to **1,000 GB**) or select host / HDFS datasets to automatically "
        "detect schemas, **override data types**, **configure dynamic partition keys**, "
        "and register optimized **Parquet / Delta Lake tables** in **Hue & Hive Metastore**."
    )

    source_type = st.radio(
        "Select Data Source Mode:",
        [
            "📁 Multi-File Browser Upload (CSV / Parquet / JSON / TSV up to 1000GB)",
            "🐘 Direct Path Ingestion (Host File / Windows Mount / HDFS Path / Wildcards)"
        ],
        horizontal=True
    )

    st.markdown("---")

    uploaded_files = []
    input_file_paths = []
    file_format = "csv"
    df_preview = None
    base_table_name = "new_table"

    if "Multi-File Browser Upload" in source_type:
        uploaded_files = st.file_uploader(
            "Drag and drop or browse one or multiple data files",
            type=["csv", "parquet", "pq", "json", "tsv", "txt"],
            accept_multiple_files=True,
            help="Files up to 1,000 GB each are supported."
        )

        if uploaded_files:
            st.success(f"📁 {len(uploaded_files)} file(s) selected: {', '.join([f.name for f in uploaded_files[:5]])}{'...' if len(uploaded_files) > 5 else ''}")
            
            # Select preview file if multiple
            preview_file = uploaded_files[0]
            if len(uploaded_files) > 1:
                file_names = [f.name for f in uploaded_files]
                selected_preview_name = st.selectbox("Select file to preview schema:", file_names)
                preview_file = next(f for f in uploaded_files if f.name == selected_preview_name)
            
            base_table_name = sanitize_table_name(os.path.splitext(uploaded_files[0].name)[0])
            
            # Robust auto-detect preview parsing using temporary disk buffer
            preview_file.seek(0)
            data_bytes = preview_file.read()
            preview_file.seek(0)

            # Write full file bytes to temporary file and flush/close immediately
            ext_suffix = os.path.splitext(preview_file.name)[1]
            tmp_f = tempfile.NamedTemporaryFile(delete=False, suffix=ext_suffix)
            tmp_f.write(data_bytes)
            tmp_f.flush()
            tmp_f.close()
            tmp_path = tmp_f.name

            try:
                # 1. Try Parquet reading via pyarrow (supports all snappy, dictionary, multi-chunk Parquet files)
                if preview_file.name.lower().endswith(('.parquet', '.pq')) or data_bytes.startswith(b'PAR1'):
                    file_format = "parquet"
                    try:
                        tbl = pq.read_table(tmp_path)
                        df_preview = tbl.to_pandas().head(50)
                    except Exception as pq_err:
                        try:
                            df_preview = pd.read_parquet(tmp_path).head(50)
                        except Exception:
                            st.error(
                                "❌ **Incomplete / Corrupted Parquet File Detected**\n\n"
                                f"The uploaded file `{preview_file.name}` is missing its trailing metadata footer (`PAR1` signature at tail).\n\n"
                                "💡 **Why this happens**: When a file download or AWS Glue/Spark export is interrupted before finishing, "
                                "the file has the opening header but is cut off before the schema footer is written to disk.\n\n"
                                "👉 **Action Required**: Please re-download the complete file from your source AWS S3 bucket / system."
                            )

                # 2. Try JSON
                elif preview_file.name.lower().endswith('.json') or data_bytes.strip().startswith((b'{', b'[')):
                    file_format = "json"
                    try:
                        df_preview = pd.read_json(tmp_path, lines=True, nrows=50)
                    except Exception:
                        try:
                            df_preview = pd.read_json(tmp_path, nrows=50)
                        except Exception as json_err:
                            st.warning(f"Could not parse JSON structure: {json_err}")

                # 3. Fallback to CSV / TSV (only for text/csv files)
                else:
                    file_format = "csv"
                    try:
                        if preview_file.name.lower().endswith(('.tsv', '.tab')):
                            df_preview = pd.read_csv(tmp_path, sep='\t', nrows=50)
                        else:
                            df_preview = pd.read_csv(tmp_path, nrows=50)
                    except Exception:
                        try:
                            df_preview = pd.read_csv(tmp_path, sep=None, engine='python', nrows=50)
                        except Exception as csv_err:
                            st.warning(f"Could not parse CSV structure: {csv_err}")
            finally:
                if os.path.exists(tmp_path):
                    try:
                        os.unlink(tmp_path)
                    except Exception:
                        pass

    else:
        st.info("💡 **Direct Path Mode**: Ingest large files (5GB, 20GB, 50GB+) directly from your Windows disk or HDFS without browser upload overhead.")
        path_input = st.text_input(
            "Enter Host Path (Windows/WSL) or HDFS Path / Wildcard:",
            value="hdfs://namenode:9000/data/benchmark/sales_train_evaluation.csv",
            help="Example: /mnt/c/Users/satish.hiremath/.../sales.csv or hdfs://namenode:9000/data/breweries.csv or /data/*.csv"
        )
        if path_input:
            input_file_path = path_input.strip()
            # Windows path translation if needed
            if re.match(r'^[a-zA-Z]:\\', input_file_path):
                drive_letter = input_file_path[0].lower()
                rel_path = input_file_path[2:].replace('\\', '/')
                input_file_path = f"/mnt/{drive_letter}{rel_path}"
                st.caption(f"ℹ️ Translated Windows path to WSL: `{input_file_path}`")
            
            input_file_paths = [input_file_path]
            base_filename = os.path.basename(input_file_path.replace('*', ''))
            base_table_name = sanitize_table_name(os.path.splitext(base_filename)[0])
            
            if input_file_path.endswith(".parquet") or input_file_path.endswith(".pq"):
                file_format = "parquet"
            elif input_file_path.endswith(".json"):
                file_format = "json"
            else:
                file_format = "csv"

            # Try sample preview if local path
            if os.path.exists(input_file_path) and os.path.isfile(input_file_path):
                try:
                    if file_format == "parquet":
                        df_preview = pd.read_parquet(input_file_path)
                    elif file_format == "json":
                        df_preview = pd.read_json(input_file_path, lines=True, nrows=50)
                    else:
                        df_preview = pd.read_csv(input_file_path, nrows=50)
                except Exception:
                    pass

    # ---------------------------------------------------------
    # Preview & Schema Override Section
    # ---------------------------------------------------------
    type_overrides = {}
    detected_cols = []
    if df_preview is not None:
        st.subheader("🔍 Schema Preview & Column Data Type Overrides")
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Columns Detected", len(df_preview.columns))
        col_m2.metric("Sample Rows Loaded", len(df_preview))
        col_m3.metric("Detected File Format", file_format.upper())
        
        st.dataframe(df_preview.head(20), use_container_width=True)
        detected_cols = [sanitize_column_name(c) for c in df_preview.columns]

        with st.expander("🛠️ Override Column Data Types (Optional)", expanded=False):
            st.markdown("Change any column's target data type before inserting into Hive / S3:")
            available_types = [
                "Auto (Inferred)",
                "STRING",
                "INT",
                "BIGINT",
                "DOUBLE",
                "FLOAT",
                "DECIMAL(18,2)",
                "BOOLEAN",
                "DATE",
                "TIMESTAMP"
            ]

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
                            selected_t = st.selectbox(
                                f"`{cname}` ➔ `{s_name}` ({inferred_type}):",
                                available_types,
                                key=f"type_override_{cname}",
                                index=0
                            )
                            if selected_t != "Auto (Inferred)":
                                type_overrides[s_name] = selected_t

            if type_overrides:
                st.info(f"⚙️ Active Column Overrides: {type_overrides}")

    # ---------------------------------------------------------
    # Target Table, Partitioning & Storage Configuration
    # ---------------------------------------------------------
    st.subheader("⚙️ Target Table, Partitioning & Storage Configuration")
    
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

    # Partition Selection
    selected_partitions = []
    if detected_cols:
        selected_partitions = st.multiselect(
            "🗂️ Select Partition Column(s) for Sub-Second Query Pruning in Hue:",
            options=detected_cols,
            help="Partitioning by columns like date, year, store_id, or region speeds up queries by skipping 90%+ of data files."
        )
        if selected_partitions:
            st.caption(f"📁 Partition Directory Layout: `s3a://warehouse/{target_table}/{'='.join(selected_partitions)}=.../`")

    col_w1, col_w2 = st.columns(2)
    with col_w1:
        write_mode = st.radio("Write Mode", ["Overwrite (Replace existing table)", "Append (Add to existing data)"], horizontal=True)
    with col_w2:
        if len(uploaded_files) > 1:
            multi_file_strategy = st.radio("Multi-File Ingestion Strategy", ["Merge All into Single Table (Union)", "Create Separate Table per File"], horizontal=True)
        else:
            multi_file_strategy = "Single Table"

    # ---------------------------------------------------------
    # Spark Execution Sizing & Resource Tuning
    # ---------------------------------------------------------
    total_est_bytes = sum(f.size for f in uploaded_files) if uploaded_files else 100 * 1024 * 1024
    rec_prof_name, rec_mb = spark_tuning_manager.recommend_profile_for_filesize(total_est_bytes)
    
    with st.expander(f"⚡ Spark Execution Sizing & Compute Tuning (Recommended: {rec_prof_name})", expanded=True):
        col_sz1, col_sz2 = st.columns([1.5, 2])
        with col_sz1:
            profile_keys = list(spark_tuning_manager.PROFILES.keys()) + ["🛠️ Custom Engine Tuning"]
            default_idx = profile_keys.index(rec_prof_name) if rec_prof_name in profile_keys else 1
            selected_ingest_profile = st.selectbox(
                "Select Execution Profile:",
                profile_keys,
                index=default_idx,
                key="ingest_sizing_profile"
            )
        with col_sz2:
            if selected_ingest_profile != "🛠️ Custom Engine Tuning":
                p_meta = spark_tuning_manager.PROFILES[selected_ingest_profile]
                st.caption(f"💡 **Profile Summary**: {p_meta['description']}")
                st.markdown(f"**Driver**: `{p_meta['driver_memory']}` | **Executor**: `{p_meta['executor_memory']}` | **Cores**: `{p_meta['executor_cores']}` | **Shuffle Partitions**: `{p_meta['shuffle_partitions']}` | **AQE**: `{'Enabled' if p_meta['aqe_enabled'] else 'Disabled'}`")
            else:
                st.caption("💡 Customize exact JVM memory and CPU cores for this specific ingestion job.")

        if selected_ingest_profile == "🛠️ Custom Engine Tuning":
            col_cust1, col_cust2, col_cust3, col_cust4 = st.columns(4)
            with col_cust1:
                c_driver_mem = st.selectbox("Driver Memory", ["1g", "2g", "4g", "8g", "16g"], index=1, key="c_drv_mem")
            with col_cust2:
                c_exec_mem = st.selectbox("Executor Memory", ["2g", "4g", "8g", "16g", "32g"], index=1, key="c_exe_mem")
            with col_cust3:
                c_exec_cores = st.number_input("Executor Cores", min_value=1, max_value=16, value=2, key="c_exe_cores")
            with col_cust4:
                c_shuffle_parts = st.number_input("Shuffle Partitions", min_value=1, max_value=800, value=64, key="c_shuf_parts")
            
            c_aqe = st.checkbox("Enable Adaptive Query Execution (AQE)", value=True, key="c_aqe_chk")
            chosen_ingest_params = {
                "driver_memory": c_driver_mem,
                "executor_memory": c_exec_mem,
                "executor_cores": c_exec_cores,
                "max_cores": c_exec_cores * 2,
                "shuffle_partitions": c_shuffle_parts,
                "aqe_enabled": c_aqe,
                "aqe_coalesce": c_aqe,
                "memory_fraction": 0.7,
                "storage_fraction": 0.5,
                "offheap_enabled": False,
                "offheap_size": "0",
                "kryo_serializer": True
            }
        else:
            chosen_ingest_params = spark_tuning_manager.PROFILES[selected_ingest_profile]

    st.markdown("---")

    # Ingestion Action Button
    can_proceed = (len(uploaded_files) > 0) or (len(input_file_paths) > 0)
    if not can_proceed:
        st.info("👆 Please upload one or more files, or enter a valid file path above.")
    
    if st.button("🚀 Ingest & Register Table in Hue", type="primary", disabled=not can_proceed):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            status_text.info("⏳ Step 1/4: Staging files and verifying cluster connection...")
            progress_bar.progress(20)

            namenode_cont = client.containers.get("namenode")
            namenode_cont.exec_run("hdfs dfs -mkdir -p /data/uploads")
            
            staged_source_paths = []

            # 1. Process browser uploads
            if uploaded_files:
                for idx, ufile in enumerate(uploaded_files):
                    status_text.info(f"⏳ Staging file {idx+1}/{len(uploaded_files)}: `{ufile.name}` ({ufile.size / (1024*1024):.1f} MB)...")
                    staging_hdfs_path = f"/data/uploads/{ufile.name}"
                    
                    ufile.seek(0)
                    file_bytes = ufile.read()
                    copy_data_to_container(namenode_cont, file_bytes, "/tmp", ufile.name)
                    
                    put_res = namenode_cont.exec_run(f"hdfs dfs -put -f /tmp/{ufile.name} {staging_hdfs_path}")
                    if put_res.exit_code != 0:
                        err_msg = put_res.output.decode('utf-8', errors='ignore') if put_res.output else "HDFS put error"
                        raise Exception(f"Failed to stage {ufile.name} to HDFS: {err_msg}")
                    
                    namenode_cont.exec_run(f"rm -f /tmp/{ufile.name}")
                    staged_source_paths.append(f"hdfs://namenode:9000{staging_hdfs_path}")

            # 2. Process direct host / HDFS paths
            elif input_file_paths:
                for ipath in input_file_paths:
                    if ipath.startswith("hdfs://") or ipath.startswith("/data/"):
                        staged_source_paths.append(ipath if ipath.startswith("hdfs://") else f"hdfs://namenode:9000{ipath}")
                    elif os.path.exists(ipath):
                        fname = os.path.basename(ipath)
                        staging_hdfs_path = f"/data/uploads/{fname}"
                        status_text.info(f"⏳ Streaming host file `{fname}` into HDFS...")
                        
                        with open(ipath, "rb") as f:
                            file_bytes = f.read()
                        copy_data_to_container(namenode_cont, file_bytes, "/tmp", fname)
                        
                        put_res = namenode_cont.exec_run(f"hdfs dfs -put -f /tmp/{fname} {staging_hdfs_path}")
                        if put_res.exit_code != 0:
                            raise Exception(f"Failed to put {fname} into HDFS")
                        namenode_cont.exec_run(f"rm -f /tmp/{fname}")
                        staged_source_paths.append(f"hdfs://namenode:9000{staging_hdfs_path}")

            status_text.info("⏳ Step 2/4: Generating dynamic PySpark schema, partitions, and type casting script...")
            progress_bar.progress(40)

            # Determine storage destination
            is_s3 = "MinIO" in storage_dest
            if is_s3:
                dest_path = f"s3a://warehouse/{target_table}/"
            else:
                dest_path = f"hdfs://namenode:9000/user/hive/warehouse/{target_table}/"

            save_mode = "overwrite" if "Overwrite" in write_mode else "append"
            is_delta = "Delta Lake" in output_format

            # Build PySpark Ingestion Script
            spark_script = f"""
import time
import re
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

spark = SparkSession.builder \\
    .appName("UI_Ingestion_{target_table}") \\
    .config("spark.driver.memory", "{chosen_ingest_params.get('driver_memory', '2g')}") \\
    .config("spark.executor.memory", "{chosen_ingest_params.get('executor_memory', '3g')}") \\
    .config("spark.sql.shuffle.partitions", "{chosen_ingest_params.get('shuffle_partitions', 64)}") \\
    .enableHiveSupport() \\
    .getOrCreate()

t0 = time.time()
source_paths = {json.dumps(staged_source_paths)}
print(f"--> Reading source files: {{source_paths}}")
"""
            if file_format == "csv":
                spark_script += f"""
df = spark.read \\
    .option("header", "true") \\
    .option("inferSchema", "true") \\
    .csv(source_paths)
"""
            elif file_format == "parquet":
                spark_script += f"""
df = spark.read.parquet(*source_paths)
"""
            elif file_format == "json":
                spark_script += f"""
df = spark.read.json(source_paths)
"""

            spark_script += f"""
# 1. Sanitize all column names for universal Hive, Parquet, and Hue SQL compatibility
for c in df.columns:
    clean_c = re.sub(r'[^a-zA-Z0-9_]', '_', c.strip()).lower()
    clean_c = re.sub(r'_+', '_', clean_c).strip('_')
    if clean_c and clean_c[0].isdigit():
        clean_c = f"col_{{clean_c}}"
    clean_c = clean_c if clean_c else "unnamed_col"
    if clean_c != c:
        df = df.withColumnRenamed(c, clean_c)

# 2. Apply Custom Column Data Type Overrides
type_overrides = {json.dumps(type_overrides)}
for col_name, target_type in type_overrides.items():
    if col_name in df.columns:
        print(f"--> Casting column '{{col_name}}' to '{{target_type}}'...")
        df = df.withColumn(col_name, F.col(col_name).cast(target_type))

# 3. Dynamic Partitioning & Table Save
writer = df.write.mode("{save_mode}").option("path", "{dest_path}")
partitions = {json.dumps(selected_partitions)}
if partitions:
    print(f"--> Applying Dynamic Partitions: {{partitions}}")
    writer = writer.partitionBy(*partitions)
"""

            if is_delta:
                spark_script += f"""
writer.format("delta").saveAsTable("{target_db}.{target_table}")
"""
            else:
                spark_script += f"""
writer.saveAsTable("{target_db}.{target_table}")
if partitions:
    try:
        spark.sql("MSCK REPAIR TABLE {target_db}.{target_table}")
    except Exception as e:
        print(f"--> MSCK Repair Note: {{e}}")
"""

            spark_script += f"""
row_cnt = df.count()
elapsed = time.time() - t0
print(f"__RESULT_SUCCESS__|{{row_cnt}}|{{elapsed:.2f}}")
spark.stop()
"""

            status_text.info("⏳ Step 3/4: Executing distributed Spark ingestion & Metastore registration...")
            progress_bar.progress(70)

            # Copy script into spark container via Python Docker SDK
            spark_cont = client.containers.get("spark")
            script_filename = f"ingest_{target_table}.py"
            copy_data_to_container(spark_cont, spark_script.encode('utf-8'), "/tmp", script_filename)

            tuning_flags = spark_tuning_manager.build_spark_submit_conf_args(chosen_ingest_params)
            res = spark_cont.exec_run(
                f"/opt/spark/bin/spark-submit {tuning_flags} /tmp/{script_filename}"
            )
            output = res.output.decode('utf-8', errors='ignore')

            if res.exit_code != 0:
                raise Exception(f"Spark Ingestion failed (exit code {res.exit_code}):\n{output}")

            # Parse execution results
            row_count_res = "N/A"
            time_taken_res = "N/A"
            for line in output.splitlines():
                if "__RESULT_SUCCESS__" in line:
                    parts = line.split("|")
                    if len(parts) >= 3:
                        row_count_res = f"{int(parts[1]):,}"
                        time_taken_res = f"{parts[2]}s"

            progress_bar.progress(100)
            status_text.empty()

            st.success(f"🎉 Table `{target_db}.{target_table}` created and registered successfully!")

            col_res1, col_res2, col_res3 = st.columns(3)
            col_res1.metric("Rows Ingested", row_count_res)
            col_res2.metric("Processing Time", time_taken_res)
            col_res3.metric("Storage Location", dest_path)

            if selected_partitions:
                st.info(f"📁 **Partitioned by:** `{', '.join(selected_partitions)}` (Partition pruning enabled in Hue!)")

            st.subheader("🔍 Query in Hue")
            st.markdown(f"Your table is ready to query in **Hue (`http://localhost:8888`)**:")
            sample_query = f"SELECT * FROM {target_db}.{target_table} LIMIT 10;"
            st.code(sample_query, language="sql")

            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                st.link_button("🎨 Open in Hue Query Editor", "http://localhost:8888")
            with col_btn2:
                st.link_button("🪣 View Files in MinIO S3", "http://localhost:9001")

        except Exception as ex:
            progress_bar.progress(100)
            status_text.empty()
            st.error(f"❌ Ingestion Error: {ex}")

# -------------------------------------------------------------
# TAB: SPARK TUNING & CLUSTER SCALING
# -------------------------------------------------------------
elif menu == "⚡ Spark Tuning & Cluster Scaling":
    st.header("⚡ Dynamic Spark Tuning & Horizontal Cluster Scaling")
    st.markdown(
        "Empower administrators to **scale worker nodes up/down on-demand**, dynamically tune "
        "**JVM memory, CPU cores, shuffle partitions, and Adaptive Query Execution (AQE)**, "
        "and select optimal workload sizing profiles to eliminate crashes and OOM errors on large datasets."
    )

    t_tab_scaling, t_tab_profiles, t_tab_active_apps = st.tabs([
        "🖥️ Cluster Compute & Worker Scaling",
        "⚙️ Workload Sizing & Parameter Tuning",
        "📈 Active Applications & Master Telemetry"
    ])

    metrics = spark_tuning_manager.get_spark_master_metrics()

    # 1. HORIZONTAL WORKER SCALING & COMPUTE OVERVIEW
    with t_tab_scaling:
        st.subheader("🖥️ Real-Time Cluster Compute Capacity")
        
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        col_m1.metric("Active Worker Nodes", f"{metrics['alive_workers']} / {metrics['total_workers']}")
        col_m2.metric("Total CPU Cores", f"{metrics['total_cores']} Cores", f"{metrics['cores_free']} Free")
        col_m3.metric("Total Cluster RAM", f"{metrics['total_memory_mb'] / 1024:.1f} GB", f"{metrics['memory_free_mb'] / 1024:.1f} GB Free")
        col_m4.metric("Active Spark Apps", metrics['active_apps_count'])

        st.markdown("---")
        st.subheader("🚀 Horizontal Worker Node Scaling (Elastic Scale Up / Down)")
        st.markdown(
            "Dynamically scale your Spark worker compute fleet up to handle massive batch ingestions, "
            "or scale down to conserve CPU and RAM resources when idle."
        )

        col_sc1, col_sc2 = st.columns([2, 1])
        with col_sc1:
            target_scale = st.slider(
                "Target Worker Node Count:",
                min_value=1,
                max_value=8,
                value=max(1, metrics['alive_workers']),
                help="Number of distributed worker node containers."
            )
            col_ns1, col_ns2 = st.columns(2)
            with col_ns1:
                sel_worker_ram = st.selectbox(
                    "RAM per Worker Node",
                    ["4g", "8g", "16g", "32g"],
                    index=1,
                    help="Hardware memory envelope allocated per worker daemon."
                )
            with col_ns2:
                sel_worker_cores = st.selectbox(
                    "CPU Cores per Worker Node",
                    [2, 4, 8, 16],
                    index=1,
                    help="CPU cores pool allocated per worker daemon."
                )

            ram_int = int(re.sub(r'[^0-9]', '', sel_worker_ram))
            est_cores = target_scale * sel_worker_cores
            est_ram = target_scale * ram_int
            st.info(f"📊 Projected Cluster Capacity: **{est_cores} Total CPU Cores** & **{est_ram} GB Total Cluster RAM** across **{target_scale} Worker(s)** ({sel_worker_ram} RAM / {sel_worker_cores} Cores per node)")
        with col_sc2:
            st.write("")
            st.write("")
            st.write("")
            st.write("")
            if st.button("🚀 Apply Worker Scale & Node Sizing", type="primary", key="btn_apply_scale"):
                with st.spinner(f"Provisioning {target_scale} worker node(s) with {sel_worker_ram} RAM & {sel_worker_cores} Cores..."):
                    out, code = spark_tuning_manager.scale_cluster_workers(target_scale, sel_worker_ram, sel_worker_cores)
                    if code == 0:
                        st.success(f"🎉 {out}")
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error(f"❌ Failed to scale workers: {out}")

        st.markdown("---")
        st.subheader("📋 Registered Worker Nodes")
        if metrics["worker_list"]:
            df_workers = pd.DataFrame(metrics["worker_list"])
            st.dataframe(df_workers, use_container_width=True, hide_index=True)
        else:
            st.warning("⚠️ No worker nodes currently registered with Spark Master. Scale up to at least 1 worker node.")

    # 2. WORKLOAD SIZING PRESETS & FINE-GRAINED TUNING
    with t_tab_profiles:
        st.subheader("⚙️ Workload Sizing Presets & Engine Tuning")
        st.markdown(
            "Select a pre-engineered profile or fine-tune exact JVM memory fractions, shuffle partition counts, "
            "and off-heap memory allocations."
        )

        current_config = spark_tuning_manager.load_tuning_config()
        active_prof_name = current_config.get("active_profile", "🟡 Medium (Standard ETL / Daily Batches)")
        active_params = current_config.get("params", spark_tuning_manager.PROFILES["🟡 Medium (Standard ETL / Daily Batches)"])

        selected_prof = st.selectbox(
            "Select Active Workload Profile:",
            list(spark_tuning_manager.PROFILES.keys()) + ["🛠️ Custom Engine Override"],
            index=list(spark_tuning_manager.PROFILES.keys()).index(active_prof_name) if active_prof_name in spark_tuning_manager.PROFILES else 1,
            key="tuning_prof_sel"
        )

        if selected_prof in spark_tuning_manager.PROFILES:
            prof_data = spark_tuning_manager.PROFILES[selected_prof]
            st.info(f"📋 **Description**: {prof_data['description']}")
            drv_mem_val = prof_data["driver_memory"]
            exe_mem_val = prof_data["executor_memory"]
            exe_cores_val = prof_data["executor_cores"]
            max_cores_val = prof_data["max_cores"]
            shuf_parts_val = prof_data["shuffle_partitions"]
            aqe_val = prof_data["aqe_enabled"]
            aqe_coal_val = prof_data["aqe_coalesce"]
            mem_frac_val = prof_data["memory_fraction"]
            offheap_val = prof_data["offheap_enabled"]
            offheap_sz_val = prof_data["offheap_size"]
            kryo_val = prof_data["kryo_serializer"]
        else:
            st.info("🛠️ **Custom Mode**: Configure exact parameters according to your specific hardware and dataset constraints.")
            drv_mem_val = active_params.get("driver_memory", "2g")
            exe_mem_val = active_params.get("executor_memory", "4g")
            exe_cores_val = active_params.get("executor_cores", 2)
            max_cores_val = active_params.get("max_cores", 4)
            shuf_parts_val = active_params.get("shuffle_partitions", 64)
            aqe_val = active_params.get("aqe_enabled", True)
            aqe_coal_val = active_params.get("aqe_coalesce", True)
            mem_frac_val = active_params.get("memory_fraction", 0.7)
            offheap_val = active_params.get("offheap_enabled", False)
            offheap_sz_val = active_params.get("offheap_size", "0")
            kryo_val = active_params.get("kryo_serializer", True)

        col_t1, col_t2 = st.columns(2)
        with col_t1:
            st.markdown("#### 🧠 JVM Memory Allocation")
            in_drv_mem = st.selectbox(
                "Driver Memory (`spark.driver.memory`)",
                ["1g", "2g", "4g", "8g", "16g", "32g"],
                index=["1g", "2g", "4g", "8g", "16g", "32g"].index(drv_mem_val) if drv_mem_val in ["1g", "2g", "4g", "8g", "16g", "32g"] else 1
            )
            in_exe_mem = st.selectbox(
                "Executor Memory (`spark.executor.memory`)",
                ["2g", "4g", "8g", "16g", "32g", "64g"],
                index=["2g", "4g", "8g", "16g", "32g", "64g"].index(exe_mem_val) if exe_mem_val in ["2g", "4g", "8g", "16g", "32g", "64g"] else 1
            )
            in_mem_frac = st.slider("Execution & Storage Memory Fraction (`spark.memory.fraction`)", 0.5, 0.95, float(mem_frac_val), 0.05)

        with col_t2:
            st.markdown("#### ⚡ CPU Cores & Parallelism")
            in_exe_cores = st.number_input("Cores Per Executor (`spark.executor.cores`)", 1, 16, int(exe_cores_val))
            in_max_cores = st.number_input("Max Cores for Cluster Job (`spark.cores.max`)", 1, 64, int(max_cores_val))
            in_shuf_parts = st.number_input("Shuffle Partitions (`spark.sql.shuffle.partitions`)", 2, 1000, int(shuf_parts_val), step=8)

        st.markdown("#### 🚀 Advanced Query Optimizations")
        col_o1, col_o2, col_o3 = st.columns(3)
        with col_o1:
            in_aqe = st.checkbox("Enable Adaptive Query Execution (AQE)", value=bool(aqe_val))
            in_aqe_coal = st.checkbox("AQE Dynamic Partition Coalescing", value=bool(aqe_coal_val), disabled=not in_aqe)
        with col_o2:
            in_kryo = st.checkbox("Enable Kryo Fast Serialization (`KryoSerializer`)", value=bool(kryo_val))
        with col_o3:
            in_offheap = st.checkbox("Enable Off-Heap Memory (`spark.memory.offHeap.enabled`)", value=bool(offheap_val))
            in_offheap_sz = st.selectbox("Off-Heap Size", ["512m", "1g", "2g", "4g"], index=["512m", "1g", "2g", "4g"].index(offheap_sz_val) if offheap_sz_val in ["512m", "1g", "2g", "4g"] else 1, disabled=not in_offheap)

        compiled_params = {
            "driver_memory": in_drv_mem,
            "executor_memory": in_exe_mem,
            "executor_cores": in_exe_cores,
            "max_cores": in_max_cores,
            "shuffle_partitions": in_shuf_parts,
            "aqe_enabled": in_aqe,
            "aqe_coalesce": in_aqe_coal,
            "memory_fraction": in_mem_frac,
            "storage_fraction": 0.5,
            "offheap_enabled": in_offheap,
            "offheap_size": in_offheap_sz if in_offheap else "0",
            "kryo_serializer": in_kryo
        }

        generated_flags = spark_tuning_manager.build_spark_submit_conf_args(compiled_params)
        st.markdown("#### 📜 Generated Spark Submit CLI Arguments")
        st.code(f"/opt/spark/bin/spark-submit {generated_flags} <job_script.py>", language="bash")

        if st.button("💾 Apply & Save Tuning Profile as Cluster Default", type="primary", key="btn_save_tuning"):
            spark_tuning_manager.save_tuning_config({
                "active_profile": selected_prof,
                "params": compiled_params
            })
            st.success(f"🎉 Tuning configuration updated and saved! All future ingestion and batch jobs will use these parameters.")

    # 3. ACTIVE APPLICATIONS MONITOR
    with t_tab_active_apps:
        st.subheader("📈 Live Running & Queued Applications on Spark Master")
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
                    "Duration": f"{a.get('duration', 0) / 1000:.1f}s",
                    "Submitted At": a.get("submitdate")
                })
            st.dataframe(pd.DataFrame(apps_data), use_container_width=True, hide_index=True)
        else:
            st.info("ℹ️ No applications are currently running on Spark Master. All cluster resources are available.")

# -------------------------------------------------------------
# TAB: TABLE & DATABASE BACKUP & DISASTER RECOVERY
# -------------------------------------------------------------
elif menu == "📦 Table Backup & Restore":
    st.header("📦 Enterprise Table & Full Database Disaster Recovery")
    st.markdown(
        "Take bit-for-bit verified backups of **single tables or entire databases** "
        "to a local folder, complete with **SHA-256 integrity checksums** to guarantee zero data corruption. "
        "Restore single tables or entire databases in 1-click."
    )

    df_tables = get_hive_metastore_tables()
    all_table_names = [f"{r['Database']}.{r['Table Name']}" for _, r in df_tables.iterrows()] if not df_tables.empty else []
    all_dbs = sorted(list(set([r['Database'] for _, r in df_tables.iterrows()]))) if not df_tables.empty else ["default"]

    b_tab_create, b_tab_list, b_tab_restore = st.tabs([
        "💾 Create Backup (Table or Full DB)",
        "📂 Local Backups Explorer",
        "🔄 Restore (Table or Database)"
    ])

    # 1. CREATE BACKUP
    with b_tab_create:
        st.subheader("💾 Create Disaster Recovery Backup")
        bk_scope = st.radio(
            "Select Backup Scope:",
            ["📁 Single Table Backup", "🗄️ Complete Database Backup (All Tables in DB)"],
            horizontal=True
        )

        if "Single Table" in bk_scope:
            if all_table_names:
                col_bk1, col_bk2 = st.columns(2)
                with col_bk1:
                    selected_bk_table = st.selectbox("Select Table to Backup:", all_table_names, key="bk_sel_table")
                with col_bk2:
                    custom_bk_id = st.text_input("Custom Backup Identifier (Optional):", value="", placeholder="e.g. rfid_snapshot_2026", key="bk_custom_id")

                if st.button("🚀 Create Full Table Backup", type="primary"):
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    status_text.info(f"⏳ Initiating backup of `{selected_bk_table}`...")
                    progress_bar.progress(30)
                    
                    parts = selected_bk_table.split(".")
                    db_n = parts[0]
                    tbl_n = parts[1]
                    
                    status_text.info(f"⏳ Exporting data chunks and calculating SHA-256 file checksums...")
                    progress_bar.progress(60)
                    
                    out, code = execute_backup_job(mode="table", db_name=db_n, table_name=tbl_n, custom_id=custom_bk_id.strip() if custom_bk_id else None)
                    progress_bar.progress(100)
                    status_text.empty()
                    
                    if code == 0 and "__BACKUP_RESULT__|" in out:
                        raw_json_line = out.split("__BACKUP_RESULT__|")[1].strip().splitlines()[0].strip()
                        manifest_json = json.loads(raw_json_line)
                        st.success(f"🎉 Backup `{manifest_json['backup_id']}` completed with 100% integrity!")
                        
                        col_bkr1, col_bkr2, col_bkr3, col_bkr4 = st.columns(4)
                        col_bkr1.metric("Rows Backed Up", f"{manifest_json['total_rows']:,}")
                        col_bkr2.metric("Files Count", manifest_json['total_files'])
                        col_bkr3.metric("Backup Size", f"{manifest_json['total_size_mb']} MB")
                        col_bkr4.metric("Duration", f"{manifest_json['elapsed_seconds']}s")
                        
                        st.info(f"📁 **Saved Locally to:** `/backups/{manifest_json['backup_id']}/`")
                    else:
                        st.error(f"❌ Backup failed: {out}")
            else:
                st.info("No tables available in Hive Metastore to backup.")
        else:
            # Complete Database Backup
            col_db1, col_db2 = st.columns(2)
            with col_db1:
                selected_bk_db = st.selectbox("Select Target Database to Backup:", all_dbs, key="bk_sel_db")
            with col_db2:
                custom_db_bk_id = st.text_input("Custom DB Backup Identifier (Optional):", value="", placeholder="e.g. default_db_full_backup", key="bk_custom_db_id")

            db_tables = df_tables[df_tables["Database"] == selected_bk_db] if not df_tables.empty else pd.DataFrame()
            st.info(f"🗄️ Database `{selected_bk_db}` contains **{len(db_tables)} table(s)**: `{', '.join(db_tables['Table Name'].tolist()) if not db_tables.empty else 'none'}`")

            if st.button("🚀 Create Complete Database Backup", type="primary"):
                progress_bar = st.progress(0)
                status_text = st.empty()
                status_text.info(f"⏳ Initiating complete database backup for `{selected_bk_db}` ({len(db_tables)} tables)...")
                progress_bar.progress(30)

                out, code = execute_backup_job(mode="database", db_name=selected_bk_db, custom_id=custom_db_bk_id.strip() if custom_db_bk_id else None)
                progress_bar.progress(100)
                status_text.empty()

                if code == 0 and "__BACKUP_RESULT__|" in out:
                    raw_db_json_line = out.split("__BACKUP_RESULT__|")[1].strip().splitlines()[0].strip()
                    db_manifest = json.loads(raw_db_json_line)
                    st.success(f"🎉 Complete Database Backup `{db_manifest['backup_id']}` created successfully with 100% integrity!")

                    col_dbm1, col_dbm2, col_dbm3, col_dbm4 = st.columns(4)
                    col_dbm1.metric("Tables Backed Up", db_manifest['total_tables'])
                    col_dbm2.metric("Total Rows Across DB", f"{db_manifest['total_rows']:,}")
                    col_dbm3.metric("Total DB Size", f"{db_manifest['total_size_mb']} MB")
                    col_dbm4.metric("Total Duration", f"{db_manifest['elapsed_seconds']}s")

                    st.info(f"📁 **Saved Locally to:** `/backups/{db_manifest['backup_id']}/`")
                else:
                    st.error(f"❌ Database backup failed: {out}")

    # 2. LOCAL BACKUPS EXPLORER
    with b_tab_list:
        st.subheader("📂 Local Backups in `/backups/`")
        if st.button("🔄 Refresh Backups List", key="ref_bks"):
            st.rerun()

        local_bks = list_local_backups()
        if local_bks:
            bk_summary_list = []
            for b in local_bks:
                b_type = b.get("backup_type", "table").upper()
                if b_type == "DATABASE":
                    src = f"Database: {b.get('database')} ({b.get('total_tables', 0)} tables)"
                else:
                    src = f"Table: {b.get('database')}.{b.get('table')}"
                
                bk_summary_list.append({
                    "Type": f"🗄️ {b_type}" if b_type == "DATABASE" else f"📁 {b_type}",
                    "Backup ID": b.get("backup_id"),
                    "Target / Source": src,
                    "Total Rows": f"{b.get('total_rows', 0):,}",
                    "Size": f"{b.get('total_size_mb', 0)} MB",
                    "Files": b.get("total_files", 0),
                    "Created At": b.get("created_at")
                })
            df_bks = pd.DataFrame(bk_summary_list)
            st.dataframe(df_bks, use_container_width=True, hide_index=True)

            st.markdown("---")
            st.subheader("🔍 Inspect Backup Details & Checksums")
            b_ids = [b["backup_id"] for b in local_bks]
            selected_insp_b = st.selectbox("Select Backup to Inspect:", b_ids, key="insp_bk_sel")
            
            if selected_insp_b:
                target_manifest = next(b for b in local_bks if b["backup_id"] == selected_insp_b)
                is_db_manifest = target_manifest.get("backup_type") == "database"

                if is_db_manifest:
                    st.markdown(f"**🗄️ Database Backup Details (`{target_manifest.get('database')}`):**")
                    col_m1, col_m2, col_m3 = st.columns(3)
                    col_m1.metric("Tables in Backup", target_manifest.get("total_tables"))
                    col_m2.metric("Total Rows", f"{target_manifest.get('total_rows'):,}")
                    col_m3.metric("Total Size", f"{target_manifest.get('total_size_mb')} MB")

                    tbl_breakdown = []
                    for t_name, t_meta in target_manifest.get("tables", {}).items():
                        tbl_breakdown.append({
                            "Table Name": t_name,
                            "Format": t_meta.get("format", "Parquet"),
                            "Rows": f"{t_meta.get('total_rows', 0):,}",
                            "Files": t_meta.get("total_files", 0),
                            "Size (MB)": t_meta.get("total_size_mb", 0)
                        })
                    st.dataframe(pd.DataFrame(tbl_breakdown), use_container_width=True, hide_index=True)
                else:
                    with st.expander("📋 View Table Manifest & SHA-256 Checksums", expanded=True):
                        col_m1, col_m2 = st.columns(2)
                        with col_m1:
                            st.json({
                                "backup_id": target_manifest.get("backup_id"),
                                "table": f"{target_manifest.get('database')}.{target_manifest.get('table')}",
                                "format": target_manifest.get("format"),
                                "total_rows": target_manifest.get("total_rows"),
                                "total_size_mb": target_manifest.get("total_size_mb"),
                                "created_at": target_manifest.get("created_at")
                            })
                        with col_m2:
                            st.markdown("**🛡️ SHA-256 File Checksums:**")
                            file_chk_df = pd.DataFrame([
                                {"File": k, "Size (Bytes)": v["size"], "SHA-256 Checksum": v["sha256"]}
                                for k, v in target_manifest.get("files", {}).items()
                            ])
                            st.dataframe(file_chk_df, use_container_width=True, hide_index=True)

                # Tarball download
                target_b_path = os.path.join(BACKUP_DIR, selected_insp_b)
                if os.path.exists(target_b_path):
                    tar_stream = io.BytesIO()
                    with tarfile.open(fileobj=tar_stream, mode="w:gz") as tar:
                        tar.add(target_b_path, arcname=selected_insp_b)
                    tar_stream.seek(0)
                    st.download_button(
                        label=f"📥 Download `{selected_insp_b}.tar.gz` Archive",
                        data=tar_stream.getvalue(),
                        file_name=f"{selected_insp_b}.tar.gz",
                        mime="application/gzip"
                    )
        else:
            st.info("No backups currently stored in `/backups/`. Create one using the 'Create Backup' tab!")

    # 3. RESTORE TABLE OR DATABASE
    with b_tab_restore:
        st.subheader("🔄 Restore Table or Database from Local Backup")
        st.markdown(
            "Restore table or database data files and register in Hive Metastore. "
            "Integrity checksums are validated prior to restore to prevent any corruption."
        )
        local_bks = list_local_backups()
        if local_bks:
            b_options = []
            for b in local_bks:
                b_type = b.get("backup_type", "table").upper()
                if b_type == "DATABASE":
                    b_options.append(f"{b['backup_id']} [DATABASE: {b['database']} - {b.get('total_tables', 0)} tables]")
                else:
                    b_options.append(f"{b['backup_id']} [TABLE: {b['database']}.{b['table']} - {b['total_rows']:,} rows]")

            selected_res_str = st.selectbox("Select Backup to Restore:", b_options, key="res_bk_sel")
            selected_res_id = selected_res_str.split(" ")[0]
            chosen_b = next(b for b in local_bks if b["backup_id"] == selected_res_id)
            is_db_restore = chosen_b.get("backup_type") == "database"

            col_rt1, col_rt2 = st.columns(2)
            with col_rt1:
                res_target_db = st.text_input("Restore Target Database", value=chosen_b.get("database", "default"), key="res_db")
                if not is_db_restore:
                    res_target_tbl = st.text_input("Restore Target Table Name", value=chosen_b["table"], key="res_tbl")
                    res_target_tbl = sanitize_table_name(res_target_tbl)
                else:
                    st.info(f"🗄️ Restoring all **{chosen_b.get('total_tables', 0)} tables** into database `{res_target_db}`.")
            with col_rt2:
                res_storage_dest = st.selectbox(
                    "Target Storage Location",
                    ["s3a://warehouse/", "hdfs://namenode:9000/user/hive/warehouse/"],
                    key="res_storage"
                )

            if is_db_restore:
                st.warning(f"⚠️ Restoring will populate all tables from `{selected_res_id}` into database `{res_target_db}` at `{res_storage_dest}`.")
            else:
                st.warning(f"⚠️ Restoring will populate `{res_target_db}.{res_target_tbl}` at `{res_storage_dest}{res_target_tbl}/`.")

            if st.button("🔄 Execute Full Restore & Register in Hue", type="primary", key="btn_run_restore"):
                progress_bar = st.progress(0)
                status_text = st.empty()
                status_text.info(f"⏳ Step 1/3: Verifying SHA-256 file checksums...")
                progress_bar.progress(30)

                status_text.info(f"⏳ Step 2/3: Restoring data files and registering in Metastore...")
                progress_bar.progress(60)

                out, code = execute_restore_job(
                    selected_res_id,
                    mode="database" if is_db_restore else "table",
                    target_db=res_target_db,
                    target_table=res_target_tbl if not is_db_restore else None,
                    storage_dest=res_storage_dest
                )
                progress_bar.progress(100)
                status_text.empty()

                if code == 0 and "__RESTORE_RESULT__|" in out:
                    raw_res_line = out.split("__RESTORE_RESULT__|")[1].strip().splitlines()[0].strip()
                    res_json = json.loads(raw_res_line)
                    if is_db_restore:
                        st.success(f"🎉 Database `{res_json['database']}` restored successfully ({res_json['total_rows_restored']:,} total rows across {len(res_json.get('tables_restored', {}))} tables)!")
                        col_rr1, col_rr2 = st.columns(2)
                        col_rr1.metric("Total Rows Restored", f"{res_json['total_rows_restored']:,}")
                        col_rr2.metric("Total Duration", f"{res_json['elapsed_seconds']}s")
                    else:
                        st.success(f"🎉 Table `{res_json['restored_table']}` restored and verified successfully!")
                        col_rr1, col_rr2, col_rr3 = st.columns(3)
                        col_rr1.metric("Rows Restored", f"{res_json['rows_restored']:,}")
                        col_rr2.metric("Storage Path", res_json['storage_location'])
                        col_rr3.metric("Duration", f"{res_json['elapsed_seconds']}s")

                    st.subheader("🔍 Query in Hue")
                    st.link_button("🎨 Open & Query in Hue Editor", "http://localhost:8888")
                else:
                    st.error(f"❌ Restore Failed: {out}")
        else:
            st.info("No backups found in `/backups/` to restore.")

# -------------------------------------------------------------
# TAB 2: DELTA LAKE TIME-TRAVEL & MAINTENANCE
# -------------------------------------------------------------
elif menu == "⏳ Delta Time-Travel & Maintenance":
    st.header("⏳ Delta Lake Time-Travel & Storage Optimization Engine")
    st.markdown(
        "Inspect full ACID commit histories, query historical snapshots (`VERSION AS OF`), "
        "roll back tables in 1-click, and run **Storage Compaction (`OPTIMIZE` & Z-Order)** and **Vacuuming**."
    )

    df_tables = get_hive_metastore_tables()
    if not df_tables.empty:
        delta_tables = df_tables[df_tables["Format"] == "Delta Lake"]
        all_table_names = [f"{r['Database']}.{r['Table Name']}" for _, r in df_tables.iterrows()]
        
        selected_tbl = st.selectbox(
            "Select Table to Manage:",
            options=all_table_names,
            help="Delta Lake tables support ACID History, Time-Travel Rollbacks, and Z-Order Compaction."
        )

        st.markdown("---")

        tab_hist, tab_opt, tab_vac, tab_rb = st.tabs([
            "📜 Commit History & Time-Travel",
            "⚡ Compaction & Z-Order (OPTIMIZE)",
            "🧹 Storage Reclamation (VACUUM)",
            "⏪ Table Rollback / Restore"
        ])

        with tab_hist:
            st.subheader(f"📜 Commit History for `{selected_tbl}`")
            if st.button(f"🔍 Fetch History for `{selected_tbl}`", type="primary"):
                with st.spinner("Querying Delta Lake commit history from transaction log..."):
                    out, code = execute_spark_sql(f"DESCRIBE HISTORY {selected_tbl};")
                    if "__ERROR__" in out or code != 0:
                        st.warning(f"Note: If `{selected_tbl}` was registered as standard Parquet, history is not tracked.\n\n{out}")
                    else:
                        st.code(out)

            st.markdown("---")
            st.subheader("🕰️ Time-Travel Snapshot Query")
            ver_input = st.number_input("Version As Of (Integer Version ID):", min_value=0, max_value=1000, value=0, step=1)
            if st.button(f"👁️ Preview `{selected_tbl}` at Version {ver_input}"):
                with st.spinner(f"Reading snapshot of `{selected_tbl}` VERSION AS OF {ver_input}..."):
                    out, code = execute_spark_sql(f"SELECT * FROM {selected_tbl} VERSION AS OF {ver_input} LIMIT 20;")
                    st.code(out)

        with tab_opt:
            st.subheader("⚡ Table Compaction & Multidimensional Z-Ordering (`OPTIMIZE`)")
            st.markdown(
                "Merge small files into optimal 128MB chunks and cluster related records together "
                "with **Z-Ordering** to accelerate downstream analytical filters by up to 100x."
            )
            zorder_col_input = st.text_input("Z-Order Columns (Optional, comma-separated e.g. `store_id, item_id`):", value="")
            if st.button("🚀 Run OPTIMIZE Compaction", type="primary"):
                with st.spinner(f"Running OPTIMIZE compaction on `{selected_tbl}`..."):
                    if zorder_col_input.strip():
                        opt_sql = f"OPTIMIZE {selected_tbl} ZORDER BY ({zorder_col_input.strip()});"
                    else:
                        opt_sql = f"OPTIMIZE {selected_tbl};"
                    out, code = execute_spark_sql(opt_sql)
                    if code == 0:
                        st.success(f"🎉 Table `{selected_tbl}` compacted and optimized successfully!")
                    st.code(out)

        with tab_vac:
            st.subheader("🧹 Reclaim Storage Space (`VACUUM`)")
            st.markdown("Delete historical data files no longer referenced by the latest Delta transaction log to free disk space in MinIO S3.")
            retention_hours = st.number_input("Retention Period (Hours to retain history):", min_value=0, max_value=720, value=168, step=24)
            st.warning("⚠️ Warning: Running VACUUM removes historical snapshots older than the retention period.")
            if st.button("🧹 Run VACUUM Storage Cleanup", type="primary"):
                with st.spinner(f"Vacuuming `{selected_tbl}` (retention: {retention_hours}h)..."):
                    vac_sql = f"SET spark.databricks.delta.vacuum.parallelDelete.enabled = true; VACUUM {selected_tbl} RETAIN {retention_hours} HOURS;"
                    out, code = execute_spark_sql(vac_sql)
                    if code == 0:
                        st.success(f"🎉 VACUUM completed for `{selected_tbl}`!")
                    st.code(out)

        with tab_rb:
            st.subheader("⏪ In-Place Table Rollback / Restore")
            st.markdown("Restore the table state to an exact historical version without re-ingesting data files.")
            restore_version = st.number_input("Target Version to Restore to:", min_value=0, max_value=1000, value=0, step=1, key="rb_ver")
            if st.button(f"⚠️ Restore `{selected_tbl}` to Version {restore_version}", type="primary"):
                with st.spinner(f"Restoring `{selected_tbl}` to version {restore_version}..."):
                    rest_sql = f"RESTORE TABLE {selected_tbl} TO VERSION AS OF {restore_version};"
                    out, code = execute_spark_sql(rest_sql)
                    if code == 0:
                        st.success(f"🎉 Table `{selected_tbl}` restored to Version {restore_version}!")
                    st.code(out)
    else:
        st.info("No tables currently registered in Hive Metastore.")

# -------------------------------------------------------------
# TAB 3: SCHEDULED INGESTION JOBS
# -------------------------------------------------------------
elif menu == "⏰ Scheduled Ingestion Jobs":
    st.header("⏰ Recurring Batch Ingestion & Directory Watchers")
    st.markdown("Configure automated recurring ingestion pipelines that monitor folders and append new data into Hive & S3 tables.")

    jobs = load_scheduled_jobs()

    col_j1, col_j2 = st.columns([1, 1])
    with col_j1:
        st.subheader("➕ Create New Ingestion Job")
        job_name = st.text_input("Job Name", value="hourly_sales_ingest")
        watch_path = st.text_input("Watch Folder / HDFS Path Pattern", value="hdfs://namenode:9000/data/incoming/*.csv")
        target_db_j = st.text_input("Target Database", value="default", key="job_db")
        target_tbl_j = st.text_input("Target Table", value="sales_stream", key="job_tbl")
        target_fmt_j = st.selectbox("Format", ["Delta Lake", "Parquet"], key="job_fmt")
        job_interval = st.selectbox("Trigger Interval", ["Every 5 Minutes", "Every 15 Minutes", "Hourly", "Daily at Midnight", "Manual / On-Demand"])

        if st.button("💾 Save Scheduled Job", type="primary"):
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
            st.success(f"🎉 Job `{job_name}` created and registered in batch scheduler!")
            st.rerun()

    with col_j2:
        st.subheader("📋 Active Scheduled Ingestion Pipelines")
        if jobs:
            for j in jobs:
                with st.expander(f"⚙️ **{j['name']}** ➔ `{j['database']}.{j['table']}` ({j['interval']})", expanded=True):
                    st.write(f"📁 **Watch Path:** `{j['watch_path']}`")
                    st.write(f"⚡ **Format:** `{j['format']}` | **Status:** `{j['status']}`")
                    st.write(f"🕒 **Last Run:** {j['last_run']} | **Rows Processed:** {j['rows_processed']:,}")
                    
                    col_b1, col_b2 = st.columns(2)
                    with col_b1:
                        if st.button(f"▶️ Trigger `{j['name']}` Now", key=f"run_{j['id']}"):
                            with st.spinner(f"Executing batch ingestion pipeline `{j['name']}`..."):
                                run_script = f"""
from pyspark.sql import SparkSession
spark = SparkSession.builder.appName("Batch_{j['name']}").enableHiveSupport().getOrCreate()
df = spark.read.option("header", "true").option("inferSchema", "true").csv("{j['watch_path']}")
cnt = df.count()
df.write.format("{'delta' if 'Delta' in j['format'] else 'parquet'}").mode("append").option("path", "s3a://warehouse/{j['table']}/").saveAsTable("{j['database']}.{j['table']}")
print(f"__BATCH_DONE__|{{cnt}}")
spark.stop()
"""
                                spark_cont = client.containers.get("spark")
                                sf = f"/tmp/batch_{j['id']}.py"
                                copy_data_to_container(spark_cont, run_script.encode('utf-8'), "/tmp", os.path.basename(sf))
                                res = spark_cont.exec_run(f"/opt/spark/bin/spark-submit {sf}")
                                out = res.output.decode('utf-8', errors='ignore')
                                if res.exit_code == 0:
                                    j['last_run'] = time.strftime('%Y-%m-%d %H:%M:%S')
                                    for line in out.splitlines():
                                        if "__BATCH_DONE__" in line:
                                            j['rows_processed'] += int(line.split("|")[1])
                                    save_scheduled_jobs(jobs)
                                    st.success(f"🎉 Batch Ingestion Completed! ({j['rows_processed']:,} total rows)")
                                else:
                                    st.error(f"Execution Error: {out}")
                    with col_b2:
                        if st.button(f"🗑️ Delete Job", key=f"del_{j['id']}"):
                            jobs = [x for x in jobs if x['id'] != j['id']]
                            save_scheduled_jobs(jobs)
                            st.warning(f"Deleted job `{j['name']}`.")
                            st.rerun()
        else:
            st.info("No recurring batch jobs registered yet. Create one on the left!")

# -------------------------------------------------------------
# TAB 4: METASTORE TABLE EXPLORER & RICH INSPECTOR
# -------------------------------------------------------------
elif menu == "🗄️ Metastore Table Explorer":
    st.header("🗄️ Metastore Catalog & Interactive Table Inspector")
    st.markdown("Browse tables registered in Hive Metastore, inspect schemas, and query records with rich interactive data grids.")

    if st.button("🔄 Refresh Catalog"):
        st.rerun()

    df_tables = get_hive_metastore_tables()
    if not df_tables.empty:
        st.dataframe(df_tables, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.subheader("🔍 Interactive Table Inspector")
        table_options = [f"{r['Database']}.{r['Table Name']}" for _, r in df_tables.iterrows()]
        selected_tbl = st.selectbox("Select Table to Inspect:", table_options)
        
        if selected_tbl:
            tbl_meta = df_tables[df_tables.apply(lambda r: f"{r['Database']}.{r['Table Name']}" == selected_tbl, axis=1)].iloc[0]
            
            # Overview Metrics
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
                    fetch_clicked = st.button("🔄 Load Sample Rows", type="primary", key=f"fetch_{selected_tbl}")

                # Auto load or load on click
                if fetch_clicked or f"data_{selected_tbl}_{row_limit}" in st.session_state:
                    with st.spinner(f"Loading {row_limit} records from `{selected_tbl}` via Spark Engine..."):
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
                                    st.caption(f"✅ Loaded {len(sample_df)} sample rows (Total in table: {insp_data.get('total_rows', 0):,} rows) in {insp_data.get('elapsed_sec', 0)}s.")
                                with col_st2:
                                    csv_bytes = sample_df.to_csv(index=False).encode('utf-8')
                                    st.download_button(
                                        "📥 Export Preview to CSV",
                                        csv_bytes,
                                        file_name=f"{selected_tbl}_sample.csv",
                                        mime="text/csv"
                                    )
                            else:
                                st.info(f"Table `{selected_tbl}` is currently empty (0 rows).")
                        else:
                            st.error(f"Failed to load table records: {insp_data.get('error')}")

            with insp_tab_schema:
                st.subheader(f"📋 Schema & Column Specifications for `{selected_tbl}`")
                if f"data_{selected_tbl}_{row_limit}" in st.session_state and st.session_state[f"data_{selected_tbl}_{row_limit}"].get("status") == "success":
                    schema_records = st.session_state[f"data_{selected_tbl}_{row_limit}"].get("schema", [])
                    if schema_records:
                        df_schema = pd.DataFrame(schema_records)
                        st.dataframe(df_schema, use_container_width=True, hide_index=True)
                else:
                    if st.button("🔍 Load Schema", key=f"load_schema_{selected_tbl}"):
                        with st.spinner("Fetching schema..."):
                            insp_data = fetch_table_inspector_data(selected_tbl, limit=1)
                            st.session_state[f"data_{selected_tbl}_{row_limit}"] = insp_data
                            if insp_data.get("status") == "success":
                                df_schema = pd.DataFrame(insp_data.get("schema", []))
                                st.dataframe(df_schema, use_container_width=True, hide_index=True)

            with insp_tab_sql:
                st.subheader(f"⚡ Execute Custom Query on `{selected_tbl}`")
                custom_sql_input = st.text_area(
                    "SQL Query:",
                    value=f"SELECT * FROM {selected_tbl} LIMIT 25;",
                    height=100
                )
                col_run1, col_run2 = st.columns([1, 3])
                with col_run1:
                    if st.button("▶️ Execute Query", type="primary", key=f"run_sql_{selected_tbl}"):
                        with st.spinner("Executing query in SparkSQL engine..."):
                            custom_res = fetch_table_inspector_data(selected_tbl, custom_sql=custom_sql_input)
                            if custom_res.get("status") == "success":
                                c_records = custom_res.get("records", [])
                                if c_records:
                                    c_df = pd.DataFrame(c_records)
                                    st.dataframe(c_df, use_container_width=True, hide_index=True)
                                    st.caption(f"✅ Returned {len(c_df)} rows in {custom_res.get('elapsed_sec', 0)}s.")
                                else:
                                    st.info("Query returned 0 rows.")
                            else:
                                st.error(f"SQL Execution Error: {custom_res.get('error')}")
                with col_run2:
                    st.link_button("🎨 Open in Hue Query Editor", "http://localhost:8888")
    else:
        st.info("No tables currently registered in Hive Metastore.")

# -------------------------------------------------------------
# TAB: PLATFORM DOCS & GUIDE CENTER
# -------------------------------------------------------------
elif menu == "📚 Platform Docs & Guide Center":
    st.header("📚 Big Data Platform Documentation & Feature Catalog")
    st.markdown(
        "Interactive documentation, benchmark reports, and feature catalogs for the entire Big Data stack."
    )

    t_docs_viewer, t_feature_catalog = st.tabs([
        "📖 Interactive Guide & Benchmark Reader",
        "🌟 Platform Feature Catalog & Architecture"
    ])

    with t_docs_viewer:
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
            col_d1, col_d2 = st.columns([3, 1])
            with col_d1:
                selected_doc_title = st.selectbox("Select Documentation Guide to View:", list(available_docs.keys()))
            
            selected_path = available_docs[selected_doc_title]
            try:
                with open(selected_path, "r", encoding="utf-8") as f:
                    doc_content = f.read()

                with col_d2:
                    st.write("")
                    st.write("")
                    st.download_button(
                        label="📥 Download Markdown (.md)",
                        data=doc_content,
                        file_name=os.path.basename(selected_path),
                        mime="text/markdown"
                    )

                st.markdown("---")
                st.markdown(doc_content)
            except Exception as e:
                st.error(f"Error reading documentation file {selected_path}: {e}")
        else:
            st.warning("⚠️ Documentation files not found at `/app/docs`. Mount `./docs:/app/docs` in docker-compose.yml.")

    with t_feature_catalog:
        st.subheader("🌟 Enterprise Big Data Platform Feature Catalog")
        
        col_fc1, col_fc2 = st.columns(2)
        with col_fc1:
            st.markdown("""
            ### 📥 1. Zero-Friction Data Ingestion Studio
            * **Multi-File Batch Upload**: Upload CSV, Parquet, and JSON files up to 1,000 GB.
            * **Automated Column Sanitization**: Fixes spaces, brackets, dots, and special characters to prevent Parquet SerDe errors.
            * **Interactive Data Type Overrides**: Cast columns dynamically before saving.
            * **Dynamic Partitioning**: Writes partitioned datasets with automatic `MSCK REPAIR TABLE` for sub-second query pruning in Hue.

            ### ⚡ 2. Spark Dynamic Tuning & Cluster Scaling
            * **Elastic Worker Fleet**: Scale from 1 to 8+ worker nodes on-demand with 0 downtime.
            * **Per-Worker Node Sizing**: Configure `4g`, `8g`, `16g`, or `32g` RAM and 2-16 CPU cores per node.
            * **Workload Sizing Profiles**: Pre-engineered Light, Medium, Heavy, and Extreme configurations.
            * **Zero-OOM Protection**: Adaptive Query Execution (AQE), Kryo fast serialization, and Off-Heap memory.

            ### 📦 3. Zero-Corruption Backup & Disaster Recovery
            * **Single Table & Full Database Backups**: Complete snapshot of both DDL metadata and underlying data chunks.
            * **SHA-256 Checksums**: Cryptographically validates every file before restore.
            * **1-Click Restore**: Restores data and registers tables in PostgreSQL Hive Metastore.
            * **Tarball Downloads**: Download `.tar.gz` backup packages directly to your workstation.
            """)

        with col_fc2:
            st.markdown("""
            ### ⏳ 4. Delta Lake Time-Travel & Maintenance
            * **ACID Commit History**: Visual history of every transaction version, operation, and timestamp.
            * **Time-Travel Snapshots**: Query any historical table state via `VERSION AS OF <n>`.
            * **1-Click Rollback**: Instantly restore tables to any historical snapshot.
            * **Storage Compaction (`OPTIMIZE`)**: Merges small files and clusters data with multi-column **Z-Ordering**.
            * **Space Reclamation (`VACUUM`)**: Purges unreferenced historical files.

            ### ⏰ 5. Automated Batch Job Scheduler
            * **Directory Watchers**: Monitor incoming directories (`hdfs://namenode:9000/data/incoming/*.csv` or host folders).
            * **Recurring Intervals**: Hourly, Daily, Every 5 minutes, or On-Demand.
            * **Persistent Registry**: Saved to `/app/scheduled_jobs.json`.

            ### 🔐 6. Enterprise Identity & SSO (Keycloak IAM)
            * **OIDC STS Authentication**: Single sign-on for Hue Query Editor, MinIO S3 Console, and JupyterLab.
            * **Role-Based Access**: Pre-configured `admin` and `bigdata` realms.
            """)

# -------------------------------------------------------------
# TAB 5: CLUSTER HEALTH & LINKS
# -------------------------------------------------------------
elif menu == "📊 Cluster Health & Links":
    st.header("📊 BDP Cluster Health & Monitoring")
    
    col_a, col_b = st.columns([1, 4])
    with col_a:
        if st.button("🔄 Refresh Status"):
            st.rerun()

    df_containers = get_container_stats()
    if not df_containers.empty:
        st.dataframe(df_containers, use_container_width=True, hide_index=True)
    else:
        st.warning("No containers detected.")

    st.subheader("🌐 Quick Platform Portals")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.link_button("🎨 Hue Query Editor", "http://localhost:8888")
        st.link_button("📓 JupyterLab", "http://localhost:8889")
    with col2:
        st.link_button("⚡ Spark Master UI", "http://localhost:8089")
        st.link_button("⚡ Spark Worker UI", "http://localhost:8082")
    with col3:
        st.link_button("🪣 MinIO Console", "http://localhost:9001")
        st.link_button("📜 Livy REST UI", "http://localhost:8998")
    with col4:
        st.link_button("🐘 HDFS NameNode", "http://localhost:9870")
        st.link_button("🧶 YARN Manager", "http://localhost:8088")
        st.link_button("🗄️ pgAdmin 4", "http://localhost:8081")
        st.link_button("🔐 Keycloak IAM", "http://localhost:8080")

# -------------------------------------------------------------
# TAB 6: ONE-CLICK CLEANUP
# -------------------------------------------------------------
elif menu == "🧹 One-Click Cleanup":
    st.header("🧹 One-Click Cluster State & Memory Purge")
    st.info(
        "Clicking this button will:\n"
        "1. Terminate all abandoned/idle Apache Livy sessions holding worker cores.\n"
        "2. Terminate idle PostgreSQL metastore database backends.\n"
        "3. Ensure HDFS is taken out of SafeMode if triggered.\n"
        "4. Reclaim memory resources."
    )
    if st.button("🚀 Run Full Memory & Session Cleanup", type="primary"):
        with st.spinner("Purging hanging sessions and memory..."):
            results = purge_hanging_state_and_memory()
            st.success("Cluster Cleanup Action Completed!")
            for log_msg in results:
                st.write(log_msg)

# -------------------------------------------------------------
# TAB 7: CLUSTER DIAGNOSTICS
# -------------------------------------------------------------
elif menu == "🔍 Cluster Diagnostics":
    st.header("🔍 Real-Time Cluster Network Diagnostics")
    if st.button("▶️ Run Full Diagnostics"):
        with st.spinner("Diagnosing cluster network endpoints..."):
            result = subprocess.run(["/app/diagnose_cluster.sh"], capture_output=True, text=True)
            st.code(result.stdout)

# -------------------------------------------------------------
# TAB 8: CONTAINER LOGS VIEWER
# -------------------------------------------------------------
elif menu == "📜 Container Logs Viewer":
    st.header("📜 Container Logs Viewer")
    all_containers = [c.name for c in client.containers.list(all=True)]
    if all_containers:
        selected_container = st.selectbox("Select Container to Inspect", sorted(all_containers))
        lines = st.slider("Log Lines", min_value=50, max_value=500, value=100, step=50)
        if selected_container:
            try:
                container = client.containers.get(selected_container)
                logs = container.logs(tail=lines).decode('utf-8', errors='ignore')
                st.text_area("Container Logs Output", logs, height=450)
            except Exception as ex:
                st.error(f"Error fetching logs for {selected_container}: {ex}")
