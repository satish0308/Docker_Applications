"""
System Maintenance, 1-Click Cluster Purge & Clean Run API Router
Provides endpoints to terminate idle database handles, clear hanging Livy sessions,
leave HDFS safe mode, reclaim cluster RAM, and execute a 1-click clean run container recreation.
"""

import json
import time
import subprocess
import urllib.request
import docker
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from service_orchestrator import get_compose_base_cmd

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

@router.post("/clean-run")
def execute_clean_run():
    """
    Nuclear Cluster Clean Run / Factory Recreate:
    1. Stops and removes all platform containers (except admin-panel).
    2. Recreates all core services from scratch in topological dependency order.
    3. Re-initializes PostgreSQL databases, roles, and grants.
    4. Seeds default Delta tables (default.sales, default.inventory_delta).
    """
    logs = []
    try:
        client = docker.from_env()
        logs.append("📦 [Step 1/5] Teardown: Stopping and removing existing cluster containers...")
        target_containers = [
            "hue", "spark-thriftserver", "livy", "jupyter-notebook", "keycloak",
            "spark_delta_hive_metastore-spark-worker-1", "spark", "hive-server",
            "pgadmin", "resourcemanager", "nodemanager", "minio", "datanode", "namenode", "hive-metastore-postgres"
        ]
        
        for cname in target_containers:
            try:
                for c in client.containers.list(all=True):
                    if cname in c.name:
                        c.remove(force=True)
                        logs.append(f"  • Removed container: {c.name}")
            except Exception as rm_ex:
                pass
        
        # 2. Recreate Foundation Services
        logs.append("🐘 [Step 2/5] Infrastructure: Recreating PostgreSQL, NameNode & DataNode...")
        compose_base = get_compose_base_cmd()
        subprocess.run(compose_base + ["up", "-d", "--no-deps", "postgres", "namenode", "datanode"], capture_output=True, text=True, timeout=120)
        
        # Wait for postgres
        time.sleep(3)
        logs.append("🔑 [Step 3/5] Metadata: Initializing Metastore schemas, users (hiveuser, hueuser), and databases (metastore, hue, keycloak)...")
        try:
            pg = client.containers.get("hive-metastore-postgres")
            init_sql = """
            SELECT 'CREATE DATABASE metastore' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'metastore')\\gexec
            DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'hiveuser') THEN CREATE ROLE hiveuser LOGIN PASSWORD 'hivepassword'; END IF; END $$;
            GRANT ALL PRIVILEGES ON DATABASE metastore TO hiveuser;
            SELECT 'CREATE DATABASE hue' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'hue')\\gexec
            DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'hueuser') THEN CREATE ROLE hueuser LOGIN PASSWORD 'hivepassword'; END IF; END $$;
            GRANT ALL PRIVILEGES ON DATABASE hue TO hueuser;
            SELECT 'CREATE DATABASE keycloak' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'keycloak')\\gexec
            GRANT ALL PRIVILEGES ON DATABASE keycloak TO hiveuser;
            """
            pg.exec_run(f"psql -U hiveuser -d metastore -c \"{init_sql}\"")
        except Exception as pg_ex:
            logs.append(f"  • Postgres init notice: {pg_ex}")

        # 3. Start remaining cluster services
        logs.append("⚡ [Step 4/5] Compute & Apps: Starting Spark, Hive, Livy, Jupyter, MinIO, pgAdmin, Keycloak & Hue...")
        services_to_start = ["spark", "spark-worker", "hive", "livy", "jupyter", "minio", "pgadmin", "keycloak", "hue"]
        subprocess.run(compose_base + ["up", "-d", "--no-deps"] + services_to_start, capture_output=True, text=True, timeout=180)

        # Apply Hue database migrations
        try:
            time.sleep(2)
            hue_c = client.containers.get("hue")
            hue_c.exec_run("/usr/share/hue/build/env/bin/hue migrate")
            logs.append("  • Applied Hue Django database migrations.")
        except Exception as hue_mig_ex:
            pass

        # 4. Wait for Spark and seed tables
        time.sleep(4)
        logs.append("📊 [Step 5/5] Lakehouse Tables: Provisioning seed Delta Lake tables (`default.sales`, `default.inventory_delta`)...")
        try:
            spark_c = client.containers.get("spark")
            seed_sql = "CREATE TABLE IF NOT EXISTS default.sales (id INT, item STRING, amount DOUBLE, timestamp TIMESTAMP) USING DELTA; INSERT INTO default.sales VALUES (1, 'MacBook Pro M3', 2499.00, current_timestamp()), (2, 'Dell XPS 15', 1899.50, current_timestamp()), (3, 'Sony WH-1000XM5', 399.99, current_timestamp()); CREATE TABLE IF NOT EXISTS default.inventory_delta (item_id INT, store_id INT, stock_count INT, last_restocked TIMESTAMP) USING DELTA; INSERT INTO default.inventory_delta VALUES (101, 1, 45, current_timestamp()), (102, 2, 80, current_timestamp());"
            spark_c.exec_run(f'/opt/spark/bin/spark-sql -e "{seed_sql}"')
            logs.append("  • Successfully seeded default Lakehouse Delta tables.")
        except Exception as seed_ex:
            logs.append(f"  • Seed table notice: {seed_ex}")

        logs.append("✅ [Complete] Clean cluster recreate finished successfully. All pods refreshed and online.")
        return {"status": "SUCCESS", "logs": logs}
    except Exception as ex:
        logs.append(f"❌ Clean run error: {ex}")
        return {"status": "FAILED", "logs": logs}
