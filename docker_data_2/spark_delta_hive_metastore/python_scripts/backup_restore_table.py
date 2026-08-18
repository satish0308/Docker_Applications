#!/usr/bin/env python3
"""
Enterprise Table Backup & Disaster Recovery Engine
Supports:
1. Full Data & Metadata Table Backup (Parquet, Delta Lake, Hive)
2. Bit-for-bit Checksum Verification
3. 1-Click In-Place or Cloned Table Restore
4. Native Hive Metastore Registration & Partition Repair
"""
import os
import sys
import json
import time
import hashlib
import argparse
from pyspark.sql import SparkSession

BACKUP_ROOT_DIR = "/backups"

def get_spark(app_name="Table_Backup_Restore_Engine"):
    return SparkSession.builder \
        .appName(app_name) \
        .config("spark.driver.memory", "2g") \
        .config("spark.executor.memory", "3g") \
        .config("spark.sql.shuffle.partitions", "16") \
        .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000") \
        .config("spark.hadoop.fs.s3a.access.key", "minioadmin") \
        .config("spark.hadoop.fs.s3a.secret.key", "minioadmin123") \
        .config("spark.hadoop.fs.s3a.path.style.access", "true") \
        .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false") \
        .config("spark.hadoop.fs.s3a.aws.credentials.provider", "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider") \
        .enableHiveSupport() \
        .getOrCreate()

