FROM quay.io/jupyterhub/k8s-singleuser-sample:4.2.0

USER root

# Install Java
RUN apt-get update && apt-get install -y openjdk-17-jdk && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Set JAVA_HOME
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV PATH=$JAVA_HOME/bin:$PATH

USER $NB_UID

# Optional: Install PySpark if needed
RUN pip install pyspark

RUN pip install --no-cache-dir pyspark pandas numpy


EXPOSE 7077