# Stage 1: Build
FROM debian:bullseye-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    tar \
    && rm -rf /var/lib/apt/lists/*

# Copy tarballs and JARs
COPY downloads/hadoop-3.4.0.tar.gz /tmp/hadoop-3.4.0.tar.gz
COPY downloads/apache-hive-4.0.0-bin.tar.gz /tmp/apache-hive-4.0.0-bin.tar.gz
COPY downloads/postgresql-42.7.4.jar /tmp/postgresql-42.7.4.jar

# Extract Hadoop
RUN mkdir -p /opt/hadoop && \
    tar -xf /tmp/hadoop-3.4.0.tar.gz -C /opt/hadoop --strip-components=1 && \
    rm /tmp/hadoop-3.4.0.tar.gz

# Extract Hive
RUN mkdir -p /opt/hive && \
    tar -xf /tmp/apache-hive-4.0.0-bin.tar.gz -C /opt/hive --strip-components=1 && \
    rm /tmp/apache-hive-4.0.0-bin.tar.gz

# Copy Postgres Driver and native Hadoop AWS S3A JARs
RUN cp /tmp/postgresql-42.7.4.jar /opt/hive/lib/postgresql-42.7.4.jar && \
    cp /opt/hadoop/share/hadoop/tools/lib/hadoop-aws-3.4.0.jar /opt/hive/lib/ && \
    cp /opt/hadoop/share/hadoop/tools/lib/bundle-2.23.19.jar /opt/hive/lib/ && \
    cp /opt/hadoop/share/hadoop/tools/lib/hadoop-aws-3.4.0.jar /opt/hadoop/share/hadoop/common/lib/ && \
    cp /opt/hadoop/share/hadoop/tools/lib/bundle-2.23.19.jar /opt/hadoop/share/hadoop/common/lib/

# Stage 2: Runtime
FROM debian:bullseye-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    openjdk-11-jre-headless \
    postgresql-client-13 \
    netcat \
    sudo \
    openssh-client \
    openssh-server \
    && rm -rf /var/lib/apt/lists/*

# Create users
RUN useradd -m -s /bin/bash hdfs && \
    useradd -m -s /bin/bash hue && \
    useradd -m -s /bin/bash hive

# Copy from builder
COPY --from=builder /opt/hadoop /home/hadoop
COPY --from=builder /opt/hive /home/hive

# Setup directories
RUN mkdir -p /hue/desktop/conf /tmp/gunicorn /home/hive/conf && \
    chown -R hue:hue /hue /tmp/gunicorn && \
    chown -R hive:hive /home/hive && \
    chmod -R 777 /hue /tmp/gunicorn

# Env vars
ENV HIVE_HOME=/home/hive
ENV HADOOP_HOME=/home/hadoop
ENV PATH=$HIVE_HOME/bin:$PATH
ENV HIVE_CONF_DIR=/home/hive/conf
ENV TMPDIR=/tmp/gunicorn
ENV HADOOP_USER_NAME=hdfs

# Configs
COPY config/hive-site.xml /home/hive/conf/hive-site.xml
COPY config/hadoop-env.sh $HADOOP_HOME/etc/hadoop/hadoop-env.sh

# Permissions
RUN chown -R hdfs:hdfs /home/hadoop /home/hive

EXPOSE 10000 10002

COPY scripts/hive_entrypoint.sh /hive_entrypoint.sh
RUN chmod +x /hive_entrypoint.sh

ENTRYPOINT [ "sh", "-c", "exec /hive_entrypoint.sh" ]
