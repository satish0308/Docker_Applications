import streamlit as st
import docker
import pandas as pd

st.set_page_config(page_title="BDP Admin Panel", layout="wide")
st.title("🚀 BDP Cluster Monitor")

# Connect to Docker
client = docker.from_env()

def get_container_stats():
    containers = client.containers.list(all=True)
    data = []
    for c in containers:
        try:
            stats = c.stats(stream=False)
            mem_usage = stats.get('memory_stats', {}).get('usage', 0)
            mem_limit = stats.get('memory_stats', {}).get('limit', 1)
            mem_perc = (mem_usage / mem_limit) * 100 if mem_limit > 0 else 0
            image = c.image.tags[0] if c.image.tags else "N/A"
        except (docker.errors.APIError, docker.errors.ImageNotFound):
            mem_perc = 0
            image = "Unknown/Error"
        
        data.append({
            "Name": c.name,
            "Status": c.status,
            "Image": image,
            "Memory %": round(mem_perc, 2)
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
    st.link_button("MinIO", "http://localhost:9001")
    st.link_button("Spark UI", "http://localhost:8080")
with col3:
    st.link_button("pgAdmin", "http://localhost:8081")
    st.link_button("Namenode", "http://localhost:9870")

st.subheader("Container Logs")
selected_container = st.selectbox("Select Container", [c.name for c in client.containers.list()])
if selected_container:
    container = client.containers.get(selected_container)
    st.text_area("Logs (last 100 lines)", container.logs(tail=100).decode('utf-8'), height=300)
