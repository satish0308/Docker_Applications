from pyspark.sql import SparkSession
import time

spark = SparkSession.builder \
    .appName("Check_Dataset") \
    .master("spark://spark:7077") \
    .enableHiveSupport() \
    .getOrCreate()

print("\n" + "="*60)
print("TABLES IN HIVE METASTORE:")
spark.sql("SHOW TABLES").show()

if spark.catalog.tableExists("default.m5_sales_large"):
    df = spark.table("default.m5_sales_large")
    t0 = time.time()
    cnt = df.count()
    elapsed = time.time() - t0
    print(f"--> TABLE 'default.m5_sales_large' has {cnt:,} rows (Counted in {elapsed:.2f}s)")
    print("--> Schema:")
    df.printSchema()

spark.stop()
