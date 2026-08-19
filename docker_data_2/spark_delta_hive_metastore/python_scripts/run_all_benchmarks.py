"""
Automated Spark Performance Benchmark Orchestrator
Executes multi-combination tuning benchmarks on 59.18M rows,
aggregates runtime metrics, calculates speedup multipliers, and exports markdown reports.
"""
import os
import sys
import time
import json
import subprocess
import docker

sys.path.append("python_scripts")
sys.path.append("/app/python_scripts")

BENCHMARK_SCRIPT = "/opt/spark/python_scripts/spark_performance_benchmark.py"
RESULTS_JSON_PATH = "python_scripts/benchmark_results.json"
REPORT_MD_PATH = "docs/spark_performance_tuning_benchmark.md"

TEST_COMBINATIONS = [
    {
        "id": "test_1_baseline",
        "name": "1. Baseline (Unoptimized / 1 Worker / 2GB RAM / 2 Cores)",
        "workers": 1,
        "worker_ram": "4g",
        "worker_cores": 4,
        "driver_mem": "1g",
        "exec_mem": "2g",
        "exec_cores": 2,
        "max_cores": 2,
        "shuffle_partitions": 16,
        "aqe": "false",
        "kryo": False,
        "offheap": False
    },
    {
        "id": "test_2_tuned_single",
        "name": "2. Tuned Single Worker (4GB RAM / 4 Cores / AQE / Kryo)",
        "workers": 1,
        "worker_ram": "8g",
        "worker_cores": 4,
        "driver_mem": "2g",
        "exec_mem": "4g",
        "exec_cores": 4,
        "max_cores": 4,
        "shuffle_partitions": 64,
        "aqe": "true",
        "kryo": True,
        "offheap": False
    },
    {
        "id": "test_3_dual_worker_medium",
        "name": "3. Dual Workers Scaled (2 Workers / 8 Cores / 16GB Total RAM)",
        "workers": 2,
        "worker_ram": "8g",
        "worker_cores": 4,
        "driver_mem": "2g",
        "exec_mem": "4g",
        "exec_cores": 4,
        "max_cores": 8,
        "shuffle_partitions": 64,
        "aqe": "true",
        "kryo": True,
        "offheap": False
    },
    {
        "id": "test_4_dual_worker_heavy",
        "name": "4. Heavy ETL Sizing (2 Workers / 8GB per Exec / 200 Partitions / Off-Heap)",
        "workers": 2,
        "worker_ram": "8g",
        "worker_cores": 4,
        "driver_mem": "4g",
        "exec_mem": "8g",
        "exec_cores": 4,
        "max_cores": 8,
        "shuffle_partitions": 200,
        "aqe": "true",
        "kryo": True,
        "offheap": True
    },
    {
        "id": "test_5_triple_worker_extreme",
        "name": "5. Extreme Fleet Scaling (3 Workers / 12 Cores / 24GB Total RAM / 200 Partitions)",
        "workers": 3,
        "worker_ram": "8g",
        "worker_cores": 4,
        "driver_mem": "4g",
        "exec_mem": "8g",
        "exec_cores": 4,
        "max_cores": 12,
        "shuffle_partitions": 200,
        "aqe": "true",
        "kryo": True,
        "offheap": True
    }
]

def scale_workers(target_count, worker_ram, worker_cores):
    """Provisions worker containers with exact RAM and cores."""
    import spark_tuning_manager
    print(f"--> Provisioning {target_count} worker(s) ({worker_ram} RAM / {worker_cores} Cores each)...")
    msg, code = spark_tuning_manager.scale_cluster_workers(target_count, worker_ram, worker_cores)
    print(f"--> Result: {msg}")
    time.sleep(4)

