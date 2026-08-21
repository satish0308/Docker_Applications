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
        "driver_memory": "3g",
        "executor_memory": "2g",
        "executor_cores": 2,
        "max_cores": 6,
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
    "🟠 Heavy Plus (12GB - 14GB RAM / High Concurrency)": {
        "id": "heavy_plus",
        "description": "High memory profile for 12GB - 14GB worker nodes, complex multi-table joins, and 12 total cluster cores.",
        "driver_memory": "4g",
        "executor_memory": "12g",
        "executor_cores": 4,
        "max_cores": 12,
        "shuffle_partitions": 300,
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
    """Loads active Spark tuning configuration from persistent JSON store."""
    paths = [TUNING_CONFIG_PATH, "spark_tuning_config.json", "/app/spark_tuning_config.json", "admin_panel/spark_tuning_config.json", "/app/python_scripts/spark_tuning_config.json"]
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
                
                dra_bool = params.get("dynamic_allocation", True)
                tune_map = {
                    "spark.driver.memory": str(params.get("driver_memory", "2g")),
                    "spark.executor.memory": str(params.get("executor_memory", "4g")),
                    "spark.executor.cores": str(params.get("executor_cores", 2)),
                    "spark.cores.max": str(params.get("max_cores", 4)),
                    "spark.dynamicAllocation.enabled": "true" if dra_bool else "false",
                    "spark.dynamicAllocation.shuffleTracking.enabled": "true" if dra_bool else "false",
                    "spark.dynamicAllocation.maxExecutors": str(params.get("max_cores", 12)),
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

def update_livy_conf(params):
    """Updates livy/conf/livy.conf with tuned parameters so interactive Livy sessions inherit Admin Panel tuning."""
    livy_paths = ["/app/livy/conf/livy.conf", "livy/conf/livy.conf"]
    for p in livy_paths:
        if os.path.exists(p):
            try:
                with open(p, "r") as f:
                    lines = f.readlines()
                
                dra_bool = params.get("dynamic_allocation", True)
                tune_map = {
                    "livy.spark.executor.cores": str(params.get("executor_cores", 2)),
                    "livy.spark.executor.memory": str(params.get("executor_memory", "4g")),
                    "livy.spark.cores.max": str(params.get("max_cores", 6)),
                    "livy.spark.dynamicAllocation.enabled": "true" if dra_bool else "false",
                    "livy.spark.dynamicAllocation.shuffleTracking.enabled": "true" if dra_bool else "false",
                    "livy.spark.dynamicAllocation.maxExecutors": str(params.get("max_cores", 12)),
                    "livy.spark.driver.memory": str(params.get("driver_memory", "2g"))
                }
                
                updated_lines = []
                seen_keys = set()
                for line in lines:
                    stripped = line.strip()
                    if stripped and not stripped.startswith("#") and "=" in stripped:
                        k, v = stripped.split("=", 1)
                        k = k.strip()
                        if k in tune_map:
                            updated_lines.append(f"{k} = {tune_map[k]}\n")
                            seen_keys.add(k)
                        else:
                            updated_lines.append(line)
                    else:
                        updated_lines.append(line)
                
                for k, v in tune_map.items():
                    if k not in seen_keys:
                        updated_lines.append(f"{k} = {v}\n")
                
                with open(p, "w") as f:
                    f.writelines(updated_lines)
            except Exception as e:
                print(f"Error updating Livy conf {p}: {e}")

def save_tuning_config(config_dict):
    """Saves active Spark tuning configuration, syncs spark-defaults.conf & livy.conf, and reloads Livy."""
    paths = [TUNING_CONFIG_PATH, "spark_tuning_config.json", "/app/spark_tuning_config.json", "admin_panel/spark_tuning_config.json", "/app/python_scripts/spark_tuning_config.json"]
    for p in paths:
        try:
            os.makedirs(os.path.dirname(os.path.abspath(p)), exist_ok=True)
            with open(p, "w") as f:
                json.dump(config_dict, f, indent=2)
        except Exception:
            pass
    if "params" in config_dict:
        update_spark_defaults_conf(config_dict["params"])
        update_livy_conf(config_dict["params"])
        try:
            client = docker.from_env()
            livy_c = client.containers.get("livy")
            livy_c.restart(timeout=3)
        except Exception:
            pass

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

    dra = "true" if params.get("dynamic_allocation", True) else "false"
    args = [
        f"--driver-memory {driver_mem}",
        f"--executor-memory {exec_mem}",
        f"--conf spark.executor.cores={exec_cores}",
        f"--conf spark.cores.max={max_cores}",
        f"--conf spark.dynamicAllocation.enabled={dra}",
        f"--conf spark.dynamicAllocation.shuffleTracking.enabled={dra}",
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
            sorted_workers = sorted(workers, key=lambda w: (0 if w.get("state") == "ALIVE" else 1, w.get("id", "")))
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
                    for w in sorted_workers
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

def scale_cluster_workers(target_count, worker_memory="8g", worker_cores=4):
    """Scales Spark Worker containers up or down and configures node memory & CPU capacity."""
    try:
        client = docker.from_env()
        all_workers = [
            c for c in client.containers.list(all=True)
            if ("spark-worker" in c.name or "spark_worker" in c.name)
        ]
        
        template_worker = all_workers[0] if all_workers else None
        if not template_worker:
            return "No base spark-worker container found.", 1

        image_name = template_worker.image.tags[0] if template_worker.image.tags else template_worker.image.id
        network_name = list(template_worker.attrs['NetworkSettings']['Networks'].keys())[0] if template_worker.attrs['NetworkSettings']['Networks'] else "hadoop-network"
        binds = template_worker.attrs['HostConfig']['Binds'] or []
        entrypoint = template_worker.attrs['Config']['Entrypoint'] or ["/home/sparkuser/start-spark2.sh"]

        target_env = [
            "SPARK_MODE=worker",
            "SPARK_MASTER_URL=spark://spark:7077",
            f"SPARK_WORKER_CORES={worker_cores}",
            f"SPARK_WORKER_MEMORY={worker_memory}"
        ]

        vol_map = {}
        for b in binds:
            parts = b.split(":")
            if len(parts) >= 2:
                host_p = parts[0]
                cont_p = parts[1]
                mode = parts[2] if len(parts) > 2 else "rw"
                vol_map[host_p] = {"bind": cont_p, "mode": mode}

        # Always ensure /data is mounted into every spark-worker container
        host_data_dir = "/home/satish/Docker_Applications/docker_data_2/spark_delta_hive_metastore/data"
        vol_map[host_data_dir] = {"bind": "/data", "mode": "rw"}

        # Check if existing workers need re-provisioning due to RAM or Core change
        running_workers = [c for c in all_workers if c.status == "running"]
        current_count = len(running_workers)

        # Remove all existing workers if sizing (RAM/Cores) changed
        sizing_changed = False
        for c in running_workers:
            c_env = c.attrs['Config']['Env'] or []
            if f"SPARK_WORKER_MEMORY={worker_memory}" not in c_env or f"SPARK_WORKER_CORES={worker_cores}" not in c_env:
                sizing_changed = True
                break

        if sizing_changed:
            for c in all_workers:
                try:
                    c.stop(timeout=3)
                    c.remove(force=True)
                except Exception:
                    pass
            all_workers = []
            running_workers = []
            current_count = 0

        # Launch target_count workers with requested RAM and Cores
        added = 0
        for i in range(1, target_count + 1):
            w_name = f"spark_delta_hive_metastore-spark-worker-{i}"
            w_port = 8090 + i  # Worker 1: 8091, Worker 2: 8092, Worker 3: 8093... (Avoids pgadmin on 8081)
            worker_env = target_env + [
                f"SPARK_PUBLIC_DNS=localhost",
                f"SPARK_WORKER_WEBUI_PORT=8081"
            ]
            try:
                c = client.containers.get(w_name)
                c_env = c.attrs['Config']['Env'] or []
                if c.status == "running" and f"SPARK_WORKER_MEMORY={worker_memory}" in c_env and f"SPARK_WORKER_CORES={worker_cores}" in c_env:
                    continue
                c.remove(force=True)
            except Exception:
                pass

            client.containers.run(
                image=image_name,
                name=w_name,
                detach=True,
                environment=worker_env,
                network=network_name,
                ports={"8081/tcp": w_port},
                volumes=vol_map,
                entrypoint=entrypoint
            )
            added += 1

        # Stop and remove any excess workers beyond target_count
        for i in range(target_count + 1, target_count + 20):
            w_name = f"spark_delta_hive_metastore-spark-worker-{i}"
            try:
                c = client.containers.get(w_name)
                c.remove(force=True)
            except Exception:
                pass

        return f"Successfully provisioned {target_count} worker node(s) with {worker_memory} RAM & {worker_cores} Cores each!", 0

    except Exception as e:
        return f"Error scaling workers: {str(e)}", 1
