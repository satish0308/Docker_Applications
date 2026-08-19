# 🚀 Production Data Pipeline & Delta Performance Engine Guide

## 🌟 Overview
This guide covers the 4 core pipeline and storage optimization engines built into the Big Data Platform:
1. **🗂️ Dynamic Partitioning & Partition Pruning**
2. **⏳ Delta Lake Time-Travel & Version Explorer**
3. **⚡ Storage Compaction & Vacuuming Engine (`OPTIMIZE` & `VACUUM`)**
4. **⏰ Scheduled Batch Ingestion & Directory Watchers**

---

## 🗂️ 1. Dynamic Partitioning & Partition Pruning
- In **"📥 Data Ingestion & Partitioning"**:
  - Automatically identifies candidate partition columns from detected schemas.
  - Multi-select dropdown allows selecting partition keys (e.g. `state_id`, `dept_id`, `year`, `date`).
  - PySpark dynamically writes partitioned datasets (`.partitionBy(...)`) to S3 / HDFS and registers partitions in Hive Metastore (`MSCK REPAIR TABLE`).
  - **Result**: Downstream SQL queries in **Hue (`http://localhost:8888`)** skip 90%+ of data files for sub-second responses!

---

## ⏳ 2. Delta Lake Time-Travel & Version Explorer
- In **"⏳ Delta Time-Travel & Maintenance"**:
  - **Commit History**: Visual table listing commit versions, timestamps, operations (`WRITE`, `MERGE`, `OPTIMIZE`), and row change metrics.
  - **1-Click Historical Snapshot Query**: Query `VERSION AS OF <n>` to inspect historical table states.
  - **1-Click Table Rollback**: Restore any Delta table state to an exact historical version (`RESTORE TABLE <tbl> TO VERSION AS OF <n>`).

---

## ⚡ 3. Storage Compaction & Vacuuming Engine (`OPTIMIZE` & `VACUUM`)
- **Table Compaction & Z-Ordering (`OPTIMIZE`)**:
  - Merges millions of small files into optimal 128MB chunks.
  - Supports multidimensional clustering (`ZORDER BY (col1, col2)`) to accelerate multi-column filters.
- **Space Reclamation (`VACUUM`)**:
  - Deletes historical parquet files no longer referenced by transaction logs to reclaim S3/MinIO disk space.

---

## ⏰ 4. Scheduled Batch Ingestion & Directory Watchers
- In **"⏰ Scheduled Ingestion Jobs"**:
  - Configure recurring batch jobs that monitor watch folders (e.g. `hdfs://namenode:9000/data/incoming/*.csv` or host folders).
  - Define trigger intervals (`Every 5 Minutes`, `Hourly`, `Daily at Midnight`, `On-Demand`).
  - 1-Click "▶️ Trigger Now" button with execution logging and row counting.
  - Persistent job registry saved to `/app/scheduled_jobs.json`.

---

## 🛠️ 5. Standalone Delta CLI Utility

```bash
# View History
python3 python_scripts/delta_maintenance.py history default.sales_table

# Optimize & Z-Order
python3 python_scripts/delta_maintenance.py optimize default.sales_table --zorder store_id item_id

# Vacuum Space
python3 python_scripts/delta_maintenance.py vacuum default.sales_table --retention 168

# Restore Snapshot
python3 python_scripts/delta_maintenance.py restore default.sales_table --version 0
```
