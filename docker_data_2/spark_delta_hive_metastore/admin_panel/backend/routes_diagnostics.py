"""
Automated Multi-Port Diagnostic Prober API Router
Selectively probes network socket connectivity and latency only for active/enabled cluster services,
gracefully skipping inactive pods while highlighting degraded ports in vivid alerts.
"""

import socket
import time
import docker
from fastapi import APIRouter
from typing import List, Dict, Any, Optional
from service_orchestrator import SERVICE_REGISTRY, find_matching_container

router = APIRouter(prefix="/api/diagnostics", tags=["Cluster Diagnostics"])

PORT_DEFINITIONS = [
    {"key": "postgres", "name": "PostgreSQL Metastore DB", "host": "postgres", "port": 5432, "tier": "Foundation & Metadata", "desc": "Hive & Keycloak relational backend"},
    {"key": "namenode", "name": "HDFS NameNode IPC", "host": "namenode", "port": 9000, "tier": "Foundation & Metadata", "desc": "HDFS Distributed RPC protocol"},
    {"key": "namenode", "name": "HDFS NameNode Web UI", "host": "namenode", "port": 9870, "tier": "Foundation & Metadata", "desc": "HDFS cluster dashboard"},
    {"key": "datanode", "name": "HDFS DataNode Web UI", "host": "datanode", "port": 9864, "tier": "Foundation & Metadata", "desc": "DataNode block metrics"},
    {"key": "spark", "name": "Spark Master IPC", "host": "spark", "port": 7077, "tier": "Compute Engines", "desc": "Spark cluster execution engine"},
    {"key": "spark", "name": "Spark Master UI", "host": "spark", "port": 8080, "tier": "Compute Engines", "desc": "Spark Master Web Console"},
    {"key": "spark", "name": "Spark History Server", "host": "spark", "port": 18080, "tier": "Compute Engines", "desc": "Event log replay daemon"},
    {"key": "spark-worker", "name": "Spark Worker Node", "host": "spark-worker", "port": 8081, "tier": "Compute Engines", "desc": "Executor worker heartbeat"},
    {"key": "hive", "name": "HiveServer2 Thrift JDBC", "host": "hive-server", "port": 10000, "tier": "Foundation & Metadata", "desc": "Hive Metastore & SQL Thrift"},
    {"key": "spark-thriftserver", "name": "Spark ThriftServer JDBC", "host": "spark-thriftserver", "port": 10000, "tier": "Compute Engines", "desc": "High-throughput JDBC/ODBC"},
    {"key": "livy", "name": "Apache Livy REST Engine", "host": "livy", "port": 8998, "tier": "Interactive Analytics", "desc": "REST session gateway"},
    {"key": "jupyter", "name": "JupyterLab Data Science", "host": "jupyter-notebook", "port": 8888, "tier": "Interactive Analytics", "desc": "Interactive Python/PySpark Studio"},
    {"key": "hue", "name": "Hue Analytics Studio", "host": "hue", "port": 8888, "tier": "Interactive Analytics", "desc": "Web SQL & Metastore UI"},
    {"key": "minio", "name": "MinIO S3 API Endpoint", "host": "minio", "port": 9000, "tier": "Storage & Data", "desc": "S3-compatible Object Storage"},
    {"key": "minio", "name": "MinIO Console UI", "host": "minio", "port": 9001, "tier": "Storage & Data", "desc": "Object storage browser"},
    {"key": "pgadmin", "name": "pgAdmin 4 Console", "host": "pgadmin", "port": 80, "tier": "Interactive Analytics", "desc": "PostgreSQL database manager"},
    {"key": "keycloak", "name": "Keycloak IAM & SSO", "host": "keycloak", "port": 8080, "tier": "Security & Identity", "desc": "OAuth2 / OIDC authentication"},
    {"key": "resourcemanager", "name": "YARN ResourceManager UI", "host": "resourcemanager", "port": 8088, "tier": "Compute Engines", "desc": "Hadoop resource coordinator"},
    {"key": "nodemanager", "name": "YARN NodeManager UI", "host": "nodemanager", "port": 8042, "tier": "Compute Engines", "desc": "YARN container worker"}
]

@router.get("/probe")
@router.post("/run")
def probe_cluster_diagnostics():
    """
    Automated Prober: Dynamically inspects only currently running/enabled services.
    Returns structured health metrics, latency ms, and flags true degradations.
    """
    try:
        client = docker.from_env()
        containers = client.containers.list(all=True)
    except Exception as ex:
        return {
            "summary": {"total_probed": 0, "healthy": 0, "degraded": 0, "inactive": len(PORT_DEFINITIONS)},
            "error": f"Docker connection failed: {ex}",
            "probes": []
        }

    running_container_names = {c.name.lower(): c for c in containers if c.status.lower() == "running"}

    probes = []
    healthy_count = 0
    degraded_count = 0
    inactive_count = 0
    total_latency = 0.0
    latency_probed_count = 0

    for port_def in PORT_DEFINITIONS:
        key = port_def["key"]
        reg_meta = SERVICE_REGISTRY.get(key, {})
        matched_c = find_matching_container(client, reg_meta) if reg_meta else None
        is_running = (matched_c.status.lower() == "running") if matched_c else False

        probe_item = {
            "service_key": key,
            "name": port_def["name"],
            "host": port_def["host"],
            "port": port_def["port"],
            "tier": port_def["tier"],
            "desc": port_def["desc"],
            "is_enabled": is_running,
            "container_name": matched_c.name.lstrip("/") if matched_c else (reg_meta.get("container") or port_def["host"]),
            "status": "INACTIVE",
            "latency_ms": None,
            "error": None
        }

        if is_running:
            # Active pod: probe network socket
            t0 = time.time()
            try:
                # If container is matched, try its direct IP on hadoop-network
                target_host = port_def["host"]
                if matched_c:
                    c_nets = matched_c.attrs.get("NetworkSettings", {}).get("Networks", {})
                    ip_addr = next((n.get("IPAddress") for n in c_nets.values() if n.get("IPAddress")), None)
                    if ip_addr:
                        target_host = ip_addr

                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(1.0)
                s.connect((target_host, port_def["port"]))
                s.close()
                elapsed_ms = round((time.time() - t0) * 1000, 1)
                
                probe_item["status"] = "HEALTHY"
                probe_item["latency_ms"] = elapsed_ms
                healthy_count += 1
                total_latency += elapsed_ms
                latency_probed_count += 1
            except Exception as ex:
                probe_item["status"] = "DEGRADED"
                probe_item["error"] = str(ex)
                degraded_count += 1
        else:
            probe_item["status"] = "INACTIVE"
            probe_item["error"] = "Service not started (Disabled in Orchestrator)"
            inactive_count += 1

        probes.append(probe_item)

    avg_latency = round(total_latency / max(latency_probed_count, 1), 1) if latency_probed_count > 0 else 0.0

    return {
        "summary": {
            "total_probed": len(probes),
            "enabled_count": healthy_count + degraded_count,
            "healthy": healthy_count,
            "degraded": degraded_count,
            "inactive": inactive_count,
            "avg_latency_ms": avg_latency,
            "cluster_status": "CRITICAL" if degraded_count > 0 else ("HEALTHY" if healthy_count > 0 else "IDLE"),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        },
        "probes": probes
    }
