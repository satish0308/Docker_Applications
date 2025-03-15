FROM debian:bullseye-slim

# Install required packages
RUN apt-get update && apt-get install -y \
    openjdk-11-jdk \
    wget \
    vim \
    postgresql-client-13 \
    unzip \
    sudo \
    ssh

## Download and install Hive
#RUN wget https://archive.apache.org/dist/hive/hive-3.1.3/apache-hive-3.1.3-bin.tar.gz
#RUN tar -xzvf apache-hive-3.1.3-bin.tar.gz
#RUN mv apache-hive-3.1.3 /usr/local/hive

# Copy Hadoop and Hive tarballs
COPY downloads/hadoop-3.4.0.tar.gz /tmp/hadoop-3.4.0.tar.gz
RUN mkdir -p /home/hadoop
RUN tar -xf /tmp/hadoop-3.4.0.tar.gz -C /home/hadoop --strip-components=1
RUN rm /tmp/hadoop-3.4.0.tar.gz


COPY downloads/apache-hive-4.0.0-bin.tar.gz /tmp/apache-hive-4.0.0-bin.tar.gz
RUN mkdir -p /home/hive
RUN tar -xf /tmp/apache-hive-4.0.0-bin.tar.gz -C /home/hive/ --strip-components=1
RUN rm /tmp/apache-hive-4.0.0-bin.tar.gz

# Set up environment variables
ENV HIVE_HOME /home/hive
ENV HADOOP_HOME /home/hadoop
ENV PATH $HIVE_HOME/bin:$PATH
ENV HIVE_CONF_DIR /home/hive/conf

# PostgreSQL JDBC Driver
RUN wget https://jdbc.postgresql.org/download/postgresql-42.2.23.jar -P $HIVE_HOME/lib/

# Copy configuration files
COPY config/hive-site.xml /home/hive/conf/hive-site.xml
COPY config/hadoop-env.sh $HADOOP_HOME/etc/hadoop/hadoop-env.sh

# Expose ports for Hive services
EXPOSE 10000 10002

# Create hdfs user and set permissions
RUN useradd -m hdfs
RUN chown -R hdfs:hdfs /home/hadoop
RUN chown -R hdfs:hdfs /home/hive
ENV HADOOP_USER_NAME hdfs
ENV HDFS_NAMENODE_USER=hdfs
ENV HDFS_DATANODE_USER=hdfs
ENV HDFS_SECONDARYNAMENODE_USER=hdfs

# Entrypoint script to start Hive services
COPY scripts/hive_entrypoint.sh /hive_entrypoint.sh
RUN chmod +x /hive_entrypoint.sh

# Command to run Hive
ENTRYPOINT ["/hive_entrypoint.sh"]