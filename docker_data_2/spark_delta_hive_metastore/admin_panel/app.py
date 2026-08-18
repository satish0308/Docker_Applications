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
    page_title="BDP Data Studio & Cluster Manager",
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
            tables.append({
                "Database": r[0],
                "Table Name": r[1],
                "Table Type": r[2],
                "Storage Location": r[3],
                "Created At": str(r[4]) if r[4] else "N/A"
            })
        return pd.DataFrame(tables)
    except Exception:
        return pd.DataFrame()

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

# Sidebar Navigation
st.sidebar.title("⚡ Big Data Studio")
menu = st.sidebar.radio(
    "Navigation Menu",
    [
        "📥 Data Ingestion & Table Creator",
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
# TAB 1: DATA INGESTION & TABLE CREATOR
# -------------------------------------------------------------
if menu == "📥 Data Ingestion & Table Creator":
    st.header("📥 Ingest Files & Auto-Create Tables in Hue / Hive")
    st.markdown(
        "Upload multiple files (up to **10 GB** each) or point to host / HDFS datasets to automatically "
        "detect schemas, **override column data types**, convert to optimized **Parquet / Delta Lake**, "
        "and register as queryable **External Tables in Hue & Hive Metastore**."
    )

    source_type = st.radio(
        "Select Data Source Mode:",
        [
            "📁 Multi-File Browser Upload (CSV / Parquet / JSON / TSV up to 10GB)",
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
            help="Files up to 10 GB each are supported."
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

            ext_suffix = os.path.splitext(preview_file.name)[1]
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext_suffix) as tmp_f:
                tmp_f.write(data_bytes)
                tmp_path = tmp_f.name

            try:
                # 1. Try Parquet reading via pyarrow (supports all snappy, dictionary, multi-chunk Parquet files)
                if data_bytes.startswith(b'PAR1') or preview_file.name.lower().endswith(('.parquet', '.pq')):
                    try:
                        tbl = pq.read_table(tmp_path)
                        df_preview = tbl.to_pandas().head(50)
                        file_format = "parquet"
                    except Exception:
                        try:
                            df_preview = pd.read_parquet(tmp_path).head(50)
                            file_format = "parquet"
                        except Exception:
                            pass

                # 2. Try JSON
                if df_preview is None and (preview_file.name.lower().endswith('.json') or data_bytes.strip().startswith((b'{', b'['))):
                    try:
                        df_preview = pd.read_json(tmp_path, lines=True, nrows=50)
                        file_format = "json"
                    except Exception:
                        try:
                            df_preview = pd.read_json(tmp_path, nrows=50)
                            file_format = "json"
                        except Exception:
                            pass

                # 3. Fallback to CSV / TSV
                if df_preview is None:
                    file_format = "csv"
                    try:
                        if preview_file.name.lower().endswith(('.tsv', '.tab')):
                            df_preview = pd.read_csv(tmp_path, sep='\t', nrows=50)
                        else:
                            df_preview = pd.read_csv(tmp_path, nrows=50)
                    except Exception:
                        try:
                            df_preview = pd.read_csv(tmp_path, sep=None, engine='python', nrows=50)
                        except Exception as e:
                            st.warning(f"Could not parse preview: {e}")
            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)

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
    if df_preview is not None:
        st.subheader("🔍 Schema Preview & Column Data Type Overrides")
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Columns Detected", len(df_preview.columns))
        col_m2.metric("Sample Rows Loaded", len(df_preview))
        col_m3.metric("Detected File Format", file_format.upper())
        
        st.dataframe(df_preview.head(20), use_container_width=True)

        with st.expander("🛠️ Override Column Data Types (Optional)", expanded=True):
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

            # Build interactive type override grid in 3-4 columns
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
    # Target Table Configuration
    # ---------------------------------------------------------
    st.subheader("⚙️ Target Table & Storage Configuration")
    
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        target_db = st.text_input("Target Hive Database", value="default")
        target_table = st.text_input("Target Table Name", value=base_table_name)
        target_table = sanitize_table_name(target_table)
    
    with col_c2:
        output_format = st.selectbox(
            "Target Storage Format",
            ["Parquet (Universal - Recommended for Hive & Hue)", "Delta Lake (ACID & Time Travel)", "CSV Text"],
            index=0
        )
        storage_dest = st.selectbox(
            "Storage Destination",
            ["MinIO S3 Bucket (s3a://warehouse/)", "HDFS (hdfs://namenode:9000/user/hive/warehouse/)"],
            index=0
        )

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
                    
                    # Clean tmp file in namenode
                    namenode_cont.exec_run(f"rm -f /tmp/{ufile.name}")
                    staged_source_paths.append(f"hdfs://namenode:9000{staging_hdfs_path}")

            # 2. Process direct host / HDFS paths
            elif input_file_paths:
                for ipath in input_file_paths:
                    if ipath.startswith("hdfs://") or ipath.startswith("/data/"):
                        staged_source_paths.append(ipath if ipath.startswith("hdfs://") else f"hdfs://namenode:9000{ipath}")
                    elif os.path.exists(ipath):
                        # Local file on host - stream into HDFS
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

            status_text.info("⏳ Step 2/4: Generating dynamic PySpark schema and type casting script...")
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

print(f"--> Final Schema Columns: {{df.columns}}")
"""

            if is_delta:
                spark_script += f"""
df.write.format("delta").mode("{save_mode}") \\
    .option("path", "{dest_path}") \\
    .saveAsTable("{target_db}.{target_table}")
"""
            else:
                spark_script += f"""
df.write.mode("{save_mode}") \\
    .option("path", "{dest_path}") \\
    .saveAsTable("{target_db}.{target_table}")
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
# TAB 2: METASTORE TABLE EXPLORER
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
# TAB 3: CLUSTER HEALTH & LINKS
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
# TAB 4: ONE-CLICK CLEANUP
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
# TAB 5: CLUSTER DIAGNOSTICS
# -------------------------------------------------------------
elif menu == "🔍 Cluster Diagnostics":
    st.header("🔍 Real-Time Cluster Network Diagnostics")
    if st.button("▶️ Run Full Diagnostics"):
        with st.spinner("Diagnosing cluster network endpoints..."):
            result = subprocess.run(["/app/diagnose_cluster.sh"], capture_output=True, text=True)
            st.code(result.stdout)

# -------------------------------------------------------------
# TAB 6: CONTAINER LOGS VIEWER
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
