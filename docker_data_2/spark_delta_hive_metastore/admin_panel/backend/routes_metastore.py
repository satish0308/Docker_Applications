"""
Hive Metastore Catalog & Table Inspector API Router
Queries PostgreSQL Hive Metastore database for catalogs, tables, schemas,
and triggers Spark for interactive data sampling, row counting, and custom SQL inspection.
"""

import os
import json
import time
import subprocess
import psycopg2
import psycopg2.extras
import docker
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

router = APIRouter(prefix="/api/metastore", tags=["Metastore Catalog"])

class InspectRequest(BaseModel):
    table_name: str
    limit: int = 50
    custom_sql: Optional[str] = None

class CreateDbRequest(BaseModel):
    database_name: str
    location: Optional[str] = None

def get_postgres_connection():
    return psycopg2.connect(
        host="postgres",
        port=5432,
        dbname="metastore",
        user="hiveuser",
        password="hivepassword",
        connect_timeout=3
    )

@router.get("/databases")
def get_all_databases():
    """Lists all registered databases in Hive Metastore."""
    try:
        conn = get_postgres_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute('SELECT "NAME" as name, "DB_LOCATION_URI" as location_uri FROM "DBS" ORDER BY "NAME";')
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return {"databases": [dict(r) for r in rows]}
    except Exception as ex:
        return {"databases": [], "error": str(ex)}

@router.post("/create-database")
def create_database(req: CreateDbRequest):
    """Creates a new database in Hive Metastore via Spark SQL."""
    try:
        client = docker.from_env()
        spark_cont = client.containers.get("spark")
        loc_clause = f" LOCATION '{req.location}'" if req.location else ""
        sql = f"CREATE DATABASE IF NOT EXISTS {req.database_name}{loc_clause};"
        res = spark_cont.exec_run(f'/opt/spark/bin/spark-sql -e "{sql}"')
        if res.exit_code != 0:
            raise HTTPException(status_code=500, detail=res.output.decode('utf-8'))
        return {"status": "SUCCESS", "database": req.database_name}
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))

@router.get("/tables")
def get_all_tables():
    """Queries Hive Metastore and returns all registered tables across all databases."""
    try:
        conn = get_postgres_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        query = """
        SELECT 
            d."NAME" as database_name,
            t."TBL_NAME" as table_name,
            t."TBL_TYPE" as table_type,
            to_timestamp(t."CREATE_TIME") as created_at,
            s."LOCATION" as storage_location
        FROM "TBLS" t
        JOIN "DBS" d ON t."DB_ID" = d."DB_ID"
        LEFT JOIN "SDS" s ON t."SD_ID" = s."SD_ID"
        ORDER BY d."NAME", t."TBL_NAME";
        """
        cur.execute(query)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        tables = []
        for r in rows:
            loc = str(r["storage_location"] or "")
            is_delta = "delta" in loc.lower() or "tbl_type" in str(r["table_type"]).lower()
            tables.append({
                "database_name": r["database_name"],
                "table_name": r["table_name"],
                "table_type": r["table_type"],
                "format": "Delta Lake" if is_delta else "Parquet / External",
                "storage_location": loc,
                "created_at": str(r["created_at"]) if r["created_at"] else "N/A",
                "Database": r["database_name"],
                "Table Name": r["table_name"],
                "Format": "Delta Lake" if is_delta else "Parquet / External",
                "Storage Location": loc,
                "Created At": str(r["created_at"]) if r["created_at"] else "N/A"
            })
        return {"tables": tables}
    except Exception as ex:
        return {"tables": [], "error": str(ex)}

