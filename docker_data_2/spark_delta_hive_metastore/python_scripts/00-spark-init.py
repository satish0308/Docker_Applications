"""
PySpark Interactive Kernel Initialization Script
Automatically connects JupyterLab to Apache Spark, Hive Metastore & MinIO S3
Dynamically loads active cluster tuning profile saved in Admin Panel Studio.
"""
import sys
import os
import json

print("⚡ [Auto-Init] Apache Spark (PySpark 3.5.2) & Hive Metastore session initializing...")

# Add directories to search path
sys.path.append("/home/jovyan/work")
sys.path.append("/opt/spark/scripts")

# Load active cluster tuning profile
tuning_params = {}
config_paths = [
    "/home/jovyan/work/spark_tuning_config.json",
    "/opt/spark/scripts/spark_tuning_config.json",
    "/app/spark_tuning_config.json"
]

for cp in config_paths:
    if os.path.exists(cp):
        try:
            with open(cp, "r") as f:
                cfg = json.load(f)
                tuning_params = cfg.get("params", {})
                if tuning_params:
                    print(f"⚡ [Auto-Init] Loaded Active Spark Tuning Profile: {cfg.get('active_profile', 'Custom')}")
                    break
        except Exception:
            pass

# Fallback defaults if no profile JSON is found
driver_mem = tuning_params.get("driver_memory", "4g")
exec_mem = tuning_params.get("executor_memory", "8g")
exec_cores = str(tuning_params.get("executor_cores", 4))
max_cores = str(tuning_params.get("max_cores", 8))
shuffle_parts = str(tuning_params.get("shuffle_partitions", 200))
aqe = "true" if tuning_params.get("aqe_enabled", True) else "false"
aqe_coal = "true" if tuning_params.get("aqe_coalesce", True) else "false"
mem_frac = str(tuning_params.get("memory_fraction", 0.8))
kryo = tuning_params.get("kryo_serializer", True)
offheap = tuning_params.get("offheap_enabled", True)
offheap_sz = tuning_params.get("offheap_size", "1g")

try:
    from pyspark.sql import SparkSession
    from pyspark.sql import functions as F

    builder = SparkSession.builder \
        .appName("JupyterLab_Interactive") \
        .master("spark://spark:7077") \
        .config("spark.driver.host", "jupyter-notebook") \
        .config("spark.driver.memory", driver_mem) \
        .config("spark.executor.memory", exec_mem) \
        .config("spark.executor.cores", exec_cores) \
        .config("spark.cores.max", max_cores) \
        .config("spark.sql.shuffle.partitions", shuffle_parts) \
        .config("spark.sql.adaptive.enabled", aqe) \
        .config("spark.sql.adaptive.coalescePartitions.enabled", aqe_coal) \
        .config("spark.memory.fraction", mem_frac) \
        .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000") \
        .config("spark.hadoop.fs.s3a.access.key", "minioadmin") \
        .config("spark.hadoop.fs.s3a.secret.key", "minioadmin123") \
        .config("spark.hadoop.fs.s3a.path.style.access", "true") \
        .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false") \
        .config("spark.hadoop.fs.s3a.aws.credentials.provider", "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider") \
        .enableHiveSupport()

    if kryo:
        builder = builder.config("spark.serializer", "org.apache.spark.serializer.KryoSerializer")
    if offheap and offheap_sz != "0":
        builder = builder.config("spark.memory.offHeap.enabled", "true") \
                         .config("spark.memory.offHeap.size", offheap_sz)

    spark = builder.getOrCreate()

    sc = spark.sparkContext
    print(f"✅ PySpark Session ready as `spark` on Master: {sc.master}!")
    print(f"✅ Active Resources: Driver {driver_mem} | Executor {exec_mem} ({exec_cores} Cores) | {shuffle_parts} Shuffle Partitions | Kryo: {kryo}")
    print("✅ Hive Metastore catalog & MinIO S3 connected.")
except Exception as e:
    print(f"⚠️ PySpark auto-initialization error: {e}")
