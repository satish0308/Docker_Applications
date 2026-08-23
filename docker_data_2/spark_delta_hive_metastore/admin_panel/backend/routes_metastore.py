"""
Hive Metastore Catalog API Router
Queries PostgreSQL Hive Metastore database to list tables, databases, columns, partition distributions, and sample data.
"""

import psycopg2
import psycopg2.extras
from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional

router = APIRouter(prefix="/api/metastore", tags=["Metastore Catalog"])

def get_postgres_connection():
    return psycopg2.connect(
        host="postgres",
        port=5432,
        dbname="metastore",
        user="hiveuser",
        password="hivepassword",
        connect_timeout=3
    )

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
        return {"tables": [dict(r) for r in rows]}
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
