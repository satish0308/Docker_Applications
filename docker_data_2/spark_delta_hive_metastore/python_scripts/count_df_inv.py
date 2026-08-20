from pyspark.sql import SparkSession
import time

spark = SparkSession.builder \
    .appName("Count_DF_Inv") \
    .enableHiveSupport() \
    .getOrCreate()

t0 = time.time()
df = spark.table("default.df_inv")
cnt = df.count()
elapsed = time.time() - t0

print("\n" + "="*70)
print(f"📊 TABLE 'default.df_inv' ROW COUNT: {cnt:,} rows")
print(f"⏱️ Count Time: {elapsed:.2f}s")
print(f"📂 Location: s3a://warehouse/df_inv/")
print("="*70)
print("\nSample records:")
df.show(5, truncate=False)
spark.stop()