@router.get("/table/{database}/{table_name}")
def get_table_details(database: str, table_name: str):
    """Fetches schema, columns, partitions, and storage parameters for a specific table."""
    try:
        conn = get_postgres_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Columns
        col_query = """
        SELECT 
            c."COLUMN_NAME" as column_name,
            c."TYPE_NAME" as type_name,
            c."INTEGER_IDX" as column_index
        FROM "COLUMNS_V2" c
        JOIN "SDS" s ON c."CD_ID" = s."CD_ID"
        JOIN "TBLS" t ON s."SD_ID" = t."SD_ID"
        JOIN "DBS" d ON t."DB_ID" = d."DB_ID"
        WHERE d."NAME" = %s AND t."TBL_NAME" = %s
        ORDER BY c."INTEGER_IDX";
        """
        cur.execute(col_query, (database, table_name))
        cols = cur.fetchall()

        # Partitions
        part_query = """
        SELECT 
            p."PART_NAME" as partition_name,
            to_timestamp(p."CREATE_TIME") as created_at
        FROM "PARTITIONS" p
        JOIN "TBLS" t ON p."TBL_ID" = t."TBL_ID"
        JOIN "DBS" d ON t."DB_ID" = d."DB_ID"
        WHERE d."NAME" = %s AND t."TBL_NAME" = %s
        LIMIT 50;
        """
        cur.execute(part_query, (database, table_name))
        parts = cur.fetchall()

        cur.close()
        conn.close()
        return {
            "database": database,
            "table": table_name,
            "columns": [dict(c) for c in cols],
            "partitions": [dict(p) for p in parts]
        }
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))

@router.post("/inspect")
def inspect_table_data(req: InspectRequest):
    """Executes a PySpark inspection job to fetch live schema, records, and row counts."""
    full_tbl = req.table_name
    sql_to_run = req.custom_sql if req.custom_sql else f"SELECT * FROM {full_tbl} LIMIT {req.limit}"
    
    script_content = f"""
import json
import time
from pyspark.sql import SparkSession

spark = SparkSession.builder \\
    .appName("Inspect_{full_tbl.replace('.', '_')}") \\
    .config("spark.driver.memory", "2g") \\
    .config("spark.executor.memory", "2g") \\
    .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000") \\
    .config("spark.hadoop.fs.s3a.access.key", "minioadmin") \\
    .config("spark.hadoop.fs.s3a.secret.key", "minioadmin123") \\
    .config("spark.hadoop.fs.s3a.path.style.access", "true") \\
    .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false") \\
    .enableHiveSupport() \\
    .getOrCreate()

t0 = time.time()
try:
    df_sample = spark.sql(\"\"\"{sql_to_run}\"\"\")
    fields = []
    for idx, f in enumerate(df_sample.schema.fields):
        fields.append({{
            "Index": idx + 1,
            "Column Name": f.name,
            "Data Type": f.dataType.simpleString().upper(),
            "Nullable": "YES" if f.nullable else "NO"
        }})
    
    records = [row.asDict(recursive=True) for row in df_sample.collect()]
    
    try:
        df_full = spark.table("{full_tbl}")
        total_count = df_full.count()
    except Exception:
        total_count = len(records)

    elapsed = time.time() - t0
    result = {{
        "status": "success",
        "schema": fields,
        "records": records,
        "total_rows": total_count,
        "columns_count": len(fields),
        "elapsed_sec": round(elapsed, 2)
    }}
    print("__JSON_RES_START__" + json.dumps(result, default=str) + "__JSON_RES_END__")
except Exception as ex:
    print("__JSON_RES_START__" + json.dumps({{"status": "error", "error": str(ex)}}) + "__JSON_RES_END__")
spark.stop()
"""
    try:
        client = docker.from_env()
        spark_cont = client.containers.get("spark")
        
        # Copy script to spark container
        import io, tarfile
        tar_stream = io.BytesIO()
        with tarfile.open(fileobj=tar_stream, mode='w') as tar:
            tarinfo = tarfile.TarInfo(name="inspect_script.py")
            raw_bytes = script_content.encode('utf-8')
            tarinfo.size = len(raw_bytes)
            tarinfo.mtime = time.time()
            tar.addfile(tarinfo, io.BytesIO(raw_bytes))
        tar_stream.seek(0)
        spark_cont.put_archive("/tmp", tar_stream.read())

        res = spark_cont.exec_run("/opt/spark/bin/spark-submit /tmp/inspect_script.py")
        output = res.output.decode('utf-8', errors='ignore')

        if "__JSON_RES_START__" in output and "__JSON_RES_END__" in output:
            json_str = output.split("__JSON_RES_START__")[1].split("__JSON_RES_END__")[0]
            parsed = json.loads(json_str)
            if parsed.get("status") == "error":
                raise HTTPException(status_code=500, detail=parsed.get("error"))
            return parsed
        else:
            raise HTTPException(status_code=500, detail=output)
    except HTTPException:
        raise
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))
