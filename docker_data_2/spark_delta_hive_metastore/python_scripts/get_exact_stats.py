from pyspark.sql import SparkSession
import time

spark = SparkSession.builder \
    .appName("Get_Exact_Stats") \
    .enableHiveSupport() \
    .getOrCreate()

t0 = time.time()
df = spark.table("default.df_inv")
cnt = df.count()
elapsed = time.time() - t0

print("\n" + "="*70)
print(f"📊 EXACT ROW COUNT of 'default.df_inv': {cnt:,} rows")
print(f"⏱️ Scan Elapsed Time: {elapsed:.2f} seconds")
print(f"📁 Storage Path: s3a://warehouse/df_inv/")
print("="*70)

spark.stop()
