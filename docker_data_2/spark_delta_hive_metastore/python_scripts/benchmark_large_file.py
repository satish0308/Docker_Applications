import time
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

def main():
    print("==========================================================")
    print("🚀 STARTING 4.3 GB DATASET END-TO-END PROCESSING BENCHMARK")
    print("==========================================================")

    spark = SparkSession.builder \
        .appName("LargeScaleBenchmark_4GB") \
        .config("spark.driver.memory", "2g") \
        .config("spark.executor.memory", "3g") \
        .config("spark.sql.shuffle.partitions", "16") \
        .enableHiveSupport() \
        .getOrCreate()

    start_total = time.time()

    # Step 1: Read 4.3 GB CSV from HDFS dynamically
    print("\n[Step 1/4] Dynamically reading 4.3 GB CSV from HDFS DataNode...")
    t0 = time.time()
    df = spark.read \
        .option("header", "true") \
        .option("inferSchema", "true") \
        .csv("hdfs://namenode:9000/data/benchmark/sales_train_evaluation.csv")
    
    # Trigger an action to get row count and inspect schema
    row_count = df.count()
    t_read = time.time() - t0
    print(f"✅ Read complete in {t_read:.2f} seconds.")
    print(f"📊 Total Rows: {row_count:,}")
    print(f"📊 Total Columns: {len(df.columns)}")
    print(f"📋 Schema:")
    df.printSchema()
    print("\n🔍 Sample Data (Top 5 rows):")
    df.show(5)

    # Step 2: Write out to S3 (MinIO) as Parquet and register in Hive Metastore
    s3_path = "s3a://warehouse/m5_sales_large/"
    table_name = "default.m5_sales_large"
    print(f"\n[Step 2/4] Writing Parquet to S3/MinIO ({s3_path}) & Registering Hive Table...")
    t0 = time.time()
    df.write.mode("overwrite") \
        .option("path", s3_path) \
        .saveAsTable(table_name)
    t_write = time.time() - t0
    print(f"✅ S3 Write & Metastore Registration complete in {t_write:.2f} seconds.")

    # Step 3: Run High-Volume SQL Aggregation Queries on S3
    print("\n[Step 3/4] Running SQL Aggregation Analytics on S3 Table...")
    t0 = time.time()
    agg_df = spark.sql("""
        SELECT 
            state_id,
            cat_id,
            COUNT(*) AS transaction_count,
            SUM(sales) AS total_sales,
            AVG(sales) AS avg_sales,
            MAX(sales) AS max_single_sale
        FROM default.m5_sales_large
        GROUP BY state_id, cat_id
        ORDER BY state_id, total_sales DESC
    """)
    agg_df.show()
    t_query = time.time() - t0
    print(f"✅ Full-table aggregation query on {row_count:,} rows completed in {t_query:.2f} seconds.")

    # Step 4: Summary Metrics
    total_time = time.time() - start_total
    print("\n==========================================================")
    print("🏆 BENCHMARK EXECUTION SUMMARY")
    print("==========================================================")
    print(f"📁 Source File Size:        4.3 GB (CSV on HDFS)")
    print(f"📈 Total Rows Processed:    {row_count:,} rows")
    print(f"⏱️  HDFS CSV Ingest Time:    {t_read:.2f} s")
    print(f"⏱️  S3 Parquet Write Time:   {t_write:.2f} s")
    print(f"⏱️  S3 Query Analytics Time: {t_query:.2f} s")
    print(f"⏱️  Total End-to-End Time:   {total_time:.2f} s")
    print("==========================================================")

    spark.stop()

if __name__ == "__main__":
    main()
