# ⚡ Apache Spark Performance Tuning & Multi-Executor Benchmark Report

## 🌟 Executive Summary
This report provides an end-to-end empirical benchmark of **Apache Spark 3.5.2** on **59,181,090 rows (4.3 GB uncompressed CSV dataset)** stored as optimized Parquet on **MinIO S3 / Hive Metastore** across **5 distinct compute configurations and tuning profiles**.

---

## 📊 Benchmark Results Matrix

| Test # | Configuration Profile | Workers | Total Cores | Total RAM | Exec Memory | Shuffle Partitions | AQE | Workload 1 (Agg) | Workload 2 (Group By) | Workload 3 (Window) | **Total Time** | **Speedup** |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1** | 1. Baseline (Unoptimized / 1 Worker / 2GB RAM / 2 Cores) | 1 | 2 Cores | 4 GB | 2g | 16 | ❌ | 454.526s | 120.488s | 206.122s | **781.136s** | 1.0x (Baseline) |
| **2** | 2. Tuned Single Worker (4GB RAM / 4 Cores / AQE / Kryo) | 1 | 4 Cores | 8 GB | 4g | 64 | ✅ | 318.674s | 95.344s | 162.496s | **576.514s** | **1.35x** 🚀 |
| **3** | 3. Dual Workers Scaled (2 Workers / 8 Cores / 16GB Total RAM) | 2 | 8 Cores | 16 GB | 4g | 64 | ✅ | 267.872s | 85.15s | 118.207s | **471.229s** | **1.66x** 🚀 |
| **4** | 4. Heavy ETL Sizing (2 Workers / 8GB per Exec / 200 Partitions / Off-Heap) | 2 | 8 Cores | 16 GB | 8g | 200 | ✅ | 253.701s | 69.538s | 110.686s | **433.925s** | **1.8x** 🚀 |
| **5** | 5. Extreme Fleet Scaling (3 Workers / 12 Cores / 24GB Total RAM / 200 Partitions) | 3 | 12 Cores | 24 GB | 8g | 200 | ✅ | 235.362s | 70.171s | 125.283s | **430.816s** | **1.81x** 🚀 |

---

## 🔬 In-Depth Workload Analysis

### 1. 📈 Workload 1: Full Table Scan & Aggregations (59.18M Rows)
- **Query**: `SELECT count(*), sum(sales), avg(sales), max(sales), min(sales) FROM default.m5_sales_large`
- **Analysis**: Pure compute and Parquet column-pruning throughput. Adding worker cores and executor memory directly reduces map stage duration.

### 2. 🗂️ Workload 2: Multi-Column Group By & Hash Aggregation (Heavy Shuffle)
- **Query**: `SELECT state_id, store_id, cat_id, dept_id, count(*), sum(sales), avg(sales), stddev(sales) FROM default.m5_sales_large GROUP BY state_id, store_id, cat_id, dept_id ORDER BY sum(sales) DESC`
- **Analysis**: Causes massive network shuffle. Increasing shuffle partitions from 16 to 64/200 prevents partition skew and JVM GC pauses, while Adaptive Query Execution (AQE) dynamically coalesces empty shuffle partitions.

### 3. ⏳ Workload 3: Distributed Window Function & Partition Ranking
- **Query**: `rank() OVER (PARTITION BY state_id ORDER BY daily_revenue DESC)`
- **Analysis**: Tests shuffle sort operations. Kryo serialization reduces serialized object size across nodes by up to 50%.

---

## 💡 Production Recommendations
1. **For Daily Batch Ingestions (<1GB)**: Use **🟡 Medium Profile** (2 Workers, 4GB RAM, 64 partitions, AQE enabled).
2. **For Massive Data / Aggregations (>10M Rows / >1GB)**: Use **🔴 Heavy Profile** (2-3 Workers, 8GB RAM per executor, 200 partitions, Kryo serializer, Off-Heap enabled).
3. **AQE & Dynamic Coalescing**: Always keep `spark.sql.adaptive.enabled=true` enabled to eliminate small partition overheads.
