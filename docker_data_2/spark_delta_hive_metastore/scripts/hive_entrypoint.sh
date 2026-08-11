#!/bin/bash
set -e  # Exit on error

LOG_FILE="/var/log/hadoop_entrypoint.log"
exec > >(tee -a $LOG_FILE) 2>&1  # Log all output

echo "========================================"
echo "🚀 Starting Hadoop & Hive Initialization"
echo "========================================"

# Set environment variables
export HADOOP_HOME=/home/hadoop
export PATH=$HADOOP_HOME/bin:$HADOOP_HOME/sbin:$PATH
export HADOOP_CONF_DIR=$HADOOP_HOME/etc/hadoop
export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64

# Start SSH
echo "🚀 Starting SSH service..."
service ssh start

# Wait for postgres
echo "Waiting for postgres to be ready..."
until nc -z postgres 5432; do
  sleep 5
done

# Start Hadoop services
echo "🚀 Starting Hadoop services..."
$HADOOP_HOME/sbin/start-dfs.sh

# Initialize Hive schema
if ! schematool -info -dbType postgres > /dev/null 2>&1; then
    echo "🛠️ Initializing Hive Metastore schema..."
    schematool -initSchema -dbType postgres
fi

# Start Hive Metastore
echo "🚀 Starting Hive Metastore..."
hive --service metastore > /var/log/metastore.log 2>&1 &

# Start HiveServer2
echo "🚀 Starting HiveServer2..."
export HADOOP_OPTS="$HADOOP_OPTS -Xmx1024m"

# Wait for Metastore to be ready
echo "Waiting for Metastore..."
sleep 20 

# Run in foreground
exec hive --service hiveserver2
