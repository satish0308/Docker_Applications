"""
BDP Selective Service Orchestrator & Dependency Resolver
Manages dynamic lifecycle, topological dependency resolution, operational presets, and container health.
"""

import docker
import socket
import time
import os
import subprocess
from typing import Dict, List, Set, Tuple, Any, Optional

# -------------------------------------------------------------
# SERVICE REGISTRY & METADATA
# -------------------------------------------------------------
SERVICE_REGISTRY: Dict[str, Dict[str, Any]] = {
    "postgres": {
        "name": "PostgreSQL Metastore DB",
        "container": "hive-metastore-postgres",
        "compose_service": "postgres",
        "tier": "Foundation & Metadata",
        "icon": "🐘",
        "port": 5432,
        "host": "postgres",
        "desc": "Relational backend for Hive Metastore, Hue UI, and Keycloak SSO.",
        "est_ram": "512 MB",
        "dependencies": []
    },
    "namenode": {
        "name": "HDFS NameNode",
        "container": "namenode",
        "compose_service": "namenode",
        "tier": "Foundation & Metadata",
        "icon": "📦",
        "port": 9000,
        "web_port": 9870,
        "host": "namenode",
        "desc": "Hadoop Distributed File System Master and namespace coordinator.",
        "est_ram": "1.0 GB",
        "dependencies": []
    },
    "datanode": {
        "name": "HDFS DataNode",
        "container": "datanode",
        "compose_service": "datanode",
        "tier": "Foundation & Metadata",
        "icon": "🗄️",
        "port": 9864,
        "host": "datanode",
        "desc": "HDFS block storage node for distributed delta files and datasets.",
        "est_ram": "1.0 GB",
        "dependencies": ["namenode"]
    },
    "spark": {
        "name": "Spark Master & History Server",
        "container": "spark",
        "compose_service": "spark",
        "tier": "Compute Engines",
        "icon": "⚡",
        "port": 7077,
        "web_port": 8089,
        "history_port": 18080,
        "host": "spark",
        "desc": "Apache Spark Master cluster manager, DAG scheduler, and History Server.",
        "est_ram": "2.0 GB",
        "dependencies": ["postgres", "namenode", "datanode"]
    },
    "spark-worker": {
        "name": "Spark Worker Fleet",
        "container": "spark_delta_hive_metastore-spark-worker-1",
        "compose_service": "spark-worker",
        "tier": "Compute Engines",
        "icon": "⚙️",
        "port": 8081,
        "host": "spark-worker",
        "desc": "Distributed Spark executors running compute tasks and memory caching.",
        "est_ram": "4.0 GB+",
        "dependencies": ["spark"]
    },
    "livy": {
        "name": "Apache Livy REST Server",
        "container": "livy",
        "compose_service": "livy",
        "tier": "Compute Engines",
        "icon": "🔌",
        "port": 8998,
        "host": "livy",
        "desc": "REST API service for submitting interactive Spark jobs from Hue & Jupyter.",
        "est_ram": "1.0 GB",
        "dependencies": ["spark", "spark-worker"]
    },
    "hive": {
        "name": "HiveServer2 & Metastore",
        "container": "hive-server",
        "compose_service": "hive",
        "tier": "Compute Engines",
        "icon": "🐝",
        "port": 10000,
        "host": "hive-server",
        "desc": "Hive query execution engine and Thrift metastore service.",
        "est_ram": "2.0 GB",
        "dependencies": ["postgres", "namenode", "datanode"]
    },
    "spark-thriftserver": {
        "name": "Spark Thrift Server (BI Gateway)",
        "container": "spark-thriftserver",
        "compose_service": "spark-thriftserver",
        "tier": "Compute Engines",
        "icon": "📊",
        "port": 10000,
        "host": "spark-thriftserver",
        "desc": "JDBC/ODBC gateway for BI tools (PowerBI, Tableau, DBeaver) into Spark.",
        "est_ram": "2.0 GB",
        "dependencies": ["spark", "spark-worker", "postgres", "namenode"]
    },
    "resourcemanager": {
        "name": "YARN ResourceManager",
        "container": "resourcemanager",
        "compose_service": "resourcemanager",
        "tier": "Compute Engines",
        "icon": "🐘",
        "port": 8088,
        "host": "resourcemanager",
        "desc": "YARN cluster scheduler and application lifecycle coordinator.",
        "est_ram": "1.5 GB",
        "dependencies": ["namenode", "datanode"]
    },
    "nodemanager": {
        "name": "YARN NodeManager",
        "container": "nodemanager",
        "compose_service": "nodemanager",
        "tier": "Compute Engines",
        "icon": "⚙️",
        "port": 8042,
        "host": "nodemanager",
        "desc": "YARN container execution daemon managing 20GB memory pool.",
        "est_ram": "2.0 GB+",
        "dependencies": ["resourcemanager"]
    },
    "keycloak": {
        "name": "Keycloak IAM & SSO",
        "container": "keycloak",
        "compose_service": "keycloak",
        "tier": "Security & Management",
        "icon": "🔐",
        "port": 8080,
        "host": "keycloak",
        "desc": "OpenID Connect / OAuth2 identity broker for MinIO and enterprise access.",
        "est_ram": "1.0 GB",
        "dependencies": ["postgres"]
    },
    "minio": {
        "name": "MinIO S3 Object Store",
        "container": "minio",
        "compose_service": "minio",
        "tier": "Foundation & Metadata",
        "icon": "🪣",
        "port": 9000,
        "web_port": 9001,
        "host": "minio",
        "desc": "S3-compatible high-performance object storage for delta tables and lakehouse.",
        "est_ram": "512 MB",
        "dependencies": ["keycloak"]
    },
    "hue": {
        "name": "Hue Analytics Studio",
        "container": "hue",
        "compose_service": "hue",
        "tier": "Interactive Studios",
        "icon": "🎨",
        "port": 8888,
        "web_port": 8888,
        "host": "hue",
        "desc": "Executive Web SQL studio for querying Hive, Delta Lake, and SparkSQL.",
        "est_ram": "1.5 GB",
        "dependencies": ["hive", "livy", "spark", "spark-worker", "postgres", "namenode", "datanode"]
    },
    "jupyter": {
        "name": "JupyterLab Data Science",
        "container": "jupyter-notebook",
        "compose_service": "jupyter",
        "tier": "Interactive Studios",
        "icon": "📓",
        "port": 8888,
        "web_port": 8889,
        "host": "jupyter-notebook",
        "desc": "Python/PySpark notebook workspace preconfigured with Delta Lake & S3.",
        "est_ram": "1.0 GB",
        "dependencies": ["spark", "spark-worker", "minio", "namenode", "datanode"]
    },
    "pgadmin": {
        "name": "pgAdmin 4 Console",
        "container": "pgadmin",
        "compose_service": "pgadmin",
        "tier": "Security & Management",
        "icon": "🛠️",
        "port": 80,
        "web_port": 8081,
        "host": "pgadmin",
        "desc": "Web-based graphical management interface for PostgreSQL metastore.",
        "est_ram": "300 MB",
        "dependencies": ["postgres"]
    }
}

