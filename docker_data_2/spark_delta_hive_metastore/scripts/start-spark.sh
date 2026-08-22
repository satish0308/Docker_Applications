#!/bin/bash
set -e

# Environment variables
SPARK_HOME=/opt/spark
SPARK_MASTER_URL=${SPARK_MASTER_URL:-"spark://spark-master:7077"}
SPARK_MODE=${SPARK_MODE:-"worker"}  # Can be "master" or "worker"
SPARK_WORKER_CORES=${SPARK_WORKER_CORES:-1}
SPARK_WORKER_MEMORY=${SPARK_WORKER_MEMORY:-"1g"}

# Check if Spark is installed
if [ ! -d "$SPARK_HOME" ]; then
    echo "ERROR: Spark is not installed in $SPARK_HOME"
    exit 1
fi

# Start Spark Master and History Server
if [ "$SPARK_MODE" == "master" ]; then
    mkdir -p /opt/spark/event_logs
    echo "Starting Spark History Server on port 18080 in background..."
    $SPARK_HOME/bin/spark-class org.apache.spark.deploy.history.HistoryServer &
    
    echo "Starting Spark Master on host spark:7077..."
    exec $SPARK_HOME/bin/spark-class org.apache.spark.deploy.master.Master \
        --host spark \
        --port 7077 \
        --webui-port 8080
fi

# Start Spark Worker
if [ "$SPARK_MODE" == "worker" ]; then
    echo "Starting Spark Worker..."
    exec $SPARK_HOME/bin/spark-class org.apache.spark.deploy.worker.Worker \
        --cores "$SPARK_WORKER_CORES" \
        --memory "$SPARK_WORKER_MEMORY" \
        $SPARK_MASTER_URL
fi

# Start Spark Thrift Server (Shared SQL / BI Server)
if [ "$SPARK_MODE" == "thriftserver" ]; then
    echo "Starting Spark Thrift Server on port 10000 connected to $SPARK_MASTER_URL..."
    exec $SPARK_HOME/bin/spark-submit \
        --class org.apache.spark.sql.hive.thriftserver.HiveThriftServer2 \
        --master "$SPARK_MASTER_URL" \
        --name "Shared-Spark-ThriftServer" \
        --conf spark.hadoop.hive.server2.thrift.port=10000 \
        --conf spark.hadoop.hive.server2.thrift.bind.host=0.0.0.0 \
        --hiveconf hive.server2.thrift.port=10000 \
        --hiveconf hive.server2.thrift.bind.host=0.0.0.0
fi

# If unrecognized mode
echo "ERROR: Unknown SPARK_MODE $SPARK_MODE. Use 'master', 'worker', or 'thriftserver'."
exit 1
