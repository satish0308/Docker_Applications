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

COPY downloads/spark-3.5.2-bin-hadoop3.tgz /tmp/spark.tgz
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

# -------- Add Hadoop AWS, AWS SDK, Delta Lake & Postgres JARs --------
COPY downloads/hadoop-aws-3.3.4.jar ${SPARK_HOME}/jars/hadoop-aws-3.3.4.jar
COPY downloads/aws-java-sdk-bundle-1.12.379.jar ${SPARK_HOME}/jars/aws-java-sdk-bundle-1.12.379.jar
COPY downloads/delta-spark_2.12-3.2.0.jar ${SPARK_HOME}/jars/delta-spark.jar
COPY downloads/delta-storage-3.2.0.jar ${SPARK_HOME}/jars/delta-storage.jar
COPY downloads/postgresql-42.7.4.jar ${SPARK_HOME}/jars/postgresql.jar

# -------- Copy Cluster Configurations --------
COPY config/spark-defaults.conf ${SPARK_HOME}/conf/spark-defaults.conf
COPY config/core-site.xml ${SPARK_HOME}/conf/core-site.xml
COPY config/hive-site.xml ${SPARK_HOME}/conf/hive-site.xml

USER root
RUN mkdir -p /user/hive/warehouse /opt/spark/event_logs /tmp/spark-events /home/jovyan/.ipython/profile_default/startup && \
    chmod -R 777 /user /opt/spark/event_logs /tmp/spark-events /home/jovyan/.ipython

RUN cat << "EOF" > /home/jovyan/.ipython/profile_default/startup/00-spark-init.py
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

try:
    spark = SparkSession.builder \
        .appName("JupyterLab_Interactive") \
        .config("spark.driver.memory", "2g") \
        .config("spark.executor.memory", "2g") \
        .enableHiveSupport() \
        .getOrCreate()
    sc = spark.sparkContext
    print("⚡ [Auto-Init] Apache Spark & Hive Metastore session ready as `spark`!")
except Exception as e:
    print(f"⚠️ PySpark init note: {e}")
EOF

USER $NB_UID

EXPOSE 7077 8888

CMD ["jupyter", "lab", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root", "--IdentityProvider.token=", "--ServerApp.password=", "--NotebookApp.token=", "--NotebookApp.password="]
