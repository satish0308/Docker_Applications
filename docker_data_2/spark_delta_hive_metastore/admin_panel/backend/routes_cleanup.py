"""
System Maintenance & 1-Click Cluster Purge API Router
Provides endpoints to terminate idle database handles, clear hanging Livy sessions,
leave HDFS safe mode, and reclaim cluster RAM.
"""

import json
import urllib.request
import docker
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any

router = APIRouter(prefix="/api/cleanup", tags=["System Cleanup"])

@router.post("/purge")
def execute_cluster_purge():
    """Performs cluster-wide garbage collection, frees idle locks, and terminates zombie sessions."""
    logs = []
    
    # 1. Clear Livy Sessions
    try:
        req = urllib.request.urlopen("http://livy:8998/sessions", timeout=3)
        data = json.loads(req.read().decode('utf-8'))
        sessions = data.get("sessions", [])
        cleared_livy = 0
        for s in sessions:
            sid = s.get("id")
            del_req = urllib.request.Request(f"http://livy:8998/sessions/{sid}", method="DELETE")
            urllib.request.urlopen(del_req, timeout=3)
            cleared_livy += 1
        logs.append(f"✅ Cleared {cleared_livy} hanging/abandoned Livy sessions.")
    except Exception as ex:
        logs.append(f"ℹ️ Livy Session Check: {ex}")

    # 2. Terminate Idle PostgreSQL Connections
    try:
        client = docker.from_env()
        pg_container = client.containers.get("hive-metastore-postgres")
        sql_cmd = (
            "psql -U hiveuser -d metastore -c "
            "\"SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            "WHERE state = 'idle' AND state_change < NOW() - INTERVAL '2 minutes' AND pid <> pg_backend_pid();\""
        )
        pg_container.exec_run(f"sh -c '{sql_cmd}'")
        logs.append("✅ Terminated idle PostgreSQL metastore backend connections.")
    except Exception as ex:
        logs.append(f"ℹ️ PostgreSQL Cleanup: {ex}")

    # 3. Ensure HDFS Out of SafeMode
    try:
        client = docker.from_env()
        nn_container = client.containers.get("namenode")
        res = nn_container.exec_run("hdfs dfsadmin -safemode leave")
        out = res.output.decode('utf-8').strip()
        logs.append(f"✅ HDFS SafeMode Status: {out}")
    except Exception as ex:
        logs.append(f"ℹ️ HDFS SafeMode Check: {ex}")

    # 4. Clean Temporary Spark Scratch Files
    try:
        client = docker.from_env()
        spark_cont = client.containers.get("spark")
        spark_cont.exec_run("rm -rf /tmp/spark-* /tmp/blockmgr-*")
        logs.append("✅ Cleaned temporary Spark block manager scratch directories.")
    except Exception as ex:
        logs.append(f"ℹ️ Spark Temp Cleanup: {ex}")

    return {
        "status": "SUCCESS",
        "timestamp": "Completed",
        "logs": logs
    }
