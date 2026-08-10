#!/bin/bash

# Directory to store downloads
DOWNLOAD_DIR="/workspaces/Docker_Applications/docker_data_2/spark_delta_hive_metastore/downloads"
mkdir -p "$DOWNLOAD_DIR"

echo "Downloading dependencies into $DOWNLOAD_DIR..."

# --- Apache Spark ---
if [ ! -f "$DOWNLOAD_DIR/spark-3.5.2-bin-hadoop3-scala2.13.tgz" ]; then
    echo "Downloading Spark 3.5.2..."
    curl -L https://archive.apache.org/dist/spark/spark-3.5.2/spark-3.5.2-bin-hadoop3-scala2.13.tgz -o "$DOWNLOAD_DIR/spark-3.5.2-bin-hadoop3-scala2.13.tgz"
fi

# --- Hadoop ---
if [ ! -f "$DOWNLOAD_DIR/hadoop-3.4.0.tar.gz" ]; then
    echo "Downloading Hadoop 3.4.0..."
    curl -L https://archive.apache.org/dist/hadoop/common/hadoop-3.4.0/hadoop-3.4.0.tar.gz -o "$DOWNLOAD_DIR/hadoop-3.4.0.tar.gz"
fi

# --- Apache Hive ---
if [ ! -f "$DOWNLOAD_DIR/apache-hive-4.0.0-bin.tar.gz" ]; then
    echo "Downloading Hive 4.0.0..."
    curl -L https://archive.apache.org/dist/hive/hive-4.0.0/apache-hive-4.0.0-bin.tar.gz -o "$DOWNLOAD_DIR/apache-hive-4.0.0-bin.tar.gz"
fi

# --- Delta Lake JARs ---
if [ ! -f "$DOWNLOAD_DIR/delta-spark_2.13-3.2.0.jar" ]; then
    echo "Downloading Delta Spark JAR..."
    curl -L https://repo1.maven.org/maven2/io/delta/delta-spark_2.13/3.2.0/delta-spark_2.13-3.2.0.jar -o "$DOWNLOAD_DIR/delta-spark_2.13-3.2.0.jar"
fi

if [ ! -f "$DOWNLOAD_DIR/delta-storage-3.2.0.jar" ]; then
    echo "Downloading Delta Storage JAR..."
    curl -L https://repo1.maven.org/maven2/io/delta/delta-storage/3.2.0/delta-storage-3.2.0.jar -o "$DOWNLOAD_DIR/delta-storage-3.2.0.jar"
fi

# --- PostgreSQL JDBC ---
if [ ! -f "$DOWNLOAD_DIR/postgresql-42.7.4.jar" ]; then
    echo "Downloading Postgres JDBC Driver..."
    curl -L https://repo1.maven.org/maven2/org/postgresql/postgresql/42.7.4/postgresql-42.7.4.jar -o "$DOWNLOAD_DIR/postgresql-42.7.4.jar"
fi

echo "All dependencies downloaded successfully."
