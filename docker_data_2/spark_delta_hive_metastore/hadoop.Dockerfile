FROM debian:bullseye-slim

# Install required packages
RUN apt-get update && apt-get install -y \
    ssh \
    openjdk-11-jdk \
    wget \
    unzip \
    vim \
    sudo \
    openssh-server

# Ensure SSH service starts
RUN mkdir -p /var/run/sshd
RUN mkdir -p /home/hadoop/logs

RUN useradd -m -s /bin/bash hadoop
RUN useradd -m -s /bin/bash hdfs
RUN useradd -m -s /bin/bash yarn


RUN usermod -aG hdfs hadoop && \
    usermod -aG hdfs yarn  # Allow yarn to interact with HDFS


# Set up passwordless SSH for Hadoop user
RUN mkdir -p /home/hadoop/.ssh && \
    ssh-keygen -t rsa -b 4096 -f /home/hadoop/.ssh/id_rsa -N "" && \
    cat /home/hadoop/.ssh/id_rsa.pub >> /home/hadoop/.ssh/authorized_keys && \
    touch /home/hadoop/.ssh/known_hosts && \
    chmod 700 /home/hadoop/.ssh && \
    chmod 600 /home/hadoop/.ssh/id_rsa /home/hadoop/.ssh/authorized_keys /home/hadoop/.ssh/known_hosts && \
    chown -R hadoop:hadoop /home/hadoop/.ssh

# Fix SSH Configuration (remove root login)
RUN echo "PasswordAuthentication yes" >> /etc/ssh/sshd_config && \
    echo "StrictModes no" >> /etc/ssh/sshd_config && \
    echo "AllowUsers hadoop root" >> /etc/ssh/sshd_config && \
    sed -i '/PermitRootLogin yes/d' /etc/ssh/sshd_config && \
    service ssh restart


# Set root password for SSH access
RUN echo 'root:hadoop' | chpasswd

# Ensure proper ownership and permissions
RUN chown -R hdfs:hadoop /home/hadoop && chmod -R 775 /home/hadoop

# Copy Hadoop tarball and extract
COPY downloads/hadoop-3.4.0.tar.gz /tmp/hadoop-3.4.0.tar.gz
RUN mkdir -p /home/hadoop && \
    tar -xf /tmp/hadoop-3.4.0.tar.gz -C /home/hadoop --strip-components=1 && \
    rm /tmp/hadoop-3.4.0.tar.gz

# Set up environment variables
ENV HADOOP_HOME=/home/hadoop
ENV HADOOP_CONF_DIR=$HADOOP_HOME/etc/hadoop
ENV PATH=$HADOOP_HOME/bin:$HADOOP_HOME/sbin:$PATH
ENV HADOOP_USER_NAME=hdfs
ENV HDFS_NAMENODE_USER=hdfs
ENV HDFS_DATANODE_USER=hdfs
ENV HDFS_SECONDARYNAMENODE_USER=hdfs
ENV YARN_RESOURCEMANAGER_USER=yarn
ENV YARN_NODEMANAGER_USER=yarn


# Create necessary Hadoop directories
RUN mkdir -p /home/hadoop/tmp /home/hadoop/logs /home/hadoop/data && \
    chown -R hdfs:hadoop /home/hadoop/tmp /home/hadoop/logs /home/hadoop/data && \
    chmod -R 775 /home/hadoop/tmp /home/hadoop/logs /home/hadoop/data


# Copy Hadoop configuration files
COPY config/core-site.xml $HADOOP_HOME/etc/hadoop/
COPY config/hdfs-site.xml $HADOOP_HOME/etc/hadoop/
COPY config/hadoop-env.sh $HADOOP_HOME/etc/hadoop/
COPY config/yarn-site.xml $HADOOP_HOME/etc/hadoop/
COPY config/mapred-site.xml $HADOOP_HOME/etc/hadoop/

# Ensure permissions are correct after copying
RUN chown -R hdfs:hadoop $HADOOP_HOME/etc/hadoop && chmod -R 775 $HADOOP_HOME/etc/hadoop

# Ensure Hadoop directories exist before setting permissions
RUN mkdir -p /home/hadoop/tmp /home/hadoop/logs /home/hadoop/data /home/hadoop/dfs /var/lib/hadoop && \
    chown -R hdfs:hadoop /home/hadoop/tmp /home/hadoop/logs /home/hadoop/data /home/hadoop/dfs /var/lib/hadoop && \
    chmod -R 775 /home/hadoop/tmp /home/hadoop/logs /home/hadoop/data /home/hadoop/dfs /var/lib/hadoop


# Ensure read-write-execute permissions for all three users
RUN chmod -R 775 /home/hadoop/tmp /home/hadoop/logs /home/hadoop/data /home/hadoop/dfs /var/lib/hadoop

RUN echo "Adding Hadoop users to hdfs group..."
RUN usermod -aG hadoop hdfs
RUN usermod -aG hadoop yarn
RUN usermod -aG hdfs hadoop
RUN usermod -aG hdfs yarn
RUN usermod -aG yarn hadoop
RUN usermod -aG yarn hdfs


# Expose SSH and Hadoop ports

EXPOSE 22 9870 9864 9866 9000 8088 8042 8030 8031 8032 8033

# Copy and set permissions for entrypoint script
COPY scripts/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
