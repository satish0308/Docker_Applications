#!/usr/bin/env python3
"""
Delta Lake Production Maintenance Utility
Supports:
1. OPTIMIZE table_name [ZORDER BY (cols...)]
2. VACUUM table_name [RETAIN num HOURS]
3. RESTORE TABLE table_name TO VERSION AS OF version
4. DESCRIBE HISTORY table_name
"""
import sys
import argparse
from pyspark.sql import SparkSession

def get_spark_session(app_name="Delta_Maintenance"):
    return SparkSession.builder \
        .appName(app_name) \
        .config("spark.driver.memory", "2g") \
        .config("spark.executor.memory", "3g") \
        .config("spark.databricks.delta.vacuum.parallelDelete.enabled", "true") \
        .enableHiveSupport() \
        .getOrCreate()

def describe_history(spark, table_name):
    print(f"--> Fetching commit history for: {table_name}")
    df = spark.sql(f"DESCRIBE HISTORY {table_name}")
    df.show(30, truncate=False)

def optimize_table(spark, table_name, zorder_cols=None):
    print(f"--> Optimizing and compacting Delta table: {table_name}")
    if zorder_cols:
        cols_str = ", ".join(zorder_cols)
        print(f"--> Applying Multidimensional Z-Ordering on: {cols_str}")
        res = spark.sql(f"OPTIMIZE {table_name} ZORDER BY ({cols_str})")
    else:
        res = spark.sql(f"OPTIMIZE {table_name}")
    res.show(truncate=False)

def vacuum_table(spark, table_name, retention_hours=168):
    print(f"--> Vacuuming Delta table {table_name} (Retaining {retention_hours} hours)...")
    if retention_hours < 168:
        spark.conf.set("spark.databricks.delta.vacuum.retentionDurationCheck.enabled", "false")
    res = spark.sql(f"VACUUM {table_name} RETAIN {retention_hours} HOURS")
    res.show(truncate=False)

def restore_table(spark, table_name, version):
    print(f"--> Restoring Delta table {table_name} to VERSION AS OF {version}...")
    res = spark.sql(f"RESTORE TABLE {table_name} TO VERSION AS OF {version}")
    res.show(truncate=False)

def main():
    parser = argparse.ArgumentParser(description="Delta Lake Cluster Maintenance Utility")
    parser.add_argument("action", choices=["history", "optimize", "vacuum", "restore"], help="Maintenance action")
    parser.add_argument("table", help="Target table (e.g. default.sales_table)")
    parser.add_argument("--zorder", nargs="+", help="Z-Order clustering columns for optimize")
    parser.add_argument("--retention", type=int, default=168, help="Vacuum retention period in hours")
    parser.add_argument("--version", type=int, help="Target version for restore")

    args = parser.parse_args()
    spark = get_spark_session()

    try:
        if args.action == "history":
            describe_history(spark, args.table)
        elif args.action == "optimize":
            optimize_table(spark, args.table, args.zorder)
        elif args.action == "vacuum":
            vacuum_table(spark, args.table, args.retention)
        elif args.action == "restore":
            if args.version is None:
                print("Error: --version is required for restore action.")
                sys.exit(1)
            restore_table(spark, args.table, args.version)
    finally:
        spark.stop()

if __name__ == "__main__":
    main()
