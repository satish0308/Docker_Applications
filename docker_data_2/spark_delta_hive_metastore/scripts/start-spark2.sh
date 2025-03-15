#!/bin/bash

# Debugging: Print environment variables
echo "Using JAVA_HOME: $JAVA_HOME"
echo "Using SPARK_HOME: $SPARK_HOME"
echo "Using PATH: $PATH"
# Set environment variables for Hadoop
export HADOOP_HOME=/opt/hadoop
export PATH=$PATH:$HADOOP_HOME/bin
export HADOOP_CONF_DIR=$HADOOP_HOME/etc/hadoop

# Set environment variables for Spark
export SPARK_HOME=/home/spark
export PATH=$PATH:$SPARK_HOME/bin


# Print versions for debugging
java -version
hadoop version
spark-submit --version

# Test HDFS connectivity
echo "Testing HDFS connectivity..."
hdfs dfs -ls / || echo "HDFS command failed. Ensure NameNode is reachable."





# Validate Spark installation
if [ ! -d "$SPARK_HOME" ]; then
    echo "ERROR: Spark is not installed in $SPARK_HOME"
    exit 1
fi

# Validate Java installation
if [ ! -d "$JAVA_HOME" ]; then
    echo "ERROR: Java is not installed in $JAVA_HOME"
    exit 1
fi

# Ensure the required directories exist
mkdir -p "$SPARK_HOME/logs"
mkdir -p "$SPARK_HOME/event_logs"

# Check SPARK_MODE environment variable
if [ -z "$SPARK_MODE" ]; then
    echo "ERROR: SPARK_MODE is not set. Please set it to one of: master, worker, standalone, or jupyter."
    exit 1
fi

case "$SPARK_MODE" in
    master)
        echo "Starting Spark Master..."
        exec "$SPARK_HOME/bin/spark-class" org.apache.spark.deploy.master.Master -h 0.0.0.0
        ;;

    worker)
        if [ -z "$SPARK_MASTER_URL" ]; then
            echo "ERROR: SPARK_MASTER_URL is not set for worker mode."
            exit 1
        fi
        echo "Starting Spark Worker..."
        exec "$SPARK_HOME/bin/spark-class" org.apache.spark.deploy.worker.Worker "$SPARK_MASTER_URL"
        ;;

    standalone)
        echo "Starting Spark in standalone mode..."
        exec "$SPARK_HOME/sbin/start-all.sh"
        ;;

    jupyter)
        echo "Starting Jupyter Notebook..."
        exec jupyter notebook --ip=0.0.0.0 --no-browser --allow-root
        ;;

    *)
        echo "ERROR: Invalid SPARK_MODE: $SPARK_MODE. Supported modes: master, worker, standalone, jupyter."
        exit 1
        ;;
esac