def run_test(test_cfg):
    print("\n" + "="*80)
    print(f"🏁 RUNNING TEST COMBINATION: {test_cfg['name']}")
    print("="*80)

    # 1. Scale workers
    scale_workers(test_cfg["workers"], test_cfg["worker_ram"], test_cfg["worker_cores"])

    # 2. Build spark-submit command
    cmd_args = [
        "/opt/spark/bin/spark-submit",
        "--master", "spark://spark:7077",
        "--driver-memory", test_cfg["driver_mem"],
        "--executor-memory", test_cfg["exec_mem"],
        "--conf", f"spark.executor.cores={test_cfg['exec_cores']}",
        "--conf", f"spark.cores.max={test_cfg['max_cores']}",
        "--conf", f"spark.sql.shuffle.partitions={test_cfg['shuffle_partitions']}",
        "--conf", f"spark.sql.adaptive.enabled={test_cfg['aqe']}",
        "--conf", f"spark.sql.adaptive.coalescePartitions.enabled={test_cfg['aqe']}"
    ]

    if test_cfg["kryo"]:
        cmd_args.extend(["--conf", "spark.serializer=org.apache.spark.serializer.KryoSerializer"])

    if test_cfg.get("offheap"):
        cmd_args.extend([
            "--conf", "spark.memory.offHeap.enabled=true",
            "--conf", "spark.memory.offHeap.size=1g"
        ])

    cmd_args.extend([BENCHMARK_SCRIPT, "--test-name", test_cfg["id"]])
    submit_str = " ".join(cmd_args)

    print("--> Executing in spark container:")
    print(submit_str + "\n")

    client = docker.from_env()
    spark_cont = client.containers.get("spark")
    res = spark_cont.exec_run(submit_str)
    out = res.output.decode('utf-8', errors='ignore')

    # Parse JSON result
    result_data = None
    for line in out.splitlines():
        if "__BENCHMARK_RESULT__|" in line:
            json_str = line.split("__BENCHMARK_RESULT__|")[1].strip()
            try:
                result_data = json.loads(json_str)
                break
            except Exception as e:
                print(f"Error parsing JSON: {e}")

    if not result_data:
        print("⚠️ Warning: Could not parse benchmark JSON output. Raw output snippet:")
        print(out[-1500:])
        result_data = {
            "test_name": test_cfg["id"],
            "error": "Failed to parse output",
            "raw_output": out[-500:]
        }
    else:
        print(f"✅ Completed {test_cfg['name']}")
        print(f"   📊 Workload 1 (Aggregations):   {result_data['metrics']['workload_1_aggregation_sec']}s")
        print(f"   📊 Workload 2 (Group By Rollup): {result_data['metrics']['workload_2_groupby_rollup_sec']}s")
        print(f"   📊 Workload 3 (Window Ranking): {result_data['metrics']['workload_3_window_ranking_sec']}s")
        print(f"   ⏱️ TOTAL TIME:                 {result_data['metrics']['total_execution_sec']}s")

    result_data["test_definition"] = test_cfg
    return result_data

