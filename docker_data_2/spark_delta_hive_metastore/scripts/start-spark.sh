#!/bin/bash
set -e

# Environment variables
SPARK_HOME=/home/spark
SPARK_MASTER_URL=${SPARK_MASTER_URL:-"spark://spark-master:7077"}
SPARK_MODE=${SPARK_MODE:-"worker"}  # Can be "master" or "worker"
SPARK_WORKER_CORES=${SPARK_WORKER_CORES:-1}
SPARK_WORKER_MEMORY=${SPARK_WORKER_MEMORY:-"1g"}

# Check if Spark is installed
if [ ! -d "$SPARK_HOME" ]; then
    echo "ERROR: Spark is not installed in $SPARK_HOME"
    exit 1
fi

# Start Spark Master
if [ "$SPARK_MODE" == "master" ]; then
    echo "Starting Spark Master..."
    exec $SPARK_HOME/bin/spark-class org.apache.spark.deploy.master.Master \
        --host 0.0.0.0 \
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

# If unrecognized mode
echo "ERROR: Unknown SPARK_MODE $SPARK_MODE. Use 'master' or 'worker'."
exit 1
