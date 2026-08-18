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

    # 3. Ensure HDFS Out of SafeMode
    try:
        nn_container = client.containers.get("namenode")
        res = nn_container.exec_run("hdfs dfsadmin -safemode leave")
        out = res.output.decode('utf-8').strip()
        logs.append(f"✅ HDFS SafeMode Status: {out}")
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

# Sidebar Navigation
st.sidebar.title("⚡ Big Data Studio & Engine")
menu = st.sidebar.radio(
    "Navigation Menu",
    [
        "📥 Data Ingestion & Partitioning",
        "⏳ Delta Time-Travel & Maintenance",
        "⏰ Scheduled Ingestion Jobs",
        "🗄️ Metastore Table Explorer",
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
    .config("spark.driver.memory", "2g") \\
    .config("spark.executor.memory", "3g") \\
    .config("spark.sql.shuffle.partitions", "16") \\
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

            res = spark_cont.exec_run(
                f"/opt/spark/bin/spark-submit --driver-memory 2g --executor-memory 3g /tmp/{script_filename}"
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
# TAB 4: METASTORE TABLE EXPLORER
# -------------------------------------------------------------
elif menu == "🗄️ Metastore Table Explorer":
    st.header("🗄️ Hive Metastore Catalog & Tables Explorer")
    st.markdown("Browse all persistent tables registered in Hive Metastore and query sample records.")

    if st.button("🔄 Refresh Catalog"):
        st.rerun()

    df_tables = get_hive_metastore_tables()
    if not df_tables.empty:
        st.dataframe(df_tables, use_container_width=True, hide_index=True)

        st.subheader("🔍 Interactive Table Inspector")
        table_options = [f"{r['Database']}.{r['Table Name']}" for _, r in df_tables.iterrows()]
        selected_tbl = st.selectbox("Select Table to Inspect:", table_options)
        
        if selected_tbl:
            col_q1, col_q2 = st.columns([1, 4])
            with col_q1:
                if st.button(f"👁️ Preview `{selected_tbl}` Data"):
                    with st.spinner(f"Reading sample rows from `{selected_tbl}`..."):
                        try:
                            spark_cont = client.containers.get("spark")
                            py_cmd = f"spark-sql -e 'SELECT * FROM {selected_tbl} LIMIT 20;'"
                            res = spark_cont.exec_run(py_cmd)
                            st.code(res.output.decode('utf-8', errors='ignore'))
                        except Exception as e:
                            st.error(f"Error querying table: {e}")
            with col_q2:
                st.link_button("🎨 Open & Query in Hue Editor", "http://localhost:8888")
    else:
        st.info("No tables currently registered in Hive Metastore.")

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
