import streamlit as st
import docker
import pandas as pd

st.set_page_config(page_title="BDP Admin Panel", layout="wide")
st.title("🚀 BDP Cluster Monitor")

# Connect to Docker
client = docker.from_env()

def check_service_health(container):
    if container.status != 'running':
        return "Down"
    
    # Check specifically for Resource Manager
    if container.name == 'resourcemanager':
        try:
            exit_code, output = container.exec_run("jps")
            if b"ResourceManager" in output:
                return "Healthy"
            return "Process Down"
        except:
            return "Error"
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

# Refresh button
if st.button("Refresh Status"):
    st.rerun()

df = get_container_stats()
st.table(df)

st.subheader("Service Navigation")
col1, col2, col3 = st.columns(3)
with col1:
    st.link_button("Hue", "http://localhost:8888")
    st.link_button("Jupyter", "http://localhost:8889")
with col2:
    st.link_button("MinIO Console", "http://localhost:9001")
    st.link_button("Spark UI", "http://localhost:8089")
with col3:
    st.link_button("pgAdmin", "http://localhost:8081")
    st.link_button("Namenode", "http://localhost:9870")

st.subheader("Container Logs")
selected_container = st.selectbox("Select Container", [c.name for c in client.containers.list()])
if selected_container:
    container = client.containers.get(selected_container)
    st.text_area("Logs (last 100 lines)", container.logs(tail=100).decode('utf-8', errors='ignore'), height=300)
