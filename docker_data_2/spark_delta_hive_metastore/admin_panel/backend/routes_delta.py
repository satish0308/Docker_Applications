"""
Delta Lake Time-Travel & Table Maintenance API Router
Provides endpoints for transaction history inspection, historical snapshot queries,
OPTIMIZE compaction, Z-Ordering, VACUUM storage reclamation, and in-place rollbacks.
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

def execute_spark_sql(sql_query: str) -> Dict[str, Any]:
    """Executes a Spark SQL command inside the spark container and returns parsed output."""
    try:
        client = docker.from_env()
        spark_cont = client.containers.get("spark")
        
        # Run spark-sql via container exec
        res = spark_cont.exec_run(
            cmd=["/opt/spark/bin/spark-sql", "-e", sql_query],
            stdout=True,
            stderr=True
        )
        raw_output = res.output.decode("utf-8", errors="ignore").strip()
        
        # Filter JVM startup noise
        filtered_lines = [
            line for line in raw_output.split("\n")
            if not any(k in line for k in [
                "Using Spark's default log4j", "WARN NativeCodeLoader", "Setting default log level",
                "Spark master: spark://", "INFO SharedState:", "INFO HiveUtils:", "INFO HiveServer2:"
            ])
        ]
        clean_output = "\n".join(filtered_lines).strip() or raw_output

        if res.exit_code != 0:
            return {
                "success": False,
                "error": clean_output,
                "output": clean_output
            }
        return {
            "success": True,
            "error": None,
            "output": clean_output
        }
    except Exception as ex:
        # Fallback to subprocess if docker client issue
        try:
            proc = subprocess.run(
                ["docker", "exec", "spark", "/opt/spark/bin/spark-sql", "-e", sql_query],
                capture_output=True,
                text=True,
                timeout=120
            )
            out = (proc.stdout + "\n" + proc.stderr).strip()
            return {
                "success": proc.returncode == 0,
                "error": None if proc.returncode == 0 else out,
                "output": out
            }
        except Exception as sub_ex:
            return {
                "success": False,
                "error": f"Failed to execute Spark SQL: {sub_ex}",
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
        raise HTTPException(status_code=500, detail=res["error"])
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
        raise HTTPException(status_code=500, detail=res["error"])
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
        raise HTTPException(status_code=500, detail=res["error"])
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
        raise HTTPException(status_code=500, detail=res["error"])
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
        raise HTTPException(status_code=500, detail=res["error"])
    return {
        "status": "SUCCESS",
        "table": full_table,
        "restored_to_version": version,
        "output": res["output"]
    }
