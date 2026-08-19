# 📦 Enterprise Table & Database Backup and Disaster Recovery Guide

A complete, zero-corruption **Table & Database Backup & Disaster Recovery Engine** has been built and integrated into both the **Web Big Data Studio (`http://localhost:8501`)** and a standalone **CLI Utility**.

---

## 🛡️ Zero Data Corruption Guarantee

1. **Both Data & Metadata Backed Up**:
   - **Schema & DDL**: Table DDL (`SHOW CREATE TABLE`), column types, partition specifications, SerDe properties, and Hive Metastore entries.
   - **Underlying Storage**: Complete, bit-for-bit export of all Parquet/Delta chunk files, partition directory trees, and transaction logs (`_delta_log/`).
2. **SHA-256 Cryptographic Checksums**:
   - Every exported data file has its SHA-256 hash calculated and stored in `backup_manifest.json`.
   - Before restoring, the engine validates all checksums. If even a single byte is corrupted or missing, the restore halts immediately with a clear alert.
3. **Automatic Hive Metastore Registration**:
   - Restoring a table or database not only puts data into MinIO S3 or HDFS, but also registers the tables in PostgreSQL Hive Metastore so they are instantly queryable in **Hue (`http://localhost:8888`)**, **SparkSQL**, and **JupyterLab**.

---

## 🖥️ How to Use via Web Studio (`http://localhost:8501`)

Open **[http://localhost:8501](http://localhost:8501)** and select **"📦 Table Backup & Restore"** from the navigation menu:

### 1. 💾 Create Backup (Single Table or Complete Database)
- **📁 Single Table Mode**:
  1. Select any table from the dropdown (e.g. `default.rfid`, `default.m5_sales_large`).
  2. Click **"🚀 Create Full Table Backup"**.
- **🗄️ Complete Database Mode**:
  1. Select the database (e.g. `default`).
  2. Click **"🚀 Create Complete Database Backup"**.
  3. Automatically discovers all tables, backs up data and DDL for each table, computes SHA-256 checksums, and creates a unified database master manifest in `/backups/db_backup_<timestamp>_<db>/`.

### 2. 📂 Local Backups Explorer
1. Lists both `[TABLE]` and `[DATABASE]` backups with table counts, row totals, sizes, and timestamps.
2. Inspect any backup to see individual table breakdowns, file sizes, and **SHA-256 checksums**.
3. **📥 1-Click Download**: Download the entire table or database backup as a `.tar.gz` bundle directly to your laptop.

### 3. 🔄 Restore (Single Table or Complete Database)
1. Select the backup to restore from the dropdown.
2. If restoring a **Database Backup**:
   - Restores all tables into the target database with 100% checksum verification and Metastore catalog registration.
3. If restoring a **Table Backup**:
   - Enter target table name and storage destination (`MinIO S3` or `HDFS`).
4. Click **"🔄 Execute Full Restore & Register in Hue"**.

---

## 💻 How to Use via Standalone Python / CLI

```bash
# 1. List all local backups (Tables & Databases)
docker exec spark /opt/spark/bin/spark-submit /opt/spark/backup_restore_table.py list

# 2. Back up an entire database (All tables in default database)
docker exec spark /opt/spark/bin/spark-submit /opt/spark/backup_restore_table.py backup-db --database default

# 3. Back up a single table
docker exec spark /opt/spark/bin/spark-submit /opt/spark/backup_restore_table.py backup --table default.rfid

# 4. Restore an entire database
docker exec spark /opt/spark/bin/spark-submit /opt/spark/backup_restore_table.py restore-db \
  --backup-id db_backup_20260818_default \
  --database default_restored

# 5. Restore a single table
docker exec spark /opt/spark/bin/spark-submit /opt/spark/backup_restore_table.py restore \
  --backup-id backup_20260818_131748_default_rfid \
  --target-table rfid_restored
```
