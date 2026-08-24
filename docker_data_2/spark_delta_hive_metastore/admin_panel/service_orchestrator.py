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

import yaml

# -------------------------------------------------------------
# DOCKER COMPOSE CANONICAL SCHEMA LOADER
# -------------------------------------------------------------
COMPOSE_DESCRIPTORS: Dict[str, Dict[str, Any]] = {
    "postgres": {
        "name": "PostgreSQL Metastore DB",
        "tier": "Foundation & Metadata",
        "icon": "🐘",
        "desc": "Relational backend for Hive Metastore, Hue UI, and Keycloak SSO.",
        "est_ram": "512 MB",
        "internal_port": 5432,
    },
    "namenode": {
        "name": "HDFS NameNode",
        "tier": "Foundation & Metadata",
        "icon": "📦",
        "desc": "Hadoop Distributed File System Master and namespace coordinator.",
        "est_ram": "1.0 GB",
        "internal_port": 9000,
        "primary_web_port": 9870,
    },
    "datanode": {
        "name": "HDFS DataNode",
        "tier": "Foundation & Metadata",
        "icon": "🗄️",
        "desc": "HDFS block storage node for distributed delta files and datasets.",
        "est_ram": "1.0 GB",
        "internal_port": 9864,
    },
    "spark": {
        "name": "Spark Master & History Server",
        "tier": "Compute Engines",
        "icon": "⚡",
        "desc": "Apache Spark Master cluster manager, DAG scheduler, and History Server.",
        "est_ram": "2.0 GB",
        "internal_port": 7077,
        "history_port": 18080,
    },
    "spark-worker": {
        "name": "Spark Worker Fleet",
        "tier": "Compute Engines",
        "icon": "⚙️",
        "desc": "Distributed Spark executors running compute tasks and memory caching.",
        "est_ram": "4.0 GB+",
        "internal_port": 8081,
    },
    "livy": {
        "name": "Apache Livy REST Server",
        "tier": "Compute Engines",
        "icon": "🔌",
        "desc": "REST API service for submitting interactive Spark jobs from Hue & Jupyter.",
        "est_ram": "1.0 GB",
        "internal_port": 8998,
    },
    "hive": {
        "name": "HiveServer2 & Metastore",
        "tier": "Compute Engines",
        "icon": "🐝",
        "desc": "Hive query execution engine and Thrift metastore service.",
        "est_ram": "2.0 GB",
        "internal_port": 10000,
        "primary_web_port": 10004,
    },
    "spark-thriftserver": {
        "name": "Spark Thrift Server (BI Gateway)",
        "tier": "Compute Engines",
        "icon": "📊",
        "desc": "JDBC/ODBC gateway for BI tools (PowerBI, Tableau, DBeaver) into Spark.",
        "est_ram": "2.0 GB",
        "internal_port": 10000,
    },
    "resourcemanager": {
        "name": "YARN ResourceManager",
        "tier": "Compute Engines",
        "icon": "🐘",
        "desc": "YARN cluster scheduler and application lifecycle coordinator.",
        "est_ram": "1.5 GB",
        "internal_port": 8088,
    },
    "nodemanager": {
        "name": "YARN NodeManager",
        "tier": "Compute Engines",
        "icon": "⚙️",
        "desc": "YARN container execution daemon managing 20GB memory pool.",
        "est_ram": "2.0 GB+",
        "internal_port": 8042,
    },
    "keycloak": {
        "name": "Keycloak IAM & SSO",
        "tier": "Security & Management",
        "icon": "🔐",
        "desc": "OpenID Connect / OAuth2 identity broker for MinIO and enterprise access.",
        "est_ram": "1.0 GB",
        "internal_port": 8080,
    },
    "minio": {
        "name": "MinIO S3 Object Store",
        "tier": "Foundation & Metadata",
        "icon": "🪣",
        "desc": "S3-compatible high-performance object storage for delta tables and lakehouse.",
        "est_ram": "512 MB",
        "internal_port": 9000,
        "primary_web_port": 9001,
    },
    "hue": {
        "name": "Hue Analytics Studio",
        "tier": "Interactive Studios",
        "icon": "🎨",
        "desc": "Executive Web SQL studio for querying Hive, Delta Lake, and SparkSQL.",
        "est_ram": "1.5 GB",
        "internal_port": 8888,
    },
    "jupyter": {
        "name": "JupyterLab Data Science",
        "tier": "Interactive Studios",
        "icon": "📓",
        "desc": "Python/PySpark notebook workspace preconfigured with Delta Lake & S3.",
        "est_ram": "1.0 GB",
        "internal_port": 8888,
        "primary_web_port": 8889,
    },
    "pgadmin": {
        "name": "pgAdmin 4 Console",
        "tier": "Security & Management",
        "icon": "🛠️",
        "desc": "Web-based graphical management interface for PostgreSQL metastore.",
        "est_ram": "300 MB",
        "internal_port": 80,
        "primary_web_port": 8081,
    },
}