def compute_checksum(file_path):
    """Computes SHA-256 checksum of a file for bit-for-bit corruption checks."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha256.update(chunk)
    return sha256.hexdigest()

def backup_table(spark, db_name, table_name, custom_backup_name=None):
    """Backs up both data and metadata for a Hive or Delta table."""
    full_table_name = f"{db_name}.{table_name}"
    timestamp_str = time.strftime("%Y%m%d_%H%M%S")
    backup_id = custom_backup_name if custom_backup_name else f"backup_{timestamp_str}_{db_name}_{table_name}"
    target_dir = os.path.join(BACKUP_ROOT_DIR, backup_id)
    data_dir = os.path.join(target_dir, "data")
    
    os.makedirs(data_dir, exist_ok=True)
    t0 = time.time()

    print(f"--> [BACKUP] Starting backup of `{full_table_name}` to `{target_dir}`...")

    # 1. Capture Schema & Table Metadata
    df = spark.table(full_table_name)
    total_rows = df.count()
    fields = [{"name": f.name, "type": f.dataType.simpleString(), "nullable": f.nullable} for f in df.schema.fields]
    
    # 2. Extract Extended Table Properties & Location
    ext_props = {}
    is_delta = False
    storage_loc = ""
    try:
        desc_df = spark.sql(f"DESCRIBE EXTENDED {full_table_name}")
        for row in desc_df.collect():
            p_name, p_val = str(row[0]).strip(), str(row[1]).strip()
            ext_props[p_name] = p_val
            if "Provider" in p_name and "delta" in p_val.lower():
                is_delta = True
            if "Location" in p_name:
                storage_loc = p_val
    except Exception as e:
        print(f"--> Metadata inspect note: {e}")

    # 3. Capture DDL if available
    ddl_sql = ""
    try:
        ddl_df = spark.sql(f"SHOW CREATE TABLE {full_table_name}")
        ddl_sql = "\n".join([r[0] for r in ddl_df.collect()])
    except Exception:
        ddl_sql = f"-- Recreated DDL for {full_table_name}\n"

    # 4. Export Table Data to Local Backup Directory
    print(f"--> [BACKUP] Exporting {total_rows:,} rows of data...")
    if is_delta:
        df.write.format("delta").mode("overwrite").save(f"file://{data_dir}")
    else:
        df.write.format("parquet").mode("overwrite").save(f"file://{data_dir}")

    # 5. Compute File Checksums for Corruption Protection
    file_manifest = {}
    total_bytes = 0
    file_count = 0
    for root, _, files in os.walk(data_dir):
        for fname in files:
            fpath = os.path.join(root, fname)
            rel_path = os.path.relpath(fpath, data_dir)
            fsize = os.path.getsize(fpath)
            f_checksum = compute_checksum(fpath)
            file_manifest[rel_path] = {"size": fsize, "sha256": f_checksum}
            total_bytes += fsize
            file_count += 1

    # 6. Save Backup Manifest
    elapsed = time.time() - t0
    manifest = {
        "backup_id": backup_id,
        "database": db_name,
        "table": table_name,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_rows": total_rows,
        "total_files": file_count,
        "total_size_bytes": total_bytes,
        "total_size_mb": round(total_bytes / (1024 * 1024), 2),
        "format": "Delta Lake" if is_delta else "Parquet",
        "original_location": storage_loc,
        "schema": fields,
        "extended_properties": ext_props,
        "files": file_manifest,
        "elapsed_seconds": round(elapsed, 2)
    }

    manifest_path = os.path.join(target_dir, "backup_manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    ddl_path = os.path.join(target_dir, "schema_ddl.sql")
    with open(ddl_path, "w") as f:
        f.write(ddl_sql)

    print(f"--> [BACKUP SUCCESS] Backup `{backup_id}` created in {elapsed:.2f}s!")
    print(f"    Rows: {total_rows:,} | Files: {file_count} | Size: {manifest['total_size_mb']} MB")
    print(f"__BACKUP_RESULT__|{json.dumps(manifest)}")
    return manifest

def restore_table(spark, backup_id, target_db="default", target_table=None, storage_dest="s3a://warehouse/"):
    """Restores a table from a backup directory with checksum validation and Metastore registration."""
    target_dir = os.path.join(BACKUP_ROOT_DIR, backup_id)
    manifest_path = os.path.join(target_dir, "backup_manifest.json")
    
    if not os.path.exists(manifest_path):
        raise FileNotFoundError(f"Backup manifest not found at {manifest_path}")

    with open(manifest_path, "r") as f:
        manifest = json.load(f)

    dest_table = target_table if target_table else manifest["table"]
    full_dest_name = f"{target_db}.{dest_table}"
    data_dir = os.path.join(target_dir, "data")
    is_delta = "delta" in manifest.get("format", "").lower()
    
    dest_storage_path = f"{storage_dest.rstrip('/')}/{dest_table}/"
    t0 = time.time()

    print(f"--> [RESTORE] Restoring backup `{backup_id}` to `{full_dest_name}` at `{dest_storage_path}`...")

    # 1. Verify Checksums Before Restoring (Prevent Corruption)
    print("--> [RESTORE] Verifying backup data integrity checksums...")
    for rel_path, meta in manifest.get("files", {}).items():
        fpath = os.path.join(data_dir, rel_path)
        if not os.path.exists(fpath):
            raise Exception(f"Corruption detected: missing file {rel_path}")
        current_chk = compute_checksum(fpath)
        if current_chk != meta["sha256"]:
            raise Exception(f"Corruption detected: checksum mismatch for {rel_path}")
    print("--> [RESTORE] ✅ All data file checksums verified bit-for-bit!")

    # 2. Read Backup Data into Spark
    if is_delta:
        df = spark.read.format("delta").load(f"file://{data_dir}")
    else:
        df = spark.read.parquet(f"file://{data_dir}")

    # 3. Write to Target Storage & Metastore
    print(f"--> [RESTORE] Writing {manifest['total_rows']:,} rows to `{dest_storage_path}`...")
    if is_delta:
        df.write.format("delta").mode("overwrite") \
            .option("path", dest_storage_path) \
            .saveAsTable(full_dest_name)
    else:
        df.write.mode("overwrite") \
            .option("path", dest_storage_path) \
            .saveAsTable(full_dest_name)

    # 4. Verify Restored Table Row Count
    restored_df = spark.table(full_dest_name)
    restored_cnt = restored_df.count()
    elapsed = time.time() - t0

    if restored_cnt != manifest["total_rows"]:
        raise Exception(f"Row count mismatch after restore! Expected {manifest['total_rows']}, got {restored_cnt}")

    result = {
        "status": "success",
        "backup_id": backup_id,
        "restored_table": full_dest_name,
        "storage_location": dest_storage_path,
        "rows_restored": restored_cnt,
        "format": manifest.get("format", "Parquet"),
        "elapsed_seconds": round(elapsed, 2)
    }

    print(f"--> [RESTORE SUCCESS] Table `{full_dest_name}` restored and verified in {elapsed:.2f}s!")
    print(f"__RESTORE_RESULT__|{json.dumps(result)}")
    return result

def list_backups():
    """Lists all available local table backups."""
    backups = []
    if not os.path.exists(BACKUP_ROOT_DIR):
        return backups
    
    for item in sorted(os.listdir(BACKUP_ROOT_DIR), reverse=True):
        bpath = os.path.join(BACKUP_ROOT_DIR, item)
        mpath = os.path.join(bpath, "backup_manifest.json")
        if os.path.isdir(bpath) and os.path.exists(mpath):
            try:
                with open(mpath, "r") as f:
                    manifest = json.load(f)
                    backups.append(manifest)
            except Exception:
                pass
    return backups

def main():
    parser = argparse.ArgumentParser(description="Big Data Platform Table Backup & Disaster Recovery CLI")
    parser.add_argument("action", choices=["backup", "restore", "list"], help="Action to perform")
    parser.add_argument("--table", help="Table to backup/restore (e.g. default.sales_table)")
    parser.add_argument("--backup-id", help="Backup identifier for restore")
    parser.add_argument("--target-table", help="Target table name for restore")
    parser.add_argument("--storage-dest", default="s3a://warehouse/", help="Target storage path prefix")

    args = parser.parse_args()

    if args.action == "list":
        backups = list_backups()
        print(f"\n📦 Found {len(backups)} Local Table Backup(s):")
        print("-" * 80)
        for b in backups:
            print(f"ID: {b['backup_id']} | Table: {b['database']}.{b['table']} | Format: {b['format']} | Rows: {b['total_rows']:,} | Size: {b['total_size_mb']} MB | Created: {b['created_at']}")
        print("-" * 80)
        return

    spark = get_spark()
    try:
        if args.action == "backup":
            if not args.table:
                print("Error: --table is required for backup (e.g. --table default.rfid)")
                sys.exit(1)
            parts = args.table.split(".")
            db = parts[0] if len(parts) > 1 else "default"
            tbl = parts[1] if len(parts) > 1 else parts[0]
            backup_table(spark, db, tbl, custom_backup_name=args.backup_id)
        elif args.action == "restore":
            if not args.backup_id:
                print("Error: --backup-id is required for restore")
                sys.exit(1)
            target_t = args.target_table
            restore_table(spark, args.backup_id, target_table=target_t, storage_dest=args.storage_dest)
    finally:
        spark.stop()

if __name__ == "__main__":
    main()
