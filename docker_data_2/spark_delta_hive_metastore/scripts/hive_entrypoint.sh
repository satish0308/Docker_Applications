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

# Ensure groups exist
groupadd -f hadoop
groupadd -f hdfs

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
  sleep 2
done

# Wait for namenode
echo "Waiting for namenode to be ready..."
until nc -z namenode 9000; do
  sleep 2
done

# Ensure HDFS is out of safemode and create directories
echo "Ensuring HDFS safemode is OFF and scratch directories exist..."
hdfs dfsadmin -safemode leave || true
hdfs dfs -mkdir -p /tmp/hive /user/hive/warehouse || true
hdfs dfs -chmod -R 777 /tmp /user || true

# Initialize Hive schema if needed
if ! schematool -info -dbType postgres > /dev/null 2>&1; then
    echo "🛠️ Initializing Hive Metastore schema..."
    schematool -initSchema -dbType postgres
fi

# Start Hive Metastore
echo "🚀 Starting Hive Metastore..."
hive --service metastore > /var/log/metastore.log 2>&1 &

# Wait for Metastore to listen on 9083
echo "Waiting for Hive Metastore on port 9083..."
until nc -z localhost 9083; do
  sleep 2
done
echo "✅ Hive Metastore is ready on port 9083."

# Start HiveServer2
echo "🚀 Starting HiveServer2..."
export HADOOP_OPTS="$HADOOP_OPTS -Xmx1024m"

exec hive --service hiveserver2
