#!/bin/bash
set -e

LOG_FILE="/var/log/hadoop_entrypoint.log"
exec > >(tee -a $LOG_FILE) 2>&1

echo "========================================"
echo "🚀 Starting Hadoop & Hive Initialization (Robust)"
echo "========================================"

# Set environment variables
export HADOOP_HOME=/home/hadoop
export PATH=$HADOOP_HOME/bin:$HADOOP_HOME/sbin:$PATH
export HADOOP_CONF_DIR=$HADOOP_HOME/etc/hadoop
export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64

# --- Robust SSH Setup for hdfs user ---
echo "🔄 Setting up SSH for hdfs..."
service ssh start
mkdir -p /home/hdfs/.ssh
# Ensure ownership is correct
chown -R hdfs:hadoop /home/hdfs/.ssh
chmod 700 /home/hdfs/.ssh

# Generate key if missing
if [ ! -f /home/hdfs/.ssh/id_rsa ]; then
    sudo -u hdfs ssh-keygen -t rsa -b 4096 -N "" -f /home/hdfs/.ssh/id_rsa
fi

# Authorize key
cat /home/hdfs/.ssh/id_rsa.pub > /home/hdfs/.ssh/authorized_keys
chmod 600 /home/hdfs/.ssh/authorized_keys
chown hdfs:hadoop /home/hdfs/.ssh/authorized_keys
ssh-keyscan -H localhost >> /home/hdfs/.ssh/known_hosts

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

# Kill existing
pkill -f HiveServer2 || true
sleep 5

# Run in foreground
exec hive --service hiveserver2
