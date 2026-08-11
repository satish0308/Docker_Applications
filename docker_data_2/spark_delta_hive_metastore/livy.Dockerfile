# Stage 1: Build
FROM debian:bullseye-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    tar \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Copy tarballs and zips
COPY downloads/apache-livy-0.8.0-incubating_2.12-bin.zip /tmp/livy.zip
COPY downloads/spark-3.5.2-bin-hadoop3-scala2.13.tgz /tmp/spark.tgz

# Extract Livy
RUN mkdir -p /opt/livy && \
    unzip /tmp/livy.zip -d /opt && \
    mv /opt/apache-livy-0.8.0-incubating_2.12-bin/* /opt/livy/ && \
    rm -rf /opt/apache-livy-0.8.0-incubating_2.12-bin /tmp/livy.zip

# Extract Spark
RUN mkdir -p /opt/spark && \
    tar -xf /tmp/spark.tgz -C /opt/spark --strip-components=1 && \
    rm /tmp/spark.tgz

# Stage 2: Runtime
FROM python:3.11-slim

# Install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    default-jre-headless \
    && rm -rf /var/lib/apt/lists/* && \
    mkdir -p /var/log/livy && \
    chmod 777 /var/log/livy

ENV LIVY_HOME=/opt/livy
ENV SPARK_HOME=/opt/spark
ENV PATH=$LIVY_HOME/bin:$SPARK_HOME/bin:$PATH

# Copy from builder
COPY --from=builder /opt/livy /opt/livy
COPY --from=builder /opt/spark /opt/spark

# Copy configuration files
COPY livy/conf/livy.conf /opt/livy/conf/
COPY livy/conf/livy-env.sh /opt/livy/conf/
COPY livy/conf/log4j.properties /opt/livy/conf/

EXPOSE 8998

ENTRYPOINT ["/opt/livy/bin/livy-server"]