# -------------------------------------------------------------
# OPERATIONAL PRESETS & WORKLOAD PROFILES
# -------------------------------------------------------------
OPERATIONAL_PRESETS: Dict[str, Dict[str, Any]] = {
    "⚡ Spark Minimalist / PySpark Core": {
        "desc": "Minimal lightweight cluster for batch PySpark, Delta Lake, and CLI scripts.",
        "category": "Batch ETL & Data Processing",
        "est_ram": "~4.5 GB RAM",
        "est_cores": "4 Cores",
        "spark_spec": {
            "driver_memory": "2g",
            "executor_memory": "2g",
            "executor_cores": 2,
            "shuffle_partitions": 32,
            "allocation": "Standalone Static"
        },
        "services": ["postgres", "namenode", "datanode", "spark", "spark-worker"]
    },
    "🎨 Hue Analytics Studio Profile": {
        "desc": "Full SQL querying platform with Hue Web Studio, Hive Metastore, Livy, and Spark.",
        "category": "Interactive SQL & Ad-hoc Analytics",
        "est_ram": "~9.5 GB RAM",
        "est_cores": "6 Cores",
        "spark_spec": {
            "driver_memory": "3g",
            "executor_memory": "4g",
            "executor_cores": 2,
            "shuffle_partitions": 64,
            "allocation": "Dynamic Resource Allocation (DRA)"
        },
        "services": ["postgres", "namenode", "datanode", "hive", "spark", "spark-worker", "livy", "hue"]
    },
    "📓 Data Science & Lakehouse (Jupyter + MinIO)": {
        "desc": "Interactive notebooks and S3 object storage for Lakehouse data science pipelines.",
        "category": "Data Science, ML & Lakehouse",
        "est_ram": "~7.0 GB RAM",
        "est_cores": "6 Cores",
        "spark_spec": {
            "driver_memory": "3g",
            "executor_memory": "4g",
            "executor_cores": 2,
            "shuffle_partitions": 64,
            "allocation": "Dynamic Resource Allocation (DRA)"
        },
        "services": ["postgres", "namenode", "datanode", "keycloak", "minio", "spark", "spark-worker", "jupyter"]
    },
    "🐘 YARN MapReduce & Batch Studio": {
        "desc": "Full Hadoop YARN MapReduce execution tier for large-scale distributed batch computing.",
        "category": "Hadoop YARN Distributed Computing",
        "est_ram": "~8.0 GB RAM",
        "est_cores": "8 Cores",
        "spark_spec": {
            "driver_memory": "4g",
            "executor_memory": "6g",
            "executor_cores": 4,
            "shuffle_partitions": 128,
            "allocation": "YARN Dynamic Allocation (20GB Pool)"
        },
        "services": ["postgres", "namenode", "datanode", "resourcemanager", "nodemanager", "hive"]
    },
    "📊 Spark Thrift BI Gateway Profile": {
        "desc": "Dedicated JDBC/ODBC endpoint for Tableau, PowerBI, DBeaver, and Superset.",
        "category": "Enterprise BI & JDBC/ODBC Gateway",
        "est_ram": "~6.0 GB RAM",
        "est_cores": "6 Cores",
        "spark_spec": {
            "driver_memory": "3g",
            "executor_memory": "4g",
            "executor_cores": 2,
            "shuffle_partitions": 64,
            "allocation": "Dynamic Resource Allocation (DRA)"
        },
        "services": ["postgres", "namenode", "datanode", "spark", "spark-worker", "spark-thriftserver"]
    },
    "🚀 Full Enterprise BDP Suite": {
        "desc": "All 15 distributed platform containers started in strict dependency order.",
        "category": "Full Platform Master Topology",
        "est_ram": "~16.0 GB RAM",
        "est_cores": "12 Cores",
        "spark_spec": {
            "driver_memory": "4g",
            "executor_memory": "8g",
            "executor_cores": 4,
            "shuffle_partitions": 200,
            "allocation": "DRA Enterprise Concurrency"
        },
        "services": list(SERVICE_REGISTRY.keys())
    }
}

