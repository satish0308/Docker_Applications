"""
Comprehensive Spark Performance Tuning Benchmark Suite
Executes realistic Big Data analytical workloads across 59.18 Million rows
testing different configurations of Executor Count, JVM Memory, Cores, Shuffle Partitions, AQE, and Kryo Serialization.
"""
import sys
import time
import json
import argparse
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window

def parse_args():
    parser = argparse.ArgumentParser(description="Spark Benchmark Runner")
    parser.add_argument("--test-name", type=str, default="Benchmark_Run", help="Name of the test run")
    parser.add_argument("--output-json", type=str, default="/opt/spark/python_scripts/benchmark_results.json", help="Path to write JSON results")
    return parser.parse_args()

def run_benchmark(spark, test_name):
    print(f"\n{'='*70}")
    print(f"🚀 EXECUTING BENCHMARK: {test_name}")
    print(f"{'='*70}")
    
    # 1. Inspect active session configuration
    conf = spark.sparkContext.getConf()
    master = spark.sparkContext.master
    driver_mem = conf.get("spark.driver.memory", "default")
    exec_mem = conf.get("spark.executor.memory", "default")
    exec_cores = conf.get("spark.executor.cores", "default")
    max_cores = conf.get("spark.cores.max", "default")
    shuffle_parts = conf.get("spark.sql.shuffle.partitions", "200")
    aqe_enabled = conf.get("spark.sql.adaptive.enabled", "false")
    kryo_enabled = conf.get("spark.serializer", "default")
    
    print(f"⚙️ Config: Master={master} | DriverMem={driver_mem} | ExecMem={exec_mem} | ExecCores={exec_cores} | MaxCores={max_cores}")
    print(f"⚙️ Tuning: ShuffleParts={shuffle_parts} | AQE={aqe_enabled} | Serializer={kryo_enabled}\n")

    # Load 59.18M row dataset
    df = spark.table("default.m5_sales_large")

    # -------------------------------------------------------------
    # WORKLOAD 1: Full-Scan Aggregation (59.18M Rows)
    # -------------------------------------------------------------
    print("⏳ Running Workload 1: Full Table Scan & Multi-Metric Aggregations...")
    t0 = time.time()
    w1_df = spark.sql("""
        SELECT 
            count(*) as total_records,
            sum(sales) as total_units_sold,
            avg(sales) as avg_units_sold,
            max(sales) as peak_sale,
            min(sales) as min_sale
        FROM default.m5_sales_large
    """)
    w1_res = w1_df.collect()
    w1_time = round(time.time() - t0, 3)
    total_rows = w1_res[0]["total_records"]
    total_sales = w1_res[0]["total_units_sold"]
    print(f"✅ Workload 1 Done in {w1_time:.3f}s | Rows: {total_rows:,} | Total Sales: {total_sales:,}")

    # -------------------------------------------------------------
    # WORKLOAD 2: Multi-Column Group By & Hash Aggregate (Heavy Shuffle)
    # -------------------------------------------------------------
    print("⏳ Running Workload 2: Multi-Column Grouping & Rollup (state_id, store_id, dept_id, cat_id)...")
    t0 = time.time()
    w2_df = spark.sql("""
        SELECT 
            state_id,
            store_id,
            cat_id,
            dept_id,
            count(*) as dept_record_count,
            sum(sales) as dept_total_sales,
            avg(sales) as dept_avg_sales,
            stddev(sales) as dept_stddev_sales
        FROM default.m5_sales_large
        GROUP BY state_id, store_id, cat_id, dept_id
        ORDER BY dept_total_sales DESC
    """)
    w2_count = w2_df.count()
    w2_time = round(time.time() - t0, 3)
    print(f"✅ Workload 2 Done in {w2_time:.3f}s | Grouped Output Rows: {w2_count:,}")

    # -------------------------------------------------------------
    # WORKLOAD 3: Windowed Partition Ranking & Time-Series Aggregations
    # -------------------------------------------------------------
    print("⏳ Running Workload 3: Distributed Window Function & State-Level Store Ranking...")
    t0 = time.time()
    w3_df = spark.sql("""
        WITH daily_store_sales AS (
            SELECT 
                state_id,
                store_id,
                date,
                sum(sales) as daily_revenue
            FROM default.m5_sales_large
            GROUP BY state_id, store_id, date
        )
        SELECT 
            state_id,
            store_id,
            date,
            daily_revenue,
            rank() OVER (PARTITION BY state_id ORDER BY daily_revenue DESC) as revenue_rank
        FROM daily_store_sales
        WHERE daily_revenue > 0
    """)
    w3_count = w3_df.count()
    w3_time = round(time.time() - t0, 3)
    print(f"✅ Workload 3 Done in {w3_time:.3f}s | Windowed Rows: {w3_count:,}")

    total_time = round(w1_time + w2_time + w3_time, 3)
    print(f"\n🏆 Total Benchmark Execution Time: {total_time:.3f}s")
    print(f"{'='*70}\n")

    return {
        "test_name": test_name,
        "total_dataset_rows": total_rows,
        "config": {
            "master": master,
            "driver_memory": driver_mem,
            "executor_memory": exec_mem,
            "executor_cores": exec_cores,
            "max_cores": max_cores,
            "shuffle_partitions": shuffle_parts,
            "aqe_enabled": aqe_enabled,
            "serializer": kryo_enabled
        },
        "metrics": {
            "workload_1_aggregation_sec": w1_time,
            "workload_2_groupby_rollup_sec": w2_time,
            "workload_3_window_ranking_sec": w3_time,
            "total_execution_sec": total_time
        }
    }

if __name__ == "__main__":
    args = parse_args()
    
    # Initialize SparkSession
    spark = SparkSession.builder \
        .appName(f"Benchmark_{args.test_name}") \
        .enableHiveSupport() \
        .getOrCreate()
        
    res = run_benchmark(spark, args.test_name)
    spark.stop()

    # Append structured result output
    print(f"__BENCHMARK_RESULT__|{json.dumps(res)}")
