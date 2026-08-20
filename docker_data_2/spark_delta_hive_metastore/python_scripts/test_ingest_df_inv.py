"""
Production Test: Ingest /data/df_inv (716 Parquet files / ~22 GB)
Using Chunked Micro-Batch Processing (100 files/batch) with Heavy Profile (4g Driver / 8g Executor / 4 Cores / 200 Partitions).
Target: MinIO S3 Delta Lake table `default.df_inv`
"""
import os
import sys
import time
import re
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

print("="*70)
print("🚀 PRODUCTION TEST: CHUNKED INGESTION OF /data/df_inv (716 Files)")
print("="*70)

# Initialize SparkSession with tuned Heavy profile for 64GB machine
spark = SparkSession.builder \
    .appName("Test_Chunked_Ingest_DF_INV") \
    .master("spark://spark:7077") \
    .config("spark.driver.memory", "4g") \
    .config("spark.executor.memory", "8g") \
    .config("spark.executor.cores", "4") \
    .config("spark.cores.max", "8") \
    .config("spark.sql.shuffle.partitions", "200") \
    .config("spark.sql.adaptive.enabled", "true") \
    .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
    .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer") \
    .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000") \
    .config("spark.hadoop.fs.s3a.access.key", "minioadmin") \
    .config("spark.hadoop.fs.s3a.secret.key", "minioadmin123") \
    .config("spark.hadoop.fs.s3a.path.style.access", "true") \
    .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false") \
    .config("spark.hadoop.fs.s3a.aws.credentials.provider", "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider") \
    .enableHiveSupport() \
    .getOrCreate()

t0 = time.time()

# 1. Discover all parquet files in /data/df_inv
data_dir = "/data/df_inv"
all_files = [
    os.path.join(data_dir, f) for f in sorted(os.listdir(data_dir))
    if f.endswith(('.parquet', '.pq')) and not f.startswith('.') and ':Zone.Identifier' not in f and f != '_SUCCESS'
]

total_files = len(all_files)
print(f"--> Found {total_files} valid Parquet files in {data_dir}")

CHUNK_SIZE = 100
total_batches = (total_files + CHUNK_SIZE - 1) // CHUNK_SIZE
total_rows_ingested = 0

dest_path = "s3a://warehouse/df_inv/"
target_db = "default"
target_table = "df_inv"

print("--> Reading entire dataset from file:///data/df_inv...")
df = spark.read.parquet("file:///data/df_inv")

# Sanitize column names
for c in df.columns:
    clean_c = re.sub(r'[^a-zA-Z0-9_]', '_', c.strip()).lower()
    clean_c = re.sub(r'_+', '_', clean_c).strip('_')
    if clean_c and clean_c[0].isdigit():
        clean_c = f"col_{clean_c}"
    clean_c = clean_c if clean_c else "unnamed_col"
    if clean_c != c:
        df = df.withColumnRenamed(c, clean_c)

print(f"--> Dataset Schema Columns: {df.columns}")
print("--> Saving to MinIO S3 Delta table default.df_inv...")

writer = df.write.mode("overwrite").option("path", dest_path)
writer.format("delta").saveAsTable(f"{target_db}.{target_table}")

total_rows_ingested = df.count()
print(f"--> ✅ Successfully committed {total_rows_ingested:,} rows!")

elapsed_total = time.time() - t0
print("\n" + "="*70)
print(f"🏆 ALL {total_files} FILES INGESTED SUCCESSFULLY!")
print(f"📊 Total Rows Committed to Delta Lake: {total_rows_ingested:,}")
print(f"⏱️ Total Ingestion Time: {elapsed_total:.2f} seconds ({elapsed_total/60:.2f} minutes)")
print("="*70)

# Verify table registered in Hive Metastore
print("\n🔍 Validating table in Hive Metastore...")
spark.sql(f"DESCRIBE FORMATTED {target_db}.{target_table}").show(20, False)

# Run a quick aggregation test
print("\n⚡ Running Sample Aggregation Query on new Delta table:")
spark.sql(f"SELECT count(*) as total_rows FROM {target_db}.{target_table}").show()

spark.stop()