# -------------------------------------------------------------
# DEPENDENCY RESOLVER & TOPOLOGICAL SORT
# -------------------------------------------------------------
def resolve_dependencies(selected_services: List[str]) -> List[str]:
    """
    Computes transitive closure of dependencies for selected services
    and returns a topologically sorted list (ancestors first).
    """
    all_needed: Set[str] = set()

    def add_deps(svc: str):
        if svc not in SERVICE_REGISTRY:
            return
        all_needed.add(svc)
        for dep in SERVICE_REGISTRY[svc]["dependencies"]:
            if dep not in all_needed:
                add_deps(dep)

    for svc in selected_services:
        add_deps(svc)

    # Topological Sort using DFS post-order reversal
    visited: Set[str] = set()
    order: List[str] = []

    def dfs(svc: str):
        if svc in visited:
            return
        visited.add(svc)
        for dep in SERVICE_REGISTRY.get(svc, {}).get("dependencies", []):
            if dep in all_needed:
                dfs(dep)
        order.append(svc)

    for svc in all_needed:
        dfs(svc)

    return order

def get_downstream_dependents(service_key: str, running_services: List[str]) -> List[str]:
    """
    Finds all running services that depend on service_key (directly or indirectly).
    """
    dependents: Set[str] = set()

    def find_children(parent: str):
        for svc, meta in SERVICE_REGISTRY.items():
            if parent in meta["dependencies"] and svc in running_services and svc not in dependents:
                dependents.add(svc)
                find_children(svc)

    find_children(service_key)
    return list(dependents)

