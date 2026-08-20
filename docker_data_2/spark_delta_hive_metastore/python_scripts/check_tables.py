from pyspark.sql import SparkSession

spark = SparkSession.builder \
    .appName("Check_All_Tables") \
    .enableHiveSupport() \
    .getOrCreate()

print("\n" + "="*70)
print("TABLES IN HIVE METASTORE:")
spark.sql("SHOW TABLES IN default").show(20, False)

if spark.catalog.tableExists("default.df_inv"):
    print("✅ Table 'default.df_inv' EXISTS!")
    cnt = spark.table("default.df_inv").count()
    print(f"--> ROW COUNT of default.df_inv: {cnt:,}")
    print("--> Sample Rows:")
    spark.table("default.df_inv").show(5, False)
    print("--> Table Detail:")
    spark.sql("DESCRIBE DETAIL default.df_inv").show(False)

spark.stop()
