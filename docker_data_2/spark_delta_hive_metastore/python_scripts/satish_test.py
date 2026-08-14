from pyspark.sql import SparkSession

spark = SparkSession.builder \
    .appName("SatishTestS3") \
    .getOrCreate()

print("--> Reading data from HDFS DataNode...")
df = spark.read.option("header", "true").csv("hdfs://namenode:9000/data/breweries.csv")
print(f"--> Total rows read from HDFS: {df.count()}")
df.show(3)

print("--> Writing table satish_test to S3 / MinIO (s3a://warehouse/satish_test)...")
df.write.format("delta").mode("overwrite").option("path", "s3a://warehouse/satish_test").saveAsTable("default.satish_test")

print("--> Querying default.satish_test from Spark...")
spark.sql("SELECT id, name, city, state FROM default.satish_test LIMIT 5").show()
spark.stop()
