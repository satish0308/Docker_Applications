import streamlit as st
import docker
import pandas as pd
import subprocess

st.set_page_config(page_title="BDP Admin Panel", layout="wide")
st.title("🚀 BDP Cluster Monitor")

# Connect to Docker
client = docker.from_env()

# Tabs
tab1, tab2, tab3 = st.tabs(["Dashboard", "Diagnostics", "Container Logs"])

with tab1:
    # Refresh button
    if st.button("Refresh Status"):
        st.rerun()

    def check_service_health(container):
        if container.status != 'running':
            return "Down"
        return "Running"

    def get_container_stats():
        containers = client.containers.list(all=True)
        data = []
        for c in containers:
            health = check_service_health(c)
            data.append({
                "Name": c.name,
                "Status": c.status,
                "Service Health": health
            })
        return pd.DataFrame(data)

    st.table(get_container_stats())

    st.subheader("Service Navigation")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.link_button("Hue", "http://localhost:8888")
        st.link_button("Jupyter", "http://localhost:8889")
    with col2:
        st.link_button("MinIO Console", "http://localhost:9001")
        st.link_button("Livy UI", "http://localhost:8998")
        st.link_button("Spark UI", "http://localhost:8089")
    with col3:
        st.link_button("pgAdmin", "http://localhost:8081")
        st.link_button("Namenode", "http://localhost:9870")

with tab2:
    st.subheader("Cluster Diagnostics")
    if st.button("Run Diagnostics"):
        result = subprocess.run(["/app/diagnose_cluster.sh"], capture_output=True, text=True)
        st.code(result.stdout)

with tab3:
    st.subheader("Container Logs")
    selected_container = st.selectbox("Select Container", [c.name for c in client.containers.list()])
    if selected_container:
        container = client.containers.get(selected_container)
        st.text_area("Logs (last 100 lines)", container.logs(tail=100).decode('utf-8', errors='ignore'), height=300)
