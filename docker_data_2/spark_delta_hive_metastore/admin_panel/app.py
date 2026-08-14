import streamlit as st
import docker
import pandas as pd
import subprocess
import urllib.request
import json
import gc

st.set_page_config(page_title="BDP Admin Panel", layout="wide", page_icon="🚀")
st.title("🚀 BDP Cluster Monitor & Diagnostics")

# Connect to Docker
try:
    client = docker.from_env()
except Exception as e:
    st.error(f"Failed to connect to Docker daemon: {e}")
    st.stop()

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "🧹 Quick Cleanup", "🔍 Diagnostics", "📜 Container Logs"])

def get_service_health(container):
    if container.status != 'running':
        return "❌ Down"
    
    # Check container health check state if defined
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
            "admin-panel", "hive-metastore-postgres", "pgadmin"
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
        res = pg_container.exec_run(f"sh -c '{sql_cmd}'")
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

with tab1:
    col_a, col_b = st.columns([1, 4])
    with col_a:
        if st.button("🔄 Refresh Dashboard"):
            st.rerun()
    with col_b:
        if st.button("🧹 Purge Hanging Sessions & Memory", type="primary"):
            with st.spinner("Clearing hanging sessions, database locks & memory..."):
                results = purge_hanging_state_and_memory()
                st.success("Cleanup completed!")
                for log_msg in results:
                    st.write(log_msg)

    df_containers = get_container_stats()
    if not df_containers.empty:
        st.dataframe(df_containers, use_container_width=True, hide_index=True)
    else:
        st.warning("No BDP cluster containers detected.")

    st.subheader("🌐 Quick Service Navigation")
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

with tab2:
    st.subheader("🧹 One-Click Cluster State & Memory Purge")
    st.info(
        "Clicking this button will:\n"
        "1. Terminate all abandoned/idle Apache Livy sessions holding worker cores.\n"
        "2. Terminate idle PostgreSQL metastore database backends.\n"
        "3. Ensure HDFS is taken out of SafeMode if triggered.\n"
        "4. Reclaim memory resources."
    )
    if st.button("🚀 Run Full Memory & Session Cleanup", key="tab2_cleanup_btn", type="primary"):
        with st.spinner("Purging hanging sessions and memory..."):
            results = purge_hanging_state_and_memory()
            st.success("Cluster Cleanup Action Completed!")
            for log_msg in results:
                st.write(log_msg)

with tab3:
    st.subheader("🔍 Real-Time Cluster Network Diagnostics")
    if st.button("▶️ Run Full Diagnostics"):
        with st.spinner("Diagnosing cluster network endpoints..."):
            result = subprocess.run(["/app/diagnose_cluster.sh"], capture_output=True, text=True)
            st.code(result.stdout)

with tab4:
    st.subheader("📜 Container Logs Viewer")
    all_containers = [c.name for c in client.containers.list(all=True)]
    if all_containers:
        selected_container = st.selectbox("Select Container to Inspect", sorted(all_containers))
        lines = st.slider("Log Lines", min_value=50, max_value=500, value=100, step=50)
        if selected_container:
            try:
                container = client.containers.get(selected_container)
                logs = container.logs(tail=lines).decode('utf-8', errors='ignore')
                st.text_area("Container Logs Output", logs, height=400)
            except Exception as ex:
                st.error(f"Error fetching logs for {selected_container}: {ex}")
