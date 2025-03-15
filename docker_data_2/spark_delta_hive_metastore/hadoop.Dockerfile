FROM debian:bullseye-slim

# Install required packages
RUN apt-get update && apt-get install -y \
    ssh \
    openjdk-11-jdk \
    wget \
    unzip \
    vim \
    sudo

RUN mkdir /var/run/sshd
RUN service ssh start

# Download and install Hadoop
#RUN wget https://archive.apache.org/dist/hadoop/common/hadoop-3.3.4/hadoop-3.3.4.tar.gz
#RUN tar -xzvf hadoop-3.3.4.tar.gz
#RUN mv hadoop-3.3.4 /usr/local/hadoop

# Copy Hadoop tarball
COPY downloads/hadoop-3.4.0.tar.gz /tmp/hadoop-3.4.0.tar.gz
RUN mkdir -p /home/hadoop
RUN tar -xf /tmp/hadoop-3.4.0.tar.gz -C /home/hadoop --strip-components=1
RUN rm /tmp/hadoop-3.4.0.tar.gz

# Set up environment variables
ENV HADOOP_HOME /home/hadoop
ENV PATH $HADOOP_HOME/bin:$PATH
RUN mkdir -p /home/hadoop/tmp /home/hadoop/logs /home/hadoop/data

# Set up passwordless SSH for Hadoop communication
RUN ssh-keygen -q -t rsa -N "" -f ~/.ssh/id_rsa && \
    cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys && \
    chmod 0600 ~/.ssh/authorized_keys

# Create Hadoop configuration files
COPY config/core-site.xml $HADOOP_HOME/etc/hadoop/
COPY config/hdfs-site.xml $HADOOP_HOME/etc/hadoop/
COPY config/hadoop-env.sh $HADOOP_HOME/etc/hadoop/

# Create hdfs user and set permissions
RUN useradd -m hdfs
RUN chown -R hdfs:hdfs /home/hadoop
ENV HADOOP_USER_NAME hdfs
ENV HDFS_NAMENODE_USER=hdfs
ENV HDFS_DATANODE_USER=hdfs
ENV HDFS_SECONDARYNAMENODE_USER=hdfs

# Expose Hadoop ports
EXPOSE 9870 9864 9000

# Copy entrypoint script for NameNode and DataNode
COPY scripts/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]