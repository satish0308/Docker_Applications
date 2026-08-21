#!/bin/bash
echo "--- 🚀 BDP Cluster Diagnostic Report ---"
date
echo ""

check_service() {
    name=$1
    host=$2
    port=$3
    python3 -c "
import socket, sys
try:
    s = socket.create_connection(('$host', $port), timeout=3)
    s.close()
    print('Checking $name ($host:$port)... ✅ OK')
except Exception as e:
    print('Checking $name ($host:$port)... ❌ FAILED')
"
}

check_service "PostgreSQL" "postgres" 5432
check_service "HDFS NameNode Web UI" "namenode" 9870
check_service "HDFS NameNode IPC" "namenode" 9000
check_service "HDFS DataNode Web UI" "datanode" 9864
check_service "YARN ResourceManager" "resourcemanager" 8088
check_service "YARN NodeManager" "nodemanager" 8042
check_service "Spark Master UI" "spark" 8080
check_service "Spark Master IPC" "spark" 7077
# Dynamic check for active Spark Workers
python3 -c "
import docker, socket
try:
    client = docker.from_env()
    workers = [c for c in client.containers.list() if 'spark-worker' in c.name]
    if not workers:
        print('Checking Spark Workers... ❌ NO ACTIVE WORKERS')
    for w in workers:
        ip = w.attrs['NetworkSettings']['Networks'].get('hadoop-network', {}).get('IPAddress')
        if ip:
            try:
                s = socket.create_connection((ip, 8081), timeout=3)
                s.close()
                print(f'Checking Spark Worker ({w.name}:{ip}:8081)... ✅ OK')
            except Exception:
                print(f'Checking Spark Worker ({w.name}:{ip}:8081)... ❌ FAILED')
        else:
            print(f'Checking Spark Worker ({w.name})... ✅ RUNNING')
except Exception as e:
    print(f'Checking Spark Workers... ⚠️ {e}')
"

check_service "Apache Livy" "livy" 8998
check_service "MinIO S3 API" "minio" 9000
check_service "MinIO Console" "minio" 9001
check_service "HiveServer2" "hive-server" 10000
check_service "Keycloak IAM & SSO" "keycloak" 8080

echo ""
echo "--- Diagnostic Complete ---"