# -------------------------------------------------------------
# CONTAINER MATCHING HELPER
# -------------------------------------------------------------
def find_matching_container(client: docker.DockerClient, meta: Dict[str, Any]):
    """Finds exact container matching service metadata from docker daemon."""
    if not client:
        return None
    try:
        all_containers = client.containers.list(all=True)
    except Exception:
        return None

    for cont in all_containers:
        cname = cont.name.lstrip("/")
        labels = cont.labels or {}
        compose_svc = labels.get("com.docker.compose.service", "")

        if compose_svc and compose_svc == meta["compose_service"]:
            return cont
        if cname == meta["container"] or cname == meta["compose_service"]:
            return cont
        if cname.endswith(f"-{meta['compose_service']}-1") or cname.endswith(f"_{meta['compose_service']}_1"):
            return cont
        if cname.startswith(f"{meta['compose_service']}-"):
            return cont
        if meta["container"] in cname:
            return cont
    return None

# -------------------------------------------------------------
# DOCKER LIFECYCLE & STATUS INSPECTOR
# -------------------------------------------------------------
def get_service_status_matrix() -> List[Dict[str, Any]]:
    """
    Inspects all platform services via Docker Daemon and returns live status matrix.
    """
    matrix = []
    try:
        client = docker.from_env()
    except Exception:
        client = None

    for key, meta in SERVICE_REGISTRY.items():
        matched_container = find_matching_container(client, meta) if client else None

        is_running = False
        health_stat = "N/A"
        status_label = "STOPPED"
        uptime = "Off"

        if matched_container:
            stat = matched_container.status.lower()
            if stat == "running":
                is_running = True
                status_label = "RUNNING"
                h_info = matched_container.attrs.get("State", {}).get("Health", {}).get("Status")
                if h_info:
                    health_stat = h_info.upper()
                    if h_info == "unhealthy":
                        status_label = "UNHEALTHY"
                
                # Verify internal port socket connectivity if healthy
                target_port = meta.get("port")
                target_host = meta.get("host") or meta.get("container") or meta["compose_service"]
                if target_port and isinstance(target_port, int):
                    try:
                        s = socket.create_connection((target_host, target_port), timeout=0.6)
                        s.close()
                        if health_stat == "N/A":
                            health_stat = "HEALTHY"
                    except Exception:
                        health_stat = "STARTING / UNREACHABLE"
                        status_label = "DEGRADED"
                
                started = matched_container.attrs.get("State", {}).get("StartedAt", "")
                uptime = started[:19].replace("T", " ") if started else "Running"
            elif stat == "restarting":
                status_label = "RESTARTING"
            elif stat in ["exited", "dead", "created"]:
                status_label = "STOPPED"

        matrix.append({
            "key": key,
            "name": meta["name"],
            "tier": meta["tier"],
            "icon": meta["icon"],
            "compose_service": meta["compose_service"],
            "container": meta["container"],
            "desc": meta["desc"],
            "est_ram": meta["est_ram"],
            "dependencies": meta["dependencies"],
            "is_running": is_running,
            "status": status_label,
            "health": health_stat,
            "uptime": uptime,
            "port": meta.get("web_port", meta.get("port", "N/A"))
        })

    return matrix

