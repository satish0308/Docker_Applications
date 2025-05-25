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
export JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64  # Ensure this path is correct

echo "✅ Environment Variables Set:"
echo "HADOOP_HOME: $HADOOP_HOME"
echo "PATH: $PATH"
echo "HADOOP_CONF_DIR: $HADOOP_CONF_DIR"
echo "JAVA_HOME: $JAVA_HOME"

# Ensure /home/hdfs/.ssh exists
if [ ! -d /home/hdfs/.ssh ]; then
    echo "📁 Creating /home/hdfs/.ssh directory..."
    mkdir -p /home/hdfs/.ssh
    chown hdfs:hdfs /home/hdfs/.ssh
    chmod 700 /home/hdfs/.ssh
fi

# Generate SSH key for hdfs user if not exists
if [ ! -f /home/hdfs/.ssh/id_rsa ]; then
    echo "🔑 Generating SSH key for hdfs user..."
    sudo -u hdfs ssh-keygen -t rsa -b 4096 -N "" -f /home/hdfs/.ssh/id_rsa
fi

# Ensure public key is in authorized_keys
if ! grep -q "$(cat /home/hdfs/.ssh/id_rsa.pub)" /home/hdfs/.ssh/authorized_keys 2>/dev/null; then
    echo "🔑 Adding SSH public key to authorized_keys..."
    sudo -u hdfs cat /home/hdfs/.ssh/id_rsa.pub >> /home/hdfs/.ssh/authorized_keys
fi

# Set proper permissions
echo "🔧 Setting correct permissions for SSH access..."
chown -R hdfs:hdfs /home/hdfs/.ssh
chmod 700 /home/hdfs/.ssh
chmod 600 /home/hdfs/.ssh/authorized_keys

# Ensure SSH service is running
echo "🚀 Starting SSH service..."
service ssh start

# Validate passwordless SSH for hdfs user
echo "🔄 Testing passwordless SSH for hdfs user..."
if ! sudo -u hdfs ssh -o StrictHostKeyChecking=no localhost exit; then
    echo "❌ ERROR: SSH setup for hdfs user failed. Check permissions!"
    exit 1
else
    echo "✅ Passwordless SSH setup successful for hdfs user!"
fi

# Start Hadoop services
echo "🚀 Starting Hadoop services..."
$HADOOP_HOME/sbin/start-dfs.sh

# Check Hadoop version
echo "🔍 Checking Hadoop version..."
hdfs version

# Ensure correct permissions for Hive Warehouse Directory
echo "🗄️ Setting permissions for Hive warehouse directory..."
hdfs dfs -mkdir -p /user/hive/warehouse
hdfs dfs -chown -R hive:hdfs /user/hive/warehouse
hdfs dfs -chmod -R 777 /user/hive/warehouse
echo "✅ Hive warehouse permissions set!"

# Initialize Hive schema if needed
if ! schematool -info -dbType postgres > /dev/null 2>&1; then
    echo "🛠️ Initializing Hive Metastore schema..."
    schematool -initSchema -dbType postgres
else
    echo "✅ Hive Metastore schema already initialized."
fi

# Start Hive Metastore & HiveServer2
echo "🚀 Starting Hive Metastore..."
hive --service metastore &

echo "🚀 Starting HiveServer2..."
hive --service hiveserver2 &

# Keep the container running
echo "✅ Hadoop & Hive startup complete. Container is running..."
tail -f /dev/null
