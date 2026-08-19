"""
Spark Tuning & Dynamic Resource Management Engine
Supports:
1. Workload Sizing Profiles (Light, Medium, Heavy, Extreme, Custom)
2. Fine-grained parameter tuning (Driver/Executor RAM, Cores, AQE, Off-Heap, Shuffle Partitions, Kryo)
3. Dynamic spark-submit argument generator
4. Live horizontal worker cluster scaling via Docker API
5. Live Spark Master cluster capacity monitoring
6. Dynamic spark-defaults.conf persistence
"""
import os
import json
import urllib.request
import docker

TUNING_CONFIG_PATH = "/app/spark_tuning_config.json"
SPARK_DEFAULTS_CONF_PATH = "/app/config/spark-defaults.conf"
HOST_SPARK_DEFAULTS_PATH = "config/spark-defaults.conf"

PROFILES = {
    "🟢 Light (Small Files / Interactive)": {
        "id": "light",
        "description": "Optimized for <100MB files, exploration & interactive testing with minimal resource footprint.",
        "driver_memory": "1g",
        "executor_memory": "2g",
        "executor_cores": 1,
        "max_cores": 2,
        "shuffle_partitions": 8,
        "aqe_enabled": False,
        "aqe_coalesce": False,
        "memory_fraction": 0.6,
        "storage_fraction": 0.5,
        "offheap_enabled": False,
        "offheap_size": "0",
        "kryo_serializer": False
    },
    "🟡 Medium (Standard ETL / Daily Batches)": {
        "id": "medium",
        "description": "Recommended for 100MB - 1GB files, multi-partition datasets with Adaptive Query Execution enabled.",
        "driver_memory": "2g",
        "executor_memory": "4g",
        "executor_cores": 2,
        "max_cores": 4,
        "shuffle_partitions": 64,
        "aqe_enabled": True,
        "aqe_coalesce": True,
        "memory_fraction": 0.7,
        "storage_fraction": 0.5,
        "offheap_enabled": False,
        "offheap_size": "0",
        "kryo_serializer": True
    },
    "🔴 Heavy (Large Big Data / >10M Rows)": {
        "id": "heavy",
        "description": "Engineered for 1GB - 10GB+ tables, 10M+ rows, heavy joins/aggregations and zero-OOM protection.",
        "driver_memory": "4g",
        "executor_memory": "8g",
        "executor_cores": 4,
        "max_cores": 8,
        "shuffle_partitions": 200,
        "aqe_enabled": True,
        "aqe_coalesce": True,
        "memory_fraction": 0.8,
        "storage_fraction": 0.4,
        "offheap_enabled": True,
        "offheap_size": "1g",
        "kryo_serializer": True
    },
    "🚀 Extreme (Petabyte Scale / High Throughput)": {
        "id": "extreme",
        "description": "Maximum horsepower for multi-gigabyte or massive partition fan-outs with 400+ partitions and aggressive caching.",
        "driver_memory": "8g",
        "executor_memory": "16g",
        "executor_cores": 8,
        "max_cores": 16,
        "shuffle_partitions": 400,
        "aqe_enabled": True,
        "aqe_coalesce": True,
        "memory_fraction": 0.85,
        "storage_fraction": 0.3,
        "offheap_enabled": True,
        "offheap_size": "2g",
        "kryo_serializer": True
    }
}

def load_tuning_config():
    """Loads active Spark tuning configuration or returns default medium profile."""
    paths = [TUNING_CONFIG_PATH, "spark_tuning_config.json", "/app/python_scripts/spark_tuning_config.json"]
    for p in paths:
        if os.path.exists(p):
            try:
                with open(p, "r") as f:
                    return json.load(f)
            except Exception:
                pass
    return {
        "active_profile": "🟡 Medium (Standard ETL / Daily Batches)",
        "params": PROFILES["🟡 Medium (Standard ETL / Daily Batches)"]
    }

def update_spark_defaults_conf(params):
    """Updates config/spark-defaults.conf with tuned parameters."""
    conf_paths = ["/app/config/spark-defaults.conf", "config/spark-defaults.conf"]
    for p in conf_paths:
        if os.path.exists(p):
            try:
                with open(p, "r") as f:
                    lines = f.readlines()
                
                tune_map = {
                    "spark.driver.memory": str(params.get("driver_memory", "2g")),
                    "spark.executor.memory": str(params.get("executor_memory", "4g")),
                    "spark.executor.cores": str(params.get("executor_cores", 2)),
                    "spark.cores.max": str(params.get("max_cores", 4)),
                    "spark.sql.shuffle.partitions": str(params.get("shuffle_partitions", 64)),
                    "spark.sql.adaptive.enabled": "true" if params.get("aqe_enabled", True) else "false",
                    "spark.sql.adaptive.coalescePartitions.enabled": "true" if params.get("aqe_coalesce", True) else "false",
                    "spark.memory.fraction": str(params.get("memory_fraction", 0.7)),
                    "spark.memory.storageFraction": str(params.get("storage_fraction", 0.5))
                }
                
                updated_lines = []
                seen_keys = set()
                for line in lines:
                    stripped = line.strip()
                    if stripped and not stripped.startswith("#") and "=" in stripped:
                        k, v = stripped.split("=", 1)
                        k = k.strip()
                        if k in tune_map:
                            updated_lines.append(f"{k}={tune_map[k]}\n")
                            seen_keys.add(k)
                        else:
                            updated_lines.append(line)
                    else:
                        updated_lines.append(line)
                
                for k, v in tune_map.items():
                    if k not in seen_keys:
                        updated_lines.append(f"{k}={v}\n")
                
                with open(p, "w") as f:
                    f.writelines(updated_lines)
            except Exception as e:
                print(f"Error updating {p}: {e}")

