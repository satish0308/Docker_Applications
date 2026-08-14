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
check_service "Spark Worker UI" "spark-worker" 8081
check_service "Apache Livy" "livy" 8998
check_service "MinIO S3 API" "minio" 9000
check_service "MinIO Console" "minio" 9001
check_service "HiveServer2" "hive-server" 10000

echo ""
echo "--- Diagnostic Complete ---"
