# Stage 1: Build
FROM python:3.11-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    tar \
    && rm -rf /var/lib/apt/lists/*

# Copy tarballs and jars
COPY downloads/spark-3.5.2-bin-hadoop3-scala2.13.tgz /tmp/spark.tgz
COPY downloads/delta-spark_2.13-3.2.0.jar /opt/jars/delta-spark.jar
COPY downloads/delta-storage-3.2.0.jar /opt/jars/delta-storage.jar
COPY downloads/postgresql-42.7.4.jar /opt/jars/postgresql.jar
COPY downloads/hadoop-aws-3.3.4.jar /opt/jars/hadoop-aws-3.3.4.jar
COPY downloads/aws-java-sdk-bundle-1.12.379.jar /opt/jars/aws-java-sdk-bundle-1.12.379.jar

# Setup Spark
RUN mkdir -p /opt/spark && \
    tar -xf /tmp/spark.tgz -C /opt/spark --strip-components=1 && \
    rm /tmp/spark.tgz

# Stage 2: Runtime
FROM python:3.11-slim

# Setup Env
ENV JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64
ENV SPARK_HOME=/opt/spark
ENV PATH="$JAVA_HOME/bin:$SPARK_HOME/bin:$PATH"

# Install Runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    openjdk-21-jre-headless \
    procps \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir pyspark pandas numpy jupyter findspark PyArrow boto3

# Copy from builder
COPY --from=builder /opt/spark /opt/spark
COPY --from=builder /opt/jars /home/spark/jars

# Setup user
ARG USERNAME=sparkuser
ARG USER_UID=1000
ARG USER_GID=1000
RUN groupadd --gid $USER_GID $USERNAME && \
    useradd --uid $USER_UID --gid $USER_GID -m -s /bin/bash $USERNAME && \
    echo "$USERNAME ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers

# Directories
RUN mkdir -p /home/$USERNAME/app ${SPARK_HOME}/logs ${SPARK_HOME}/event_logs && \
    chown -R $USER_UID:$USER_GID ${SPARK_HOME} /home/$USERNAME

# Configs
RUN echo "spark.eventLog.enabled true" >> ${SPARK_HOME}/conf/spark-defaults.conf && \
    echo "spark.eventLog.dir file://${SPARK_HOME}/event_logs" >> ${SPARK_HOME}/conf/spark-defaults.conf && \
    echo "spark.history.fs.logDirectory file://${SPARK_HOME}/event_logs" >> ${SPARK_HOME}/conf/spark-defaults.conf

COPY config/hive-site.xml ${SPARK_HOME}/conf/hive-site.xml
COPY config/core-site.xml ${SPARK_HOME}/conf/core-site.xml
COPY config/hdfs-site.xml ${SPARK_HOME}/conf/hdfs-site.xml

# Copy scripts BEFORE switching user
COPY scripts/start-spark.sh /home/$USERNAME/start-spark2.sh
RUN chmod +x /home/$USERNAME/start-spark2.sh && \
    chown $USERNAME:$USERNAME /home/$USERNAME/start-spark2.sh

USER $USERNAME
WORKDIR /home/$USERNAME/app

ENV SPARK_CLASSPATH="/home/spark/jars/*"
ENV SPARK_MODE="master"

EXPOSE 4040 4041 18080 8888 5555 8080 7077

ENTRYPOINT ["/home/sparkuser/start-spark2.sh"]
