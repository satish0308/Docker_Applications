FROM quay.io/jupyterhub/k8s-singleuser-sample:4.2.0

USER root

# -------- Install Java (OpenJDK 21) + tools --------
RUN apt-get update && apt-get install -y \
    openjdk-17-jdk \
    curl \
    netcat-openbsd \
    iproute2 && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV PATH=$JAVA_HOME/bin:$PATH

# -------- Install Spark (3.5.2 pre-built for Hadoop 3) --------
ENV SPARK_VERSION=3.5.2
ENV HADOOP_VERSION=3
ENV SPARK_HOME=/opt/spark

COPY downloads/spark-3.5.2-bin-hadoop3-scala2.13.tgz /tmp/spark.tgz
RUN mkdir -p ${SPARK_HOME} \
    && tar -xf /tmp/spark.tgz -C ${SPARK_HOME} --strip-components=1 \
    && rm /tmp/spark.tgz

ENV PATH=${SPARK_HOME}/bin:${SPARK_HOME}/sbin:$PATH
ENV PYSPARK_PYTHON=python3
ENV PYSPARK_DRIVER_PYTHON=python3

RUN echo "export SPARK_HOME=/opt/spark" >> /etc/profile.d/spark.sh && \
    echo "export PATH=\$SPARK_HOME/bin:\$SPARK_HOME/sbin:\$PATH" >> /etc/profile.d/spark.sh


ENV PYTHONPATH=${SPARK_HOME}/python:${SPARK_HOME}/python/lib/py4j-0.10.9.7-src.zip:\$PYTHONPATH

# -------- Clean PySpark (pip) and install core deps only --------
RUN pip uninstall -y pyspark && \
    pip install --no-cache-dir pandas numpy jupyterlab matplotlib


RUN pip install --no-cache-dir pyspark pandas numpy

# -------- Add Hadoop AWS & AWS SDK for S3A --------
ENV HADOOP_AWS_VERSION=3.3.4
ENV AWS_SDK_VERSION=1.12.379

RUN curl -L https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/${HADOOP_AWS_VERSION}/hadoop-aws-${HADOOP_AWS_VERSION}.jar \
    -o ${SPARK_HOME}/jars/hadoop-aws-${HADOOP_AWS_VERSION}.jar && \
    curl -L https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk-bundle/${AWS_SDK_VERSION}/aws-java-sdk-bundle-${AWS_SDK_VERSION}.jar \
    -o ${SPARK_HOME}/jars/aws-java-sdk-bundle-${AWS_SDK_VERSION}.jar


USER $NB_UID

EXPOSE 7077 4040


