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
import psycopg2

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
    name = re.sub(r'[^a-zA-Z0-9_]', '_', name.lower())
    if name and name[0].isdigit():
        name = f"tbl_{name}"
    return name.strip('_')

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
    except Exception as ex:
        # Fallback to empty if metastore unreachable
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
        "Upload a dataset file (or specify an HDFS / storage path) to automatically "
        "detect its schema, convert to optimized **Parquet / Delta Lake**, store in **MinIO S3 / HDFS**, "
        "and register as a queryable **External Table in Hue & Hive Metastore**."
    )

    source_type = st.radio(
        "Select Data Source:",
        ["📁 Upload Local File (CSV / Parquet / JSON / TSV)", "🐘 Select Existing File in HDFS / S3 Path"],
        horizontal=True
    )

    st.markdown("---")

    uploaded_file = None
    input_file_path = None
    file_format = "csv"
    df_preview = None
    base_table_name = "new_table"

    if "Upload Local File" in source_type:
        uploaded_file = st.file_uploader(
            "Drag and drop or browse a data file",
            type=["csv", "parquet", "pq", "json", "tsv", "txt"]
        )
        if uploaded_file is not None:
            filename = uploaded_file.name
            base_table_name = sanitize_table_name(os.path.splitext(filename)[0])
            
            # Detect format
            ext = filename.split(".")[-1].lower()
            if ext in ["parquet", "pq"]:
                file_format = "parquet"
                try:
                    df_preview = pd.read_parquet(uploaded_file)
                except Exception as e:
                    st.warning(f"Could not parse Parquet preview: {e}")
            elif ext == "json":
                file_format = "json"
                try:
                    df_preview = pd.read_json(uploaded_file, lines=True, nrows=50)
                except Exception:
                    uploaded_file.seek(0)
                    try:
                        df_preview = pd.read_json(uploaded_file, nrows=50)
                    except Exception:
                        pass
            elif ext in ["tsv", "txt"]:
                file_format = "csv"
                try:
                    df_preview = pd.read_csv(uploaded_file, sep="\t", nrows=50)
                except Exception:
                    uploaded_file.seek(0)
                    df_preview = pd.read_csv(uploaded_file, nrows=50)
            else:
                file_format = "csv"
                try:
                    df_preview = pd.read_csv(uploaded_file, nrows=50)
                except Exception as e:
                    st.warning(f"Could not parse CSV preview: {e}")
            
            uploaded_file.seek(0)

    else:
        hdfs_path_input = st.text_input(
            "Enter HDFS or Storage Path:",
            value="hdfs://namenode:9000/data/breweries.csv",
            help="Example: hdfs://namenode:9000/data/breweries.csv or /data/benchmark/sales.csv"
        )
        if hdfs_path_input:
            input_file_path = hdfs_path_input.strip()
            base_filename = os.path.basename(input_file_path)
            base_table_name = sanitize_table_name(os.path.splitext(base_filename)[0])
            if input_file_path.endswith(".parquet") or input_file_path.endswith(".pq"):
                file_format = "parquet"
            elif input_file_path.endswith(".json"):
                file_format = "json"
            else:
                file_format = "csv"

    # Preview Section
    if df_preview is not None:
        st.subheader("🔍 Dynamic Schema & Data Preview (First 50 Rows)")
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Columns Detected", len(df_preview.columns))
        col_m2.metric("Sample Rows Loaded", len(df_preview))
        col_m3.metric("Detected Format", file_format.upper())
        
        st.dataframe(df_preview.head(50), use_container_width=True)

        with st.expander("📋 Inferred Column Types"):
            dtypes_df = pd.DataFrame({
                "Column Name": df_preview.columns,
                "Inferred Python Type": [str(t) for t in df_preview.dtypes],
                "Non-Null Count": [f"{df_preview[c].count()} / {len(df_preview)}" for c in df_preview.columns]
            })
            st.dataframe(dtypes_df, use_container_width=True, hide_index=True)

    # Ingestion Configuration Form
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

    write_mode = st.radio("Write Mode", ["Overwrite (Replace existing table)", "Append (Add to existing data)"], horizontal=True)

    st.markdown("---")

    # Ingestion Action Button
    can_proceed = (uploaded_file is not None) or (input_file_path is not None)
    if not can_proceed:
        st.info("👆 Please upload a file or specify a valid HDFS path above to start ingestion.")
    
    if st.button("🚀 Ingest & Register Table in Hue", type="primary", disabled=not can_proceed):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            status_text.info("⏳ Step 1/4: Preparing staging files and cluster connection...")
            progress_bar.progress(20)
            
            # Determine HDFS staging path
            if uploaded_file is not None:
                staging_hdfs_path = f"/data/uploads/{uploaded_file.name}"
                namenode_cont = client.containers.get("namenode")
                namenode_cont.exec_run("hdfs dfs -mkdir -p /data/uploads")
                
                # Copy file into namenode /tmp directory via Docker SDK
                uploaded_file.seek(0)
                file_bytes = uploaded_file.read()
                copy_data_to_container(namenode_cont, file_bytes, "/tmp", uploaded_file.name)
                
                # Ingest to HDFS from container /tmp
                put_res = namenode_cont.exec_run(f"hdfs dfs -put -f /tmp/{uploaded_file.name} {staging_hdfs_path}")
                if put_res.exit_code != 0:
                    err_msg = put_res.output.decode('utf-8', errors='ignore') if put_res.output else "Unknown HDFS error"
                    raise Exception(f"Failed to stage file to HDFS: {err_msg}")
                
                source_path_for_spark = f"hdfs://namenode:9000{staging_hdfs_path}"
            else:
                source_path_for_spark = input_file_path

            status_text.info("⏳ Step 2/4: Generating dynamic PySpark ingestion script...")
            progress_bar.progress(40)

            # Determine storage path
            is_s3 = "MinIO" in storage_dest
            if is_s3:
                dest_path = f"s3a://warehouse/{target_table}/"
            else:
                dest_path = f"hdfs://namenode:9000/user/hive/warehouse/{target_table}/"

            save_mode = "overwrite" if "Overwrite" in write_mode else "append"
            is_delta = "Delta Lake" in output_format
            is_parquet = "Parquet" in output_format

            # Build PySpark Ingestion Script
            spark_script = f"""
import time
import re
from pyspark.sql import SparkSession

spark = SparkSession.builder \\
    .appName("UI_Ingestion_{target_table}") \\
    .config("spark.driver.memory", "2g") \\
    .config("spark.executor.memory", "3g") \\
    .enableHiveSupport() \\
    .getOrCreate()

t0 = time.time()
print("--> Reading source data from: {source_path_for_spark}")
"""
            if file_format == "csv":
                spark_script += f"""
df = spark.read \\
    .option("header", "true") \\
    .option("inferSchema", "true") \\
    .csv("{source_path_for_spark}")
"""
            elif file_format == "parquet":
                spark_script += f"""
df = spark.read.parquet("{source_path_for_spark}")
"""
            elif file_format == "json":
                spark_script += f"""
df = spark.read.json("{source_path_for_spark}")
"""

            spark_script += f"""
# Sanitize all column names for universal Hive, Parquet, and Hue SQL compatibility
for c in df.columns:
    clean_c = re.sub(r'[^a-zA-Z0-9_]', '_', c.strip()).lower()
    clean_c = re.sub(r'_+', '_', clean_c).strip('_')
    if clean_c and clean_c[0].isdigit():
        clean_c = f"col_{{clean_c}}"
    clean_c = clean_c if clean_c else "unnamed_col"
    if clean_c != c:
        df = df.withColumnRenamed(c, clean_c)

print(f"--> Normalized Columns: {{df.columns}}")
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

            # Parse results
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