def find_docker_compose_path() -> Optional[str]:
    """Locates the canonical docker-compose.yml file from workspace or container paths."""
    candidate_paths = [
        "/app/docker-compose.yml",
        "/workspace/docker-compose.yml",
        os.path.abspath(os.path.join(os.path.dirname(__file__), "../docker-compose.yml")),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "../../docker-compose.yml")),
        "docker-compose.yml"
    ]
    for path in candidate_paths:
        if os.path.exists(path):
            return path
    return None

def load_service_registry_from_compose() -> Dict[str, Dict[str, Any]]:
    """
    Dynamically derives all hostnames, port mappings, container names, images,
    and dependency topologies directly from docker-compose.yml.
    """
    compose_file = find_docker_compose_path()
    compose_services = {}
    if compose_file:
        try:
            with open(compose_file, "r") as f:
                data = yaml.safe_load(f) or {}
                compose_services = data.get("services", {})
        except Exception as ex:
            print(f"Warning: Failed to load docker-compose.yml: {ex}")

    registry = {}
    all_keys = list(dict.fromkeys(list(COMPOSE_DESCRIPTORS.keys()) + [k for k in compose_services.keys() if k != "admin-panel"]))

    for key in all_keys:
        svc_data = compose_services.get(key, {})
        descriptor = COMPOSE_DESCRIPTORS.get(key, {
            "name": key.capitalize(),
            "tier": "Compute Engines",
            "icon": "📦",
            "desc": f"Distributed service {key}",
            "est_ram": "1.0 GB",
            "internal_port": None
        })

        # 1. Derive Container Name
        cname = svc_data.get("container_name") or descriptor.get("container")
        if not cname:
            if key == "spark-worker":
                cname = "spark_delta_hive_metastore-spark-worker-1"
            else:
                cname = key

        # 2. Derive Hostname
        hostname = svc_data.get("hostname") or descriptor.get("host") or cname or key

        # 3. Derive Image Tag or Dockerfile
        image_spec = svc_data.get("image")
        if not image_spec:
            build_info = svc_data.get("build")
            if isinstance(build_info, dict):
                image_spec = build_info.get("dockerfile", f"spark_delta_hive_metastore-{key}")
            elif isinstance(build_info, str):
                image_spec = f"spark_delta_hive_metastore-{key}"
            else:
                image_spec = f"spark_delta_hive_metastore-{key}:latest"

        # 4. Derive Ports & Port Mappings
        raw_ports = svc_data.get("ports", [])
        port_mappings = []
        host_port = None
        container_port = None
        history_port = descriptor.get("history_port")

        for p in raw_ports:
            p_str = str(p)
            if ":" in p_str:
                parts = p_str.split(":")
                try:
                    h_p = int(parts[0])
                    c_p = int(parts[1])
                    port_mappings.append({"host": h_p, "container": c_p, "raw": p_str})
                    if h_p == 18080:
                        history_port = 18080
                    elif host_port is None:
                        host_port = h_p
                        container_port = c_p
                except ValueError:
                    port_mappings.append({"raw": p_str})
            else:
                try:
                    c_p = int(p_str)
                    port_mappings.append({"container": c_p, "raw": p_str})
                except ValueError:
                    pass

        # Select primary web_port and internal listening port
        internal_port = descriptor.get("internal_port") or container_port or host_port or 80
        web_port = descriptor.get("primary_web_port") or host_port or internal_port

        # 5. Derive Dependencies
        raw_deps = svc_data.get("depends_on", [])
        if isinstance(raw_deps, dict):
            deps = list(raw_deps.keys())
        elif isinstance(raw_deps, list):
            deps = [d if isinstance(d, str) else list(d.keys())[0] for d in raw_deps]
        else:
            deps = descriptor.get("dependencies", [])

        registry[key] = {
            "key": key,
            "name": descriptor["name"],
            "tier": descriptor["tier"],
            "icon": descriptor["icon"],
            "compose_service": key,
            "container": cname,
            "host": hostname,
            "image": image_spec,
            "port": internal_port,
            "web_port": web_port,
            "history_port": history_port,
            "ports_mapped": [pm.get("raw", "") for pm in port_mappings] if port_mappings else [f"{web_port}:{internal_port}"],
            "desc": descriptor["desc"],
            "est_ram": descriptor["est_ram"],
            "dependencies": deps
        }

    return registry

