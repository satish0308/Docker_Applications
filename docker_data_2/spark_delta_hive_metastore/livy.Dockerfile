# Stage 1: Build
FROM debian:bullseye-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    tar \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Copy tarballs and zips
COPY downloads/apache-livy-0.8.0-incubating_2.12-bin.zip /tmp/livy.zip
COPY downloads/spark-3.5.2-bin-hadoop3.tgz /tmp/spark.tgz

# Extract Livy
RUN mkdir -p /opt/livy && \
    unzip /tmp/livy.zip -d /opt && \
    mv /opt/apache-livy-0.8.0-incubating_2.12-bin/* /opt/livy/ && \
    rm -rf /opt/apache-livy-0.8.0-incubating_2.12-bin /tmp/livy.zip

# Extract Spark
RUN mkdir -p /opt/spark && \
    tar -xf /tmp/spark.tgz -C /opt/spark --strip-components=1 && \
    rm /tmp/spark.tgz

# Copy jars to Spark system jars directory
COPY downloads/delta-spark_2.12-3.2.0.jar /opt/spark/jars/delta-spark.jar
COPY downloads/delta-storage-3.2.0.jar /opt/spark/jars/delta-storage.jar
COPY downloads/postgresql-42.7.4.jar /opt/spark/jars/postgresql.jar
COPY downloads/hadoop-aws-3.3.4.jar /opt/spark/jars/hadoop-aws-3.3.4.jar
COPY downloads/aws-java-sdk-bundle-1.12.379.jar /opt/spark/jars/aws-java-sdk-bundle-1.12.379.jar

# Stage 2: Runtime
FROM python:3.11-slim

# Install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    default-jre-headless \
    && rm -rf /var/lib/apt/lists/* && \
    mkdir -p /var/log/livy /opt/spark/event_logs /user/hive/warehouse && \
    chmod -R 777 /var/log/livy /opt/spark/event_logs /user

ENV LIVY_HOME=/opt/livy
ENV SPARK_HOME=/opt/spark
ENV PATH=$LIVY_HOME/bin:$SPARK_HOME/bin:$PATH

# JDK 17+/21 locks down reflective access that Kryo needs (e.g. to serialize
# SerializedLambda) when the RSC driver negotiates its session; without these
# opens the driver JVM dies instantly with InaccessibleObjectException.
ENV JDK_JAVA_OPTIONS="--add-opens=java.base/java.lang=ALL-UNNAMED \
--add-opens=java.base/java.lang.invoke=ALL-UNNAMED \
--add-opens=java.base/java.lang.reflect=ALL-UNNAMED \
--add-opens=java.base/java.io=ALL-UNNAMED \
--add-opens=java.base/java.net=ALL-UNNAMED \
--add-opens=java.base/java.nio=ALL-UNNAMED \
--add-opens=java.base/java.util=ALL-UNNAMED \
--add-opens=java.base/java.util.concurrent=ALL-UNNAMED \
--add-opens=java.base/java.util.concurrent.atomic=ALL-UNNAMED \
--add-opens=java.base/sun.nio.ch=ALL-UNNAMED \
--add-opens=java.base/sun.nio.cs=ALL-UNNAMED \
--add-opens=java.base/sun.security.action=ALL-UNNAMED \
--add-opens=java.base/sun.util.calendar=ALL-UNNAMED"

# Copy from builder
COPY --from=builder /opt/livy /opt/livy
COPY --from=builder /opt/spark /opt/spark

# Deduplicate JARs between rsc-jars and repl_2.12-jars to prevent Spark 3.x NettyStreamManager collisions
RUN rm -f /opt/livy/repl_2.12-jars/minlog-*.jar \
          /opt/livy/repl_2.12-jars/objenesis-*.jar \
          /opt/livy/repl_2.12-jars/kryo-shaded-*.jar

# Copy configuration files
COPY livy/conf/livy.conf /opt/livy/conf/
COPY livy/conf/livy-env.sh /opt/livy/conf/
COPY livy/conf/log4j.properties /opt/livy/conf/
COPY config/core-site.xml /opt/spark/conf/core-site.xml
COPY config/spark-defaults.conf /opt/spark/conf/spark-defaults.conf
COPY config/hive-site.xml /opt/spark/conf/hive-site.xml

EXPOSE 8998

ENTRYPOINT ["/opt/livy/bin/livy-server"]
