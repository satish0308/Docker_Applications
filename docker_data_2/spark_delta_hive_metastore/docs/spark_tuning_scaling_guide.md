# ⚡ Enterprise Spark Dynamic Tuning & Cluster Scaling Suite

## 🌟 Executive Overview
As datasets grow into millions of rows and multi-gigabyte files, fixed Spark parameters often lead to memory exhaustion (`OutOfMemoryError`), garbage collection pauses, or compute bottlenecks. 

The **Dynamic Spark Parameter Tuning & Horizontal Scaling Engine** allows administrators to:
1. **🚀 Scale Worker Nodes Up / Down Elasticity**: Horizontally add or remove worker compute nodes (1 to 8+ workers) in 1-click without taking down the cluster.
2. **🎛️ Select Workload Sizing Profiles**: Choose from 4 pre-engineered profiles (Light, Medium, Heavy, Extreme) or define custom JVM memory, CPU cores, and shuffle partition counts.
3. **🛡️ Auto-Detect Dataset Sizing during Ingestion**: The Ingestion Studio automatically inspects uploaded file sizes and recommends the optimal Spark execution profile before running.
4. **⚡ Advanced Query Optimizations**: Built-in toggle support for **Adaptive Query Execution (AQE)**, **Dynamic Partition Coalescing**, **Off-Heap Memory**, and **Kryo Serialization**.

---

## 🖥️ Workload Sizing Profiles

| Profile | Target Dataset Size | Driver RAM | Executor RAM | Executor Cores | Max Cores | Shuffle Partitions | AQE | Use Case |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| 🟢 **Light** | `< 100 MB` | `1 GB` | `2 GB` | `1` | `2` | `8` | Off | Exploration, small CSVs, test jobs |
| 🟡 **Medium** | `100 MB - 1 GB` | `2 GB` | `4 GB` | `2` | `4` | `64` | On | Standard daily batches, partitioned tables |
| 🔴 **Heavy** | `1 GB - 10 GB` (`>10M rows`) | `4 GB` | `8 GB` | `4` | `8` | `200` | On | Large ETL, multi-table joins, wide schemas |
| 🚀 **Extreme** | `> 10 GB` (Multi-GB batches) | `8 GB` | `16 GB` | `8` | `16` | `400` | On | Petabyte scale, massive fan-outs, heavy shuffles |
| 🛠️ **Custom** | *Any* | User Defined | User Defined | User Defined | User Defined | User Defined | Configurable | Exact hardware & workload tailoring |

---

## 🎛️ How to Use in Web Studio (`http://localhost:8501`)

### 1. 🚀 Scaling Cluster Compute Nodes
1. Open **[http://localhost:8501](http://localhost:8501)** and navigate to **"⚡ Spark Tuning & Cluster Scaling"**.
2. Under **"🖥️ Cluster Compute & Worker Scaling"**, view live cluster metrics (Active Workers, Total CPU Cores, Total Cluster RAM).
3. Adjust the **"Target Worker Count"** slider (e.g. from 1 to 3 workers).
4. Click **"🚀 Apply Worker Scale"**.
   - Docker dynamically starts additional worker nodes.
   - Workers automatically register at `spark://spark:7077`.
   - Cores and Memory instantly scale up (e.g. 3 workers = 12 Cores, 12 GB RAM).

### 2. ⚙️ Sizing & Tuning Spark Engine Defaults
1. Under **"⚙️ Workload Sizing & Parameter Tuning"**, pick your workload profile (e.g. `🔴 Heavy`).
2. Review or tweak:
   - **Driver Memory** (`spark.driver.memory`)
   - **Executor Memory** (`spark.executor.memory`)
   - **Cores per Executor** (`spark.executor.cores`)
   - **Shuffle Partitions** (`spark.sql.shuffle.partitions`)
   - **Adaptive Query Execution (AQE)**
   - **Off-Heap Memory** & **Kryo Serialization**
3. Click **"💾 Apply & Save Tuning Profile as Cluster Default"**.

### 3. 📥 Dataset Ingestion Auto-Sizing
1. Go to **"📥 Data Ingestion & Partitioning"**.
2. Upload your dataset or specify a path.
3. The platform **automatically calculates total file size and recommends the optimal profile** in the *⚡ Spark Execution Sizing & Compute Tuning* expander.
4. Click **"🚀 Ingest & Register Table in Hue"**—Spark will execute with your chosen sizing parameters dynamically!

---

## 💻 CLI & Docker Operations

```bash
# 1. Scale cluster to 3 worker nodes
docker compose up -d --scale spark-worker=3

# 2. Check live Spark cluster capacity
curl -s http://localhost:8089/json/ | jq '{workers: .aliveworkers, cores: .cores, memory_mb: .memory}'

# 3. Submit custom heavy job with dynamic tuning parameters
docker exec spark /opt/spark/bin/spark-submit \
  --driver-memory 4g \
  --executor-memory 8g \
  --conf spark.executor.cores=4 \
  --conf spark.cores.max=8 \
  --conf spark.sql.shuffle.partitions=200 \
  --conf spark.sql.adaptive.enabled=true \
  --conf spark.serializer=org.apache.spark.serializer.KryoSerializer \
  /app/python_scripts/my_large_job.py
```
