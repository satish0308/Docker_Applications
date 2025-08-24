# Use the official Python image as a base
FROM python:3.11-slim

# Set environment variables for Spark, Java, and Hadoop
ENV JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64
ENV PATH="$JAVA_HOME/bin:$PATH"
ENV SPARK_VERSION=3.5.2
ENV HADOOP_VERSION=3.4.1
ENV SPARK_HOME=/home/spark
ENV PATH=$SPARK_HOME/bin:$PATH
ENV HADOOP_HOME=/opt/hadoop
ENV PATH=$PATH:$HADOOP_HOME/bin
ENV HADOOP_CONF_DIR=$HADOOP_HOME/etc/hadoop
ENV JAVA_VERSION=21
ENV SPARK_MODE="master"


# Additional environment variables for Delta Lake and Unity Catalog
ENV DELTA_VERSION=3.2.0
ENV UNITY_CATALOG_VERSION=0.2.0-SNAPSHOT

# Install necessary packages and dependencies
RUN apt-get update && apt-get install -y \
    openjdk-21-jre-headless \
    curl \
    wget \
    vim \
    sudo \
    whois \
    ca-certificates-java

RUN pip install --no-cache-dir pyspark pandas numpy

# Install Hadoop
RUN curl -O https://dlcdn.apache.org/hadoop/common/hadoop-${HADOOP_VERSION}/hadoop-${HADOOP_VERSION}.tar.gz \
    && tar -xzf hadoop-${HADOOP_VERSION}.tar.gz \
    && mv hadoop-${HADOOP_VERSION} /opt/hadoop \
    && rm hadoop-${HADOOP_VERSION}.tar.gz

# Copy and set up Spark
COPY downloads/spark-3.5.2-bin-hadoop3-scala2.13.tgz /tmp/apache-spark.tgz
RUN mkdir -p ${SPARK_HOME} \
    && tar -xf /tmp/apache-spark.tgz -C ${SPARK_HOME} --strip-components=1 \
    && rm /tmp/apache-spark.tgz

# Set up a non-root user
ARG USERNAME=sparkuser
ARG USER_UID=1000
ARG USER_GID=1000

RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m -s /bin/bash $USERNAME \
    && echo "$USERNAME ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers

# Set ownership for Spark directories
RUN chown -R $USER_UID:$USER_GID ${SPARK_HOME}

# Create directories for logs and event logs
RUN mkdir -p ${SPARK_HOME}/logs \
    && mkdir -p ${SPARK_HOME}/event_logs \
    && chown -R $USER_UID:$USER_GID ${SPARK_HOME}/event_logs \
    && chown -R $USER_UID:$USER_GID ${SPARK_HOME}/logs

# Set up Spark configuration for logging and history server
RUN echo "spark.eventLog.enabled true" >> $SPARK_HOME/conf/spark-defaults.conf \
    && echo "spark.eventLog.dir file://${SPARK_HOME}/event_logs" >> $SPARK_HOME/conf/spark-defaults.conf \
    && echo "spark.history.fs.logDirectory file://${SPARK_HOME}/event_logs" >> $SPARK_HOME/conf/spark-defaults.conf

# Install Python packages for Jupyter and PySpark
RUN pip install --no-cache-dir jupyter findspark pandas numpy PyArrow boto3

# Add JAR files for Delta Lake, PostgreSQL, and Unity Catalog
RUN mkdir -p /home/spark/jars
COPY downloads/delta-spark_2.13-3.2.0.jar /home/spark/jars/delta-spark_2.13-3.2.0.jar
COPY downloads/delta-storage-3.2.0.jar /home/spark/jars/delta-storage-3.2.0.jar
COPY downloads/postgresql-42.7.4.jar /home/spark/jars/postgresql-42.7.4.jar
# Uncomment if you use Unity Catalog
# COPY downloads/unitycatalog-spark-0.2.0-SNAPSHOT.jar /home/spark/jars/unitycatalog-spark-0.2.0-SNAPSHOT.jar



# Add Hadoop AWS + AWS SDK JARs for MinIO/S3 access
RUN curl -L -o /home/spark/jars/hadoop-aws-3.3.4.jar \
        https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/3.3.4/hadoop-aws-3.3.4.jar && \
    curl -L -o /home/spark/jars/aws-java-sdk-bundle-1.12.379.jar \
        https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk-bundle/1.12.379/aws-java-sdk-bundle-1.12.379.jar



# Copy Hadoop and Spark configuration files
COPY config/hive-site.xml $SPARK_HOME/conf/hive-site.xml
# Add core-site.xml and hdfs-site.xml for HDFS connectivity
COPY config/core-site.xml $HADOOP_CONF_DIR/core-site.xml
COPY config/hdfs-site.xml $HADOOP_CONF_DIR/hdfs-site.xml

COPY config/core-site.xml $SPARK_HOME/conf/core-site.xml
COPY config/hdfs-site.xml $SPARK_HOME/conf/hdfs-site.xml


# List JAR files for verification
RUN ls -la /home/spark/jars

# Add the entrypoint script
COPY scripts/start-spark.sh /home/spark/start-spark2.sh
RUN chmod +x /home/spark/start-spark2.sh

ENV SPARK_CLASSPATH="/home/spark/jars/*"

# Switch to non-root user
USER $USERNAME

# Set workdir and create application directories
RUN mkdir -p /home/$USERNAME/app

WORKDIR /home/$USERNAME/app

# Expose necessary ports for Jupyter, Spark UI, and JDWP debug port
EXPOSE 4040 4041 18080 8888 5555 8080 7077

# Entrypoint
ENTRYPOINT ["/home/spark/start-spark2.sh"]

