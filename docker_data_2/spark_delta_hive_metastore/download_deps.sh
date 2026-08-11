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

# --- Apache Livy ---
if [ ! -f "$DOWNLOAD_DIR/apache-livy-0.8.0-incubating-bin.tar.gz" ]; then
    echo "Downloading Livy 0.8.0..."
    curl -L https://archive.apache.org/dist/incubator/livy/0.8.0-incubating/apache-livy-0.8.0-incubating-bin.tar.gz -o "$DOWNLOAD_DIR/apache-livy-0.8.0-incubating-bin.tar.gz"
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

# --- JDBC Drivers ---
if [ ! -f "$DOWNLOAD_DIR/postgresql-42.7.4.jar" ]; then
    echo "Downloading Postgres JDBC Driver..."
    curl -L https://repo1.maven.org/maven2/org/postgresql/postgresql/42.7.4/postgresql-42.7.4.jar -o "$DOWNLOAD_DIR/postgresql-42.7.4.jar"
fi

# --- Hadoop AWS Connectors ---
if [ ! -f "$DOWNLOAD_DIR/hadoop-aws-3.3.4.jar" ]; then
    echo "Downloading Hadoop AWS 3.3.4..."
    curl -L https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/3.3.4/hadoop-aws-3.3.4.jar -o "$DOWNLOAD_DIR/hadoop-aws-3.3.4.jar"
fi

if [ ! -f "$DOWNLOAD_DIR/aws-java-sdk-bundle-1.12.379.jar" ]; then
    echo "Downloading AWS Java SDK 1.12.379..."
    curl -L https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk-bundle/1.12.379/aws-java-sdk-bundle-1.12.379.jar -o "$DOWNLOAD_DIR/aws-java-sdk-bundle-1.12.379.jar"
fi

echo "All dependencies downloaded successfully."