def save_tuning_config(config_dict):
    """Saves active Spark tuning configuration and syncs spark-defaults.conf."""
    paths = [TUNING_CONFIG_PATH, "spark_tuning_config.json", "/app/python_scripts/spark_tuning_config.json"]
    for p in paths:
        try:
            os.makedirs(os.path.dirname(os.path.abspath(p)), exist_ok=True)
            with open(p, "w") as f:
                json.dump(config_dict, f, indent=2)
        except Exception:
            pass
    if "params" in config_dict:
        update_spark_defaults_conf(config_dict["params"])

def recommend_profile_for_filesize(size_in_bytes):
    """Recommends an optimal Spark profile based on uploaded dataset size."""
    mb = size_in_bytes / (1024 * 1024)
    if mb < 100:
        return "🟢 Light (Small Files / Interactive)", mb
    elif mb < 1024:
        return "🟡 Medium (Standard ETL / Daily Batches)", mb
    elif mb < 10240:
        return "🔴 Heavy (Large Big Data / >10M Rows)", mb
    else:
        return "🚀 Extreme (Petabyte Scale / High Throughput)", mb

def build_spark_submit_conf_args(params):
    """Builds CLI --conf arguments string for spark-submit based on params dictionary."""
    driver_mem = params.get("driver_memory", "2g")
    exec_mem = params.get("executor_memory", "3g")
    exec_cores = params.get("executor_cores", 2)
    max_cores = params.get("max_cores", 4)
    shuffle_parts = params.get("shuffle_partitions", 64)
    aqe = "true" if params.get("aqe_enabled", True) else "false"
    aqe_coalesce = "true" if params.get("aqe_coalesce", True) else "false"
    mem_frac = params.get("memory_fraction", 0.7)
    storage_frac = params.get("storage_fraction", 0.5)
    offheap = "true" if params.get("offheap_enabled", False) else "false"
    offheap_sz = params.get("offheap_size", "0")
    kryo = params.get("kryo_serializer", True)

    args = [
        f"--driver-memory {driver_mem}",
        f"--executor-memory {exec_mem}",
        f"--conf spark.executor.cores={exec_cores}",
        f"--conf spark.cores.max={max_cores}",
        f"--conf spark.sql.shuffle.partitions={shuffle_parts}",
        f"--conf spark.sql.adaptive.enabled={aqe}",
        f"--conf spark.sql.adaptive.coalescePartitions.enabled={aqe_coalesce}",
        f"--conf spark.memory.fraction={mem_frac}",
        f"--conf spark.memory.storageFraction={storage_frac}"
    ]

    if offheap == "true" and offheap_sz != "0":
        args.append(f"--conf spark.memory.offHeap.enabled=true")
        args.append(f"--conf spark.memory.offHeap.size={offheap_sz}")

    if kryo:
        args.append(f"--conf spark.serializer=org.apache.spark.serializer.KryoSerializer")

    return " ".join(args)

def get_spark_master_metrics():
    """Queries Spark Master JSON API to retrieve real-time cluster compute metrics."""
    endpoints = ["http://spark:8080/json/", "http://localhost:8089/json/"]
    for ep in endpoints:
        try:
            req = urllib.request.urlopen(ep, timeout=3)
            data = json.loads(req.read().decode('utf-8'))
            workers = data.get("workers", [])
            alive_workers = [w for w in workers if w.get("state") == "ALIVE"]
            total_cores = data.get("cores", 0)
            cores_used = data.get("coresused", 0)
            total_mem = data.get("memory", 0)
            mem_used = data.get("memoryused", 0)
            active_apps = data.get("activeapps", [])
            return {
                "status": "connected",
                "master_url": data.get("url", "spark://spark:7077"),
                "total_workers": len(workers),
                "alive_workers": len(alive_workers),
                "total_cores": total_cores,
                "cores_used": cores_used,
                "cores_free": max(0, total_cores - cores_used),
                "total_memory_mb": total_mem,
                "memory_used_mb": mem_used,
                "memory_free_mb": max(0, total_mem - mem_used),
                "active_apps_count": len(active_apps),
                "active_apps": active_apps,
                "worker_list": [
                    {
                        "Worker ID": w.get("id", ""),
                        "Host": w.get("host", ""),
                        "Cores": w.get("cores", 0),
                        "Cores Used": w.get("coresused", 0),
                        "Memory (MB)": w.get("memory", 0),
                        "Memory Used (MB)": w.get("memoryused", 0),
                        "State": "🟢 " + w.get("state", "") if w.get("state") == "ALIVE" else "🔴 " + w.get("state", "")
                    }
                    for w in workers
                ]
            }
        except Exception:
            pass
    return {
        "status": "disconnected",
        "master_url": "spark://spark:7077",
        "total_workers": 0,
        "alive_workers": 0,
        "total_cores": 0,
        "cores_used": 0,
        "cores_free": 0,
        "total_memory_mb": 0,
        "memory_used_mb": 0,
        "memory_free_mb": 0,
        "active_apps_count": 0,
        "active_apps": [],
        "worker_list": []
    }

def scale_cluster_workers(target_count):
    """Scales Spark Worker containers up or down via Docker socket."""
    client = docker.from_env()
    existing_workers = [
        c for c in client.containers.list(all=True)
        if "spark-worker" in c.name or "spark_worker" in c.name
    ]
    current_count = len([c for c in existing_workers if c.status == "running"])

    if target_count == current_count:
        return f"Cluster is already running at {target_count} worker(s).", 0

    import subprocess
    cmd = f"docker compose up -d --scale spark-worker={target_count}"
    proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return proc.stdout + proc.stderr, proc.returncode