def get_host_workspace_dir() -> str:
    """Finds the actual host filesystem path for the workspace mount."""
    try:
        client = docker.from_env()
        for cname in ["admin-panel", "spark_delta_hive_metastore-admin-panel-1"]:
            try:
                c = client.containers.get(cname)
                for m in c.attrs.get("Mounts", []):
                    if m.get("Destination") == "/workspace":
                        return m.get("Source", "/workspace")
            except Exception:
                pass
    except Exception:
        pass
    return "/workspace"

def get_compose_base_cmd() -> List[str]:
    """Returns the robust docker compose command with correct workspace context."""
    cmd = ["docker", "compose"]
    host_ws = get_host_workspace_dir()
    if host_ws and host_ws != "/workspace":
        cmd.extend(["--project-directory", host_ws, "-f", "/workspace/docker-compose.yml"])
    elif os.path.exists("/workspace/docker-compose.yml"):
        cmd.extend(["--project-directory", "/workspace", "-f", "/workspace/docker-compose.yml"])
    elif os.path.exists("/app/docker-compose.yml"):
        cmd.extend(["-f", "/app/docker-compose.yml"])
    elif os.path.exists("docker-compose.yml"):
        cmd.extend(["-f", "docker-compose.yml"])
    return cmd

def start_services_sequential(services: List[str]) -> List[Dict[str, Any]]:
    """
    Starts a list of services in topological dependency order using existing containers.
    Auto-heals stale docker networks without attempting to create duplicate pods.
    """
    resolved_order = resolve_dependencies(services)
    results = []
    try:
        client = docker.from_env()
    except Exception as ex:
        return [{"service": s, "status": "FAILED", "msg": f"Docker connection error: {ex}"} for s in resolved_order]

    # Find the primary active hadoop network
    active_network = None
    try:
        for net in client.networks.list():
            if net.name in ["hadoop-network", "spark_delta_hive_metastore_hadoop-network", "database-net"]:
                active_network = net
                break
    except Exception:
        pass

    for svc_key in resolved_order:
        meta = SERVICE_REGISTRY.get(svc_key)
        if not meta:
            continue

        comp_name = meta["compose_service"]
        res_info = {"service": meta["name"], "key": svc_key, "status": "UNKNOWN", "msg": ""}

        # 1. Check if container already exists and start it
        matched = find_matching_container(client, meta)
        if matched:
            # Refresh status
            try:
                matched.reload()
            except Exception:
                pass

            if matched.status.lower() == "running":
                res_info["status"] = "RUNNING"
                res_info["msg"] = "Already running."
                results.append(res_info)
                continue

            # Attempt direct container start with automatic network healing
            try:
                matched.start()
                res_info["status"] = "STARTED"
                res_info["msg"] = f"Container '{matched.name}' started successfully."
                results.append(res_info)
                time.sleep(0.8)
                continue
            except Exception as start_ex:
                err_str = str(start_ex)
                # If network was recreated or missing, auto-heal connection
                if "network" in err_str.lower():
                    try:
                        if active_network:
                            try:
                                active_network.connect(matched)
                            except Exception:
                                pass
                        # Also attempt CLI network connect fallback
                        subprocess.run(["docker", "network", "connect", "hadoop-network", matched.name], capture_output=True)
                        matched.start()
                        res_info["status"] = "STARTED"
                        res_info["msg"] = f"Auto-healed network and started '{matched.name}'."
                        results.append(res_info)
                        time.sleep(0.8)
                        continue
                    except Exception as heal_ex:
                        # Try via CLI docker start
                        proc = subprocess.run(["docker", "start", matched.name], capture_output=True, text=True)
                        if proc.returncode == 0:
                            res_info["status"] = "STARTED"
                            res_info["msg"] = f"Started '{matched.name}' via Docker CLI."
                            results.append(res_info)
                            time.sleep(0.8)
                            continue
                        else:
                            res_info["status"] = "FAILED"
                            res_info["msg"] = f"Failed to start existing container: {proc.stderr.strip() or heal_ex}"
                            results.append(res_info)
                            continue
                else:
                    # Non-network error on direct start; try docker start CLI before compose
                    proc = subprocess.run(["docker", "start", matched.name], capture_output=True, text=True)
                    if proc.returncode == 0:
                        res_info["status"] = "STARTED"
                        res_info["msg"] = f"Started '{matched.name}'."
                        results.append(res_info)
                        time.sleep(0.8)
                        continue
                    else:
                        res_info["status"] = "FAILED"
                        res_info["msg"] = proc.stderr.strip() or str(start_ex)
                        results.append(res_info)
                        continue

        # 2. Only if container does NOT exist at all, create via docker compose
        try:
            compose_cmd = get_compose_base_cmd() + ["up", "-d", "--no-deps", comp_name]
            proc = subprocess.run(
                compose_cmd,
                capture_output=True,
                text=True,
                timeout=120
            )
            if proc.returncode == 0:
                res_info["status"] = "STARTED"
                res_info["msg"] = "Created and started via Docker Compose."
            else:
                # If conflict occurred, resolve by starting existing container
                err_msg = proc.stderr.strip() or proc.stdout.strip()
                if "Conflict" in err_msg or "already in use" in err_msg:
                    target_cname = meta.get("container", comp_name)
                    c_proc = subprocess.run(["docker", "start", target_cname], capture_output=True, text=True)
                    if c_proc.returncode == 0:
                        res_info["status"] = "STARTED"
                        res_info["msg"] = f"Reconnected and started existing container '{target_cname}'."
                    else:
                        res_info["status"] = "WARNING"
                        res_info["msg"] = c_proc.stderr.strip() or err_msg
                else:
                    res_info["status"] = "WARNING"
                    res_info["msg"] = err_msg
        except Exception as ex:
            res_info["status"] = "FAILED"
            res_info["msg"] = str(ex)

        results.append(res_info)
        time.sleep(0.8)

    return results

