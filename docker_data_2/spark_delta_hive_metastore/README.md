# 🚀 Big Data Platform (BDP) Sandbox

This project provides a comprehensive, Docker-based Big Data environment, merging features from the classic Hadoop/Spark stack with modern integrations like Delta Lake, MinIO (S3-compatible object store), and an interactive JupyterHub notebook environment.

---

## 📦 Components

- **Hadoop Ecosystem**: HDFS (Namenode/Datanode), YARN (ResourceManager/NodeManager).
- **Compute Engine**: Custom Spark 3.5.2 engine with Delta Lake 3.2.0, AWS SDK, and Postgres JDBC drivers.
- **Metastore**: Hive Metastore backed by PostgreSQL, with pgAdmin for management.
- **Visualizer**: Hue for HDFS exploration and SQL query editing.
- **Storage**: MinIO for S3-compatible data lake storage.
- **Interactive**: JupyterLab notebook environment pre-configured with Spark and MinIO connectivity.

---

## 🚀 Getting Started

1.  **Bring up the infrastructure**:
    ```bash
    # Navigate to the directory
    cd docker_data_2/spark_delta_hive_metastore/
    
    # Start the services
    docker-compose up -d
    ```

2.  **Accessing Services**:
    - **⚡ Admin Web Studio**: `http://localhost:8501` (Data Ingestion, Backup/Restore, Spark Tuning & Scaling)
    - **Hue Query Editor**: `http://localhost:8888`
    - **JupyterLab**: `http://localhost:8889`
    - **MinIO S3 Console**: `http://localhost:9001` (login: `minioadmin` / `minioadmin123`)
    - **Keycloak IAM (SSO)**: `http://localhost:8080` (login: `admin` / `admin`)
    - **Spark Master UI**: `http://localhost:8089` (or `http://localhost:8080`)
    - **pgAdmin 4**: `http://localhost:8081`
    - **HDFS Namenode**: `http://localhost:9870`
    - **YARN ResourceManager**: `http://localhost:8088`

---

## 📚 Platform Guides & Documentation

All comprehensive enterprise guides are available under the **[`docs/`](docs/)** directory:

- ⚡ **[Spark Dynamic Tuning & Horizontal Cluster Scaling Guide](docs/spark_tuning_scaling_guide.md)**: Dynamic workload sizing profiles (Light, Medium, Heavy, Extreme), OOM prevention, and horizontal worker node scaling (`docker compose up -d --scale spark-worker=N`).
- 📦 **[Table & Full Database Disaster Recovery Guide](docs/table_backup_restore_guide.md)**: Bit-for-bit verified table and database backups with cryptographic SHA-256 checksums and 1-click restore.
- 🚀 **[Production Data Pipeline & Delta Performance Guide](docs/data_pipeline_delta_guide.md)**: Dynamic Partitioning, Delta Lake Time-Travel, `OPTIMIZE` / `VACUUM` compaction, and Scheduled Directory Watchers.

---

## ⚙️ Connectivity

### Connecting Jupyter to Spark
In your JupyterLab notebook, the `spark` and `sc` sessions are **automatically initialized upon opening any notebook**! You can also connect manually with:

```python
from pyspark.sql import SparkSession

spark = SparkSession.builder \
    .appName("BDP Jupyter Session") \
    .enableHiveSupport() \
    .getOrCreate()
```

### Connecting Jupyter to MinIO (S3)
To query data stored in MinIO:

```python
spark = SparkSession.builder \
    .appName("BDP MinIO Connection") \
    .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000") \
    .config("spark.hadoop.fs.s3a.access.key", "minioadmin") \
    .config("spark.hadoop.fs.s3a.secret.key", "minioadmin123") \
    .config("spark.hadoop.fs.s3a.path.style.access", "true") \
    .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false") \
    .config("spark.hadoop.fs.s3a.aws.credentials.provider", "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider") \
    .getOrCreate()
```
