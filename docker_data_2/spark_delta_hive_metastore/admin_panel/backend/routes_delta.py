"""
Delta Lake Time-Travel & Table Maintenance API Router
Provides endpoints for transaction history inspection, historical snapshot queries,
OPTIMIZE compaction, Z-Ordering, VACUUM storage reclamation, and in-place rollbacks.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import subprocess
import json

router = APIRouter(prefix="/api/delta", tags=["Delta Lake Maintenance"])

class OptimizeRequest(BaseModel):
    zorder_columns: Optional[str] = None

class VacuumRequest(BaseModel):
    retention_hours: int = 168

class RestoreRequest(BaseModel):
    version: int

def execute_spark_sql(sql_query: str) -> Dict[str, Any]:
    """Executes a Spark SQL command inside the spark container and returns parsed output."""
    escaped_sql = sql_query.replace('"', '\\"')
    cmd = [
        "docker", "exec", "spark",
        "/opt/spark/bin/spark-sql",
        "-e", sql_query
    ]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120
        )
        if proc.returncode != 0:
            return {
                "success": False,
                "error": proc.stderr.strip() or proc.stdout.strip(),
                "output": proc.stdout.strip()
            }
        return {
            "success": True,
            "error": None,
            "output": proc.stdout.strip()
        }
    except Exception as ex:
        return {
            "success": False,
            "error": str(ex),
            "output": ""
        }

@router.get("/history/{db}/{table}")
def get_delta_history(db: str, table: str):
    """Retrieves the transaction commit history for a Delta Lake table."""
    full_table = f"{db}.{table}"
    res = execute_spark_sql(f"DESCRIBE HISTORY {full_table};")
    if not res["success"]:
        raise HTTPException(status_code=500, detail=res["error"])
    return {
        "table": full_table,
        "history_output": res["output"]
    }

@router.get("/snapshot/{db}/{table}")
def get_delta_snapshot(db: str, table: str, version: int = 0, limit: int = 25):
    """Queries a historical snapshot of a Delta table at a specific version."""
    full_table = f"{db}.{table}"
    res = execute_spark_sql(f"SELECT * FROM {full_table} VERSION AS OF {version} LIMIT {limit};")
    if not res["success"]:
        raise HTTPException(status_code=500, detail=res["error"])
    return {
        "table": full_table,
        "version": version,
        "snapshot_output": res["output"]
    }

@router.post("/optimize/{db}/{table}")
def optimize_delta_table(db: str, table: str, req: OptimizeRequest):
    """Triggers file compaction and optional multidimensional Z-Ordering."""
    full_table = f"{db}.{table}"
    if req.zorder_columns and req.zorder_columns.strip():
        sql = f"OPTIMIZE {full_table} ZORDER BY ({req.zorder_columns.strip()});"
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

@router.post("/vacuum/{db}/{table}")
def vacuum_delta_table(db: str, table: str, req: VacuumRequest):
    """Triggers VACUUM storage reclamation to delete expired unreferenced files."""
    full_table = f"{db}.{table}"
    sql = f"SET spark.databricks.delta.vacuum.parallelDelete.enabled = true; VACUUM {full_table} RETAIN {req.retention_hours} HOURS;"
    res = execute_spark_sql(sql)
    if not res["success"]:
        raise HTTPException(status_code=500, detail=res["error"])
    return {
        "status": "SUCCESS",
        "table": full_table,
        "retention_hours": req.retention_hours,
        "output": res["output"]
    }

@router.post("/restore/{db}/{table}")
def restore_delta_table(db: str, table: str, req: RestoreRequest):
    """Restores a Delta Lake table in-place to an earlier point-in-time version."""
    full_table = f"{db}.{table}"
    sql = f"RESTORE TABLE {full_table} TO VERSION AS OF {req.version};"
    res = execute_spark_sql(sql)
    if not res["success"]:
        raise HTTPException(status_code=500, detail=res["error"])
    return {
        "status": "SUCCESS",
        "table": full_table,
        "restored_to_version": req.version,
        "output": res["output"]
    }
