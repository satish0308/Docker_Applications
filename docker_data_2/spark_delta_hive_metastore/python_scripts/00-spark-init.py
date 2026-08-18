"""
PySpark Interactive Kernel Initialization Script
Automatically connects JupyterLab to Apache Spark, Hive Metastore & MinIO S3
"""
import sys
import os

print("⚡ [Auto-Init] Apache Spark (PySpark 3.5.2) & Hive Metastore session initializing...")

try:
    from pyspark.sql import SparkSession
    from pyspark.sql import functions as F

    spark = SparkSession.builder \
        .appName("JupyterLab_Interactive") \
        .config("spark.driver.memory", "2g") \
        .config("spark.executor.memory", "2g") \
        .config("spark.sql.shuffle.partitions", "16") \
        .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000") \
        .config("spark.hadoop.fs.s3a.access.key", "minioadmin") \
        .config("spark.hadoop.fs.s3a.secret.key", "minioadmin123") \
        .config("spark.hadoop.fs.s3a.path.style.access", "true") \
        .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false") \
        .config("spark.hadoop.fs.s3a.aws.credentials.provider", "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider") \
        .enableHiveSupport() \
        .getOrCreate()

    sc = spark.sparkContext
    print("✅ PySpark Session ready as `spark`!")
    print("✅ Spark Context ready as `sc`!")
    print("✅ Hive Metastore catalog & MinIO S3 connected.")
except Exception as e:
    print(f"⚠️ PySpark auto-initialization error: {e}")
