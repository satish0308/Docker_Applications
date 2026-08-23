"""
Data Ingestion API Router
Handles micro-batch dataset uploads, schema detection, type overrides, and dynamic partition registration.
"""

import os
import json
import time
import uuid
import threading
import docker
import pandas as pd
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict

router = APIRouter(prefix="/api/ingestion", tags=["Data Ingestion"])

INGESTION_JOBS_FILE = "ingestion_jobs.json"

def load_ingestion_jobs():
    if os.path.exists(INGESTION_JOBS_FILE):
        try:
            with open(INGESTION_JOBS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_ingestion_jobs(jobs):
    with open(INGESTION_JOBS_FILE, "w") as f:
        json.dump(jobs, f, indent=2)

@router.get("/jobs")
def get_ingestion_jobs():
    """Returns list of all active and historical ingestion jobs."""
    return {"jobs": load_ingestion_jobs()}

@router.post("/preview-schema")
async def preview_schema(file: UploadFile = File(...)):
    """Reads head of uploaded CSV/Parquet file and returns detected schema and sample rows."""
    try:
        content = await file.read()
        filename = file.filename.lower()
        if filename.endswith(".parquet") or filename.endswith(".pq"):
            import io
            df = pd.read_parquet(io.BytesIO(content))
        else:
            import io
            df = pd.read_csv(io.BytesIO(content), nrows=100)

        schema = []
        for col in df.columns:
            dtype_str = str(df[col].dtype)
            suggested = "STRING"
            if "int" in dtype_str:
                suggested = "BIGINT"
            elif "float" in dtype_str or "double" in dtype_str:
                suggested = "DOUBLE"
            elif "bool" in dtype_str:
                suggested = "BOOLEAN"
            elif "datetime" in dtype_str:
                suggested = "TIMESTAMP"
            schema.append({
                "column": col,
                "detected_type": dtype_str,
                "suggested_sql_type": suggested,
                "sample": str(df[col].iloc[0]) if not df.empty else ""
            })

        return {
            "columns": list(df.columns),
            "schema": schema,
            "rows_count": len(df),
            "preview_data": df.head(10).to_dict(orient="records")
        }
    except Exception as ex:
        raise HTTPException(status_code=400, detail=f"Failed to parse file schema: {ex}")
