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
    - **Hue**: `http://localhost:8888`
    - **JupyterLab**: `http://localhost:8889`
    - **MinIO Console**: `http://localhost:9001` (login: `minioadmin` / `minioadmin123`)
    - **Spark UI**: `http://localhost:8080`
    - **pgAdmin**: `http://localhost:8081`
    - **HDFS Namenode**: `http://localhost:9870`
    - **YARN ResourceManager**: `http://localhost:8088`

---

## ⚙️ Connectivity

### Connecting Jupyter to Spark
In your JupyterLab notebook, use the following `SparkSession` builder to connect to the Spark master:

```python
from pyspark.sql import SparkSession

spark = SparkSession.builder \
    .appName("BDP Jupyter Session") \
    .master("spark://spark:7077") \
    .config("spark.executor.memory", "2g") \
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
