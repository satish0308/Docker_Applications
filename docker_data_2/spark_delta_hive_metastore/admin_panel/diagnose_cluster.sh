#!/bin/bash
echo "--- BDP Cluster Diagnostic Report ---"
date
echo ""

check_service() {
    name=$1
    host=$2
    port=$3
    echo -n "Checking $name ($host:$port)... "
    if nc -zv "$host" "$port" &>/dev/null; then
        echo "✅ OK"
    else
        echo "❌ FAILED"
    fi
}

check_service "PostgreSQL" "postgres" 5432
check_service "NameNode" "namenode" 9870
check_service "ResourceManager" "resourcemanager" 8088
check_service "Spark Master" "spark" 7077
check_service "Spark History" "spark" 18080
check_service "Livy" "livy" 8998
check_service "HiveServer2" "hive-server" 10000

echo ""
echo "--- Diagnostic Complete ---"
