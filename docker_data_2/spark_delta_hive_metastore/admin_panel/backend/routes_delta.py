"""
Delta Lake Time-Travel & Table Maintenance API Router
Provides endpoints for transaction history inspection, historical snapshot queries,
OPTIMIZE compaction, Z-Ordering, VACUUM storage reclamation, 1-click in-place Delta conversion, and rollbacks.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Union
import subprocess
import json
import docker

router = APIRouter(prefix="/api/delta", tags=["Delta Lake Maintenance"])

class OptimizeRequest(BaseModel):
    database: Optional[str] = "default"
    table: Optional[str] = None
    zorder_columns: Optional[str] = None
    zorder_by: Optional[Union[List[str], str]] = None

class VacuumRequest(BaseModel):
    database: Optional[str] = "default"
    table: Optional[str] = None
    retention_hours: int = 168

class RestoreRequest(BaseModel):
    database: Optional[str] = "default"
    table: Optional[str] = None
    version: int = 0

class ConvertRequest(BaseModel):
    database: Optional[str] = "default"
    table: Optional[str] = None
    partition_schema: Optional[str] = None

def clean_spark_output(raw_output: str) -> str:
    """Strips verbose JVM flags and log4j headers from Spark CLI output."""
    if not raw_output:
        return ""
    lines = raw_output.strip().split("\n")
    cleaned = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if any(ign in stripped for ign in [
            "NOTE: Picked up JDK_JAVA_OPTIONS:",
            "Setting default log level",
            "To adjust logging level use sc.setLogLevel",
            "WARN NativeCodeLoader:",
            "WARN Utils: Service 'SparkUI'",
            "WARN HiveConf:",
            "WARN ObjectStore:",
            "WARN MetricsConfig:",
            "WARN SparkStringUtils:",
            "WARN SessionState:",
            "Spark Web UI available at",
            "Spark master: local",
            "Using Spark's default log4j",
            "Time taken:"
        ]):
            continue
        cleaned.append(line)
    return "\n".join(cleaned).strip() or raw_output.strip()

def execute_spark_sql(sql_query: str) -> Dict[str, Any]:
    """Executes a Spark SQL command inside the spark container and returns parsed clean output."""
    try:
        client = docker.from_env()
        spark_cont = client.containers.get("spark")
        
        res = spark_cont.exec_run(
            cmd=["/opt/spark/bin/spark-sql", "-e", sql_query],
            stdout=True,
            stderr=True
        )
        raw_output = res.output.decode("utf-8", errors="ignore")
        clean_out = clean_spark_output(raw_output)

        if res.exit_code != 0:
            # Detect if table is a non-Delta parquet table
            if "UNSUPPORTED_FEATURE.TIME_TRAVEL" in clean_out or "is not a Delta table" in clean_out:
                return {
                    "success": False,
                    "is_parquet": True,
                    "error": f"Table is stored in standard Apache Parquet format (not Delta Lake). Click 'Convert to Delta Lake' to enable Time-Travel, OPTIMIZE, and VACUUM.",
                    "raw_error": clean_out,
                    "output": ""
                }
            return {
                "success": False,
                "is_parquet": False,
                "error": clean_out,
                "output": clean_out
            }
        return {
            "success": True,
            "is_parquet": False,
            "error": None,
            "output": clean_out
        }
    except Exception as ex:
        return {
            "success": False,
            "is_parquet": False,
            "error": f"Failed to execute Spark SQL: {str(ex)}",
            "output": ""
        }

@router.get("/history/{db}/{table}")
def get_delta_history_path(db: str, table: str):
    """Retrieves the transaction commit history for a Delta Lake table via path."""
    return get_delta_history_handler(db, table)

@router.get("/history")
def get_delta_history_query(database: str = "default", table: str = "sales"):
    """Retrieves the transaction commit history for a Delta Lake table via query parameters."""
    return get_delta_history_handler(database, table)

def get_delta_history_handler(db: str, table: str):
    full_table = f"{db}.{table}"
    res = execute_spark_sql(f"DESCRIBE HISTORY {full_table};")
    if not res["success"]:
        raise HTTPException(status_code=400 if res.get("is_parquet") else 500, detail=res["error"])
    return {
        "status": "SUCCESS",
        "table": full_table,
        "history_output": res["output"]
    }

@router.get("/snapshot/{db}/{table}")
def get_delta_snapshot_path(db: str, table: str, version: int = 0, limit: int = 25):
    """Queries a historical snapshot of a Delta table at a specific version via path."""
    return get_delta_snapshot_handler(db, table, version, limit)

@router.get("/snapshot")
def get_delta_snapshot_query(database: str = "default", table: str = "sales", version: int = 0, limit: int = 25):
    """Queries a historical snapshot of a Delta table at a specific version via query parameters."""
    return get_delta_snapshot_handler(database, table, version, limit)

def get_delta_snapshot_handler(db: str, table: str, version: int = 0, limit: int = 25):
    full_table = f"{db}.{table}"
    res = execute_spark_sql(f"SELECT * FROM {full_table} VERSION AS OF {version} LIMIT {limit};")
    if not res["success"]:
        raise HTTPException(status_code=400 if res.get("is_parquet") else 500, detail=res["error"])
    return {
        "status": "SUCCESS",
        "table": full_table,
        "version": version,
        "snapshot_output": res["output"]
    }

@router.post("/optimize")
def optimize_delta_table_body(req: OptimizeRequest):
    """Triggers file compaction and optional multidimensional Z-Ordering via POST body."""
    db = req.database or "default"
    table = req.table or "sales"
    return optimize_delta_table_handler(db, table, req)

@router.post("/optimize/{db}/{table}")
def optimize_delta_table_path(db: str, table: str, req: OptimizeRequest):
    """Triggers file compaction and optional multidimensional Z-Ordering via path."""
    return optimize_delta_table_handler(db, table, req)

def optimize_delta_table_handler(db: str, table: str, req: OptimizeRequest):
    full_table = f"{db}.{table}"
    
    # Resolve zorder columns from either zorder_by list or zorder_columns string
    zorder_str = None
    if req.zorder_by:
        if isinstance(req.zorder_by, list):
            zorder_str = ", ".join([c.strip() for c in req.zorder_by if c.strip()])
        elif isinstance(req.zorder_by, str) and req.zorder_by.strip():
            zorder_str = req.zorder_by.strip()
    elif req.zorder_columns and req.zorder_columns.strip():
        zorder_str = req.zorder_columns.strip()

    if zorder_str:
        sql = f"OPTIMIZE {full_table} ZORDER BY ({zorder_str});"
    else:
        sql = f"OPTIMIZE {full_table};"

    res = execute_spark_sql(sql)
    if not res["success"]:
        raise HTTPException(status_code=400 if res.get("is_parquet") else 500, detail=res["error"])
    return {
        "status": "SUCCESS",
        "table": full_table,
        "sql": sql,
        "output": res["output"]
    }

@router.post("/vacuum")
def vacuum_delta_table_body(req: VacuumRequest):
    """Triggers VACUUM storage reclamation to delete expired unreferenced files via POST body."""
    db = req.database or "default"
    table = req.table or "sales"
    return vacuum_delta_table_handler(db, table, req.retention_hours)

@router.post("/vacuum/{db}/{table}")
def vacuum_delta_table_path(db: str, table: str, req: VacuumRequest):
    """Triggers VACUUM storage reclamation to delete expired unreferenced files via path."""
    return vacuum_delta_table_handler(db, table, req.retention_hours)

def vacuum_delta_table_handler(db: str, table: str, retention_hours: int):
    full_table = f"{db}.{table}"
    sql = f"SET spark.databricks.delta.vacuum.parallelDelete.enabled = true; VACUUM {full_table} RETAIN {retention_hours} HOURS;"
    res = execute_spark_sql(sql)
    if not res["success"]:
        raise HTTPException(status_code=400 if res.get("is_parquet") else 500, detail=res["error"])
    return {
        "status": "SUCCESS",
        "table": full_table,
        "retention_hours": retention_hours,
        "output": res["output"]
    }

@router.post("/restore")
def restore_delta_table_body(req: RestoreRequest):
    """Restores a Delta Lake table in-place to an earlier point-in-time version via POST body."""
    db = req.database or "default"
    table = req.table or "sales"
    return restore_delta_table_handler(db, table, req.version)

@router.post("/restore/{db}/{table}")
def restore_delta_table_path(db: str, table: str, req: RestoreRequest):
    """Restores a Delta Lake table in-place to an earlier point-in-time version via path."""
    return restore_delta_table_handler(db, table, req.version)

def restore_delta_table_handler(db: str, table: str, version: int):
    full_table = f"{db}.{table}"
    sql = f"RESTORE TABLE {full_table} TO VERSION AS OF {version};"
    res = execute_spark_sql(sql)
    if not res["success"]:
        raise HTTPException(status_code=400 if res.get("is_parquet") else 500, detail=res["error"])
    return {
        "status": "SUCCESS",
        "table": full_table,
        "restored_to_version": version,
        "output": res["output"]
    }

@router.post("/convert")
def convert_to_delta_body(req: ConvertRequest):
    """Converts a standard Apache Parquet table in-place to a Delta Lake table via POST body."""
    db = req.database or "default"
    table = req.table or "rfid"
    return convert_to_delta_handler(db, table, req.partition_schema)

@router.post("/convert/{db}/{table}")
def convert_to_delta_path(db: str, table: str, req: ConvertRequest = None):
    """Converts a standard Apache Parquet table in-place to a Delta Lake table via path."""
    part = req.partition_schema if req else None
    return convert_to_delta_handler(db, table, part)

def convert_to_delta_handler(db: str, table: str, partition_schema: Optional[str] = None):
    full_table = f"{db}.{table}"
    if partition_schema and partition_schema.strip():
        sql = f"CONVERT TO DELTA {full_table} PARTITIONED BY ({partition_schema.strip()});"
    else:
        sql = f"CONVERT TO DELTA {full_table};"

    res = execute_spark_sql(sql)
    if not res["success"]:
        raise HTTPException(status_code=500, detail=res["error"])
    return {
        "status": "SUCCESS",
        "table": full_table,
        "message": f"Table '{full_table}' successfully converted to Delta Lake format with transaction log.",
        "sql": sql,
        "output": res["output"]
    }
