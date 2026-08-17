# Stage 1: Build/Preparation
FROM debian:bullseye-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    tar \
    && rm -rf /var/lib/apt/lists/*

# Download and extract Hadoop
COPY downloads/hadoop-3.4.0.tar.gz /tmp/hadoop-3.4.0.tar.gz
RUN mkdir -p /opt/hadoop && \
    tar -xf /tmp/hadoop-3.4.0.tar.gz -C /opt/hadoop --strip-components=1 && \
    rm /tmp/hadoop-3.4.0.tar.gz && \
    cp /opt/hadoop/share/hadoop/tools/lib/hadoop-aws-3.4.0.jar /opt/hadoop/share/hadoop/common/lib/ && \
    cp /opt/hadoop/share/hadoop/tools/lib/bundle-2.23.19.jar /opt/hadoop/share/hadoop/common/lib/

# Stage 2: Runtime
FROM debian:bullseye-slim

# Install minimal runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    openjdk-11-jdk \
    ssh \
    vim \
    sudo \
    openssh-server \
    && rm -rf /var/lib/apt/lists/*

# Copy Hadoop from builder
COPY --from=builder /opt/hadoop /home/hadoop

# Ensure SSH service starts
RUN mkdir -p /var/run/sshd /home/hadoop/logs

# Setup users and permissions
RUN useradd -m -s /bin/bash hadoop && \
    useradd -m -s /bin/bash hdfs && \
    useradd -m -s /bin/bash yarn && \
    usermod -aG hdfs hadoop && \
    usermod -aG hdfs yarn && \
    usermod -aG hadoop hdfs && \
    usermod -aG hadoop yarn && \
    usermod -aG yarn hadoop && \
    usermod -aG yarn hdfs

# SSH setup
RUN mkdir -p /home/hadoop/.ssh && \
    ssh-keygen -t rsa -b 4096 -f /home/hadoop/.ssh/id_rsa -N "" && \
    cat /home/hadoop/.ssh/id_rsa.pub >> /home/hadoop/.ssh/authorized_keys && \
    touch /home/hadoop/.ssh/known_hosts && \
    chmod 700 /home/hadoop/.ssh && \
    chmod 600 /home/hadoop/.ssh/id_rsa /home/hadoop/.ssh/authorized_keys /home/hadoop/.ssh/known_hosts && \
    chown -R hadoop:hadoop /home/hadoop/.ssh && \
    echo "PasswordAuthentication yes" >> /etc/ssh/sshd_config && \
    echo "StrictModes no" >> /etc/ssh/sshd_config && \
    echo "AllowUsers hadoop root" >> /etc/ssh/sshd_config && \
    sed -i '/PermitRootLogin yes/d' /etc/ssh/sshd_config && \
    echo 'root:hadoop' | chpasswd

# Environment variables
ENV HADOOP_HOME=/home/hadoop
ENV HADOOP_CONF_DIR=$HADOOP_HOME/etc/hadoop
ENV PATH=$HADOOP_HOME/bin:$HADOOP_HOME/sbin:$PATH
ENV HADOOP_USER_NAME=hdfs
ENV HDFS_NAMENODE_USER=hdfs
ENV HDFS_DATANODE_USER=hdfs
ENV HDFS_SECONDARYNAMENODE_USER=hdfs
ENV YARN_RESOURCEMANAGER_USER=yarn
ENV YARN_NODEMANAGER_USER=yarn

# Create Hadoop directories
RUN mkdir -p /home/hadoop/tmp /home/hadoop/logs /home/hadoop/data /home/hadoop/dfs /var/lib/hadoop && \
    chown -R hdfs:hadoop /home/hadoop/tmp /home/hadoop/logs /home/hadoop/data /home/hadoop/dfs /var/lib/hadoop && \
    chmod -R 775 /home/hadoop/tmp /home/hadoop/logs /home/hadoop/data /home/hadoop/dfs /var/lib/hadoop

# Copy configs
COPY config/core-site.xml $HADOOP_HOME/etc/hadoop/
COPY config/hdfs-site.xml $HADOOP_HOME/etc/hadoop/
COPY config/hadoop-env.sh $HADOOP_HOME/etc/hadoop/
COPY config/yarn-site.xml $HADOOP_HOME/etc/hadoop/
COPY config/mapred-site.xml $HADOOP_HOME/etc/hadoop/
RUN chown -R hdfs:hadoop $HADOOP_HOME/etc/hadoop && chmod -R 775 $HADOOP_HOME/etc/hadoop

EXPOSE 22 9870 9864 9866 9000 8088 8042 8030 8031 8032 8033

COPY scripts/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