def stop_services_cascade(services: List[str], cascade: bool = True) -> List[Dict[str, Any]]:
    """
    Stops selected services and optionally stops all downstream dependents.
    """
    matrix = get_service_status_matrix()
    running_keys = [m["key"] for m in matrix if m["is_running"]]

    targets_to_stop: Set[str] = set(services)
    if cascade:
        for svc in services:
            downstream = get_downstream_dependents(svc, running_keys)
            targets_to_stop.update(downstream)

    # Reverse topological sort for stopping (children before parents)
    stop_order = resolve_dependencies(list(targets_to_stop))
    stop_order.reverse()

    results = []
    try:
        client = docker.from_env()
    except Exception as ex:
        return [{"service": s, "status": "FAILED", "msg": f"Docker connection error: {ex}"} for s in stop_order]

    for svc_key in stop_order:
        meta = SERVICE_REGISTRY.get(svc_key)
        if not meta:
            continue

        res_info = {"service": meta["name"], "key": svc_key, "status": "UNKNOWN", "msg": ""}
        try:
            matched = find_matching_container(client, meta)
            if matched and matched.status.lower() == "running":
                matched.stop(timeout=10)
                res_info["status"] = "STOPPED"
                res_info["msg"] = "Container stopped gracefully."
            else:
                compose_cmd = get_compose_base_cmd() + ["stop", meta["compose_service"]]
                subprocess.run(compose_cmd, capture_output=True, timeout=30)
                res_info["status"] = "STOPPED"
                res_info["msg"] = "Service stopped."
        except Exception as ex:
            res_info["status"] = "FAILED"
            res_info["msg"] = str(ex)

        results.append(res_info)

    return results

def restart_single_service(service_key: str) -> Tuple[bool, str]:
    """Restarts a single container by service key."""
    meta = SERVICE_REGISTRY.get(service_key)
    if not meta:
        return False, "Unknown service."
    try:
        client = docker.from_env()
        matched = find_matching_container(client, meta)
        if matched:
            matched.restart(timeout=10)
            return True, f"Restarted `{meta['name']}` successfully."
        else:
            compose_cmd = get_compose_base_cmd() + ["restart", meta["compose_service"]]
            proc = subprocess.run(
                compose_cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            return proc.returncode == 0, proc.stdout or proc.stderr
    except Exception as ex:
        return False, str(ex)