# Initialize canonical service registry from compose specification
SERVICE_REGISTRY: Dict[str, Dict[str, Any]] = load_service_registry_from_compose()

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
        if cname.endswith(f"-{meta['compose_service']}-1") or cname.endswith(f"_{meta['compose_service']}_1") or cname.endswith(f"-{meta['compose_service']}-2"):
            return cont
        if cname.startswith(f"{meta['compose_service']}-") and not cname.startswith("spark-thriftserver"):
            return cont
    return None

# -------------------------------------------------------------
# -------------------------------------------------------------
# DOCKER LIFECYCLE & STATUS INSPECTOR
# -------------------------------------------------------------
def inspect_single_service(key: str, meta: Dict[str, Any], client: Optional[docker.DockerClient]) -> Dict[str, Any]:
    """Inspects a single service status quickly without blocking DNS lookups."""
    matched_container = find_matching_container(client, meta) if client else None

    is_running = False
    health_stat = "N/A"
    status_label = "STOPPED"
    uptime = "Off"

    if matched_container:
        try:
            stat = matched_container.status.lower()
            if stat == "running":
                is_running = True
                status_label = "RUNNING"
                h_info = matched_container.attrs.get("State", {}).get("Health", {}).get("Status")
                if h_info:
                    health_stat = h_info.upper()
                    if h_info == "unhealthy":
                        status_label = "UNHEALTHY"

                # Check port responsiveness directly using container IP and internal listening port
                target_port = meta.get("port")
                if target_port and isinstance(target_port, int) and health_stat != "UNHEALTHY":
                    c_nets = matched_container.attrs.get("NetworkSettings", {}).get("Networks", {})
                    ip_addr = next((n.get("IPAddress") for n in c_nets.values() if n.get("IPAddress")), None)
                    check_target = ip_addr or meta.get("host") or meta["compose_service"]

                    try:
                        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        s.settimeout(0.2) # 200ms max
                        s.connect((check_target, target_port))
                        s.close()
                        if health_stat == "N/A":
                            health_stat = "HEALTHY"
                    except Exception:
                        health_stat = "STARTING / UNREACHABLE"
                        status_label = "DEGRADED"
                        is_running = False

                started = matched_container.attrs.get("State", {}).get("StartedAt", "")
                uptime = started[:19].replace("T", " ") if started else "Running"
            elif stat == "restarting":
                status_label = "RESTARTING"
            elif stat in ["exited", "dead", "created"]:
                status_label = "STOPPED"
        except Exception:
            pass

    return {
        "key": key,
        "name": meta["name"],
        "tier": meta["tier"],
        "icon": meta["icon"],
        "compose_service": meta["compose_service"],
        "container": meta["container"],
        "host": meta.get("host", meta["compose_service"]),
        "image": meta.get("image", "N/A"),
        "ports_mapped": meta.get("ports_mapped", []),
        "desc": meta["desc"],
        "est_ram": meta["est_ram"],
        "dependencies": meta["dependencies"],
        "is_running": is_running,
        "status": status_label,
        "health": health_stat,
        "uptime": uptime,
        "port": meta.get("web_port", meta.get("port", "N/A"))
    }

def get_service_status_matrix() -> List[Dict[str, Any]]:
    """
    Inspects all platform services concurrently via Docker Daemon and returns live status matrix in <50ms.
    Dynamically syncs with docker-compose.yml on every inspection.
    """
    try:
        client = docker.from_env()
    except Exception:
        client = None

    active_registry = load_service_registry_from_compose()

    import concurrent.futures
    matrix = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        futures = {executor.submit(inspect_single_service, k, meta, client): k for k, meta in active_registry.items()}
        for future in concurrent.futures.as_completed(futures):
            try:
                matrix.append(future.result())
            except Exception:
                pass

    # Maintain original registry ordering
    order_map = {k: idx for idx, k in enumerate(active_registry.keys())}
    matrix.sort(key=lambda x: order_map.get(x["key"], 999))
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