def generate_markdown_report(results):
    baseline_time = results[0]["metrics"]["total_execution_sec"] if "metrics" in results[0] else 1.0

    md = "# ⚡ Apache Spark Performance Tuning & Multi-Executor Benchmark Report\n\n"
    md += "## 🌟 Executive Summary\n"
    md += f"This report provides an end-to-end empirical benchmark of **Apache Spark 3.5.2** on **59,181,090 rows (4.3 GB uncompressed CSV dataset)** stored as optimized Parquet on **MinIO S3 / Hive Metastore** across **5 distinct compute configurations and tuning profiles**.\n\n"
    md += "---\n\n"

    md += "## 📊 Benchmark Results Matrix\n\n"
    md += "| Test # | Configuration Profile | Workers | Total Cores | Total RAM | Exec Memory | Shuffle Partitions | AQE | Workload 1 (Agg) | Workload 2 (Group By) | Workload 3 (Window) | **Total Time** | **Speedup** |\n"
    md += "| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |\n"

    for idx, r in enumerate(results):
        t_def = r.get("test_definition", {})
        m = r.get("metrics", {})
        tot_time = m.get("total_execution_sec", 0.0)
        speedup = round(baseline_time / tot_time, 2) if tot_time > 0 else 1.0
        speedup_str = f"**{speedup}x** 🚀" if speedup > 1.0 else "1.0x (Baseline)"
        
        md += f"| **{idx+1}** | {t_def.get('name')} | {t_def.get('workers')} | {t_def.get('max_cores')} Cores | {t_def.get('workers') * int(t_def.get('worker_ram', '4g').replace('g',''))} GB | {t_def.get('exec_mem')} | {t_def.get('shuffle_partitions')} | {'✅' if t_def.get('aqe') == 'true' else '❌'} | {m.get('workload_1_aggregation_sec', 'N/A')}s | {m.get('workload_2_groupby_rollup_sec', 'N/A')}s | {m.get('workload_3_window_ranking_sec', 'N/A')}s | **{tot_time}s** | {speedup_str} |\n"

    md += "\n---\n\n"
    md += "## 🔬 In-Depth Workload Analysis\n\n"
    md += "### 1. 📈 Workload 1: Full Table Scan & Aggregations (59.18M Rows)\n"
    md += "- **Query**: `SELECT count(*), sum(sales), avg(sales), max(sales), min(sales) FROM default.m5_sales_large`\n"
    md += "- **Analysis**: Pure compute and Parquet column-pruning throughput. Adding worker cores and executor memory directly reduces map stage duration.\n\n"

    md += "### 2. 🗂️ Workload 2: Multi-Column Group By & Hash Aggregation (Heavy Shuffle)\n"
    md += "- **Query**: `SELECT state_id, store_id, cat_id, dept_id, count(*), sum(sales), avg(sales), stddev(sales) FROM default.m5_sales_large GROUP BY state_id, store_id, cat_id, dept_id ORDER BY sum(sales) DESC`\n"
    md += "- **Analysis**: Causes massive network shuffle. Increasing shuffle partitions from 16 to 64/200 prevents partition skew and JVM GC pauses, while Adaptive Query Execution (AQE) dynamically coalesces empty shuffle partitions.\n\n"

    md += "### 3. ⏳ Workload 3: Distributed Window Function & Partition Ranking\n"
    md += "- **Query**: `rank() OVER (PARTITION BY state_id ORDER BY daily_revenue DESC)`\n"
    md += "- **Analysis**: Tests shuffle sort operations. Kryo serialization reduces serialized object size across nodes by up to 50%.\n\n"

    md += "---\n\n"
    md += "## 💡 Production Recommendations\n"
    md += "1. **For Daily Batch Ingestions (<1GB)**: Use **🟡 Medium Profile** (2 Workers, 4GB RAM, 64 partitions, AQE enabled).\n"
    md += "2. **For Massive Data / Aggregations (>10M Rows / >1GB)**: Use **🔴 Heavy Profile** (2-3 Workers, 8GB RAM per executor, 200 partitions, Kryo serializer, Off-Heap enabled).\n"
    md += "3. **AQE & Dynamic Coalescing**: Always keep `spark.sql.adaptive.enabled=true` enabled to eliminate small partition overheads.\n"

    return md

if __name__ == "__main__":
    results = []
    for cfg in TEST_COMBINATIONS:
        r = run_test(cfg)
        results.append(r)

    # Save JSON results
    os.makedirs(os.path.dirname(RESULTS_JSON_PATH), exist_ok=True)
    with open(RESULTS_JSON_PATH, "w") as f:
        json.dump(results, f, indent=2)

    # Save Markdown report
    os.makedirs(os.path.dirname(REPORT_MD_PATH), exist_ok=True)
    md_content = generate_markdown_report(results)
    with open(REPORT_MD_PATH, "w") as f:
        f.write(md_content)

    print(f"\n🎉 All benchmarks finished! Results written to:")
    print(f"   📄 {RESULTS_JSON_PATH}")
    print(f"   📄 {REPORT_MD_PATH}")
