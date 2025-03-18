FROM debian:bullseye-slim

# Install required packages
RUN apt-get update && apt-get install -y \
    openjdk-11-jdk \
    wget \
    vim \
    postgresql-client-13 \
    unzip \
    sudo \
    ssh \
    netcat

# Create required users
RUN useradd -m -s /bin/bash hdfs
RUN useradd -m -s /bin/bash hue   # Ensure 'hue' user exists before setting permissions
RUN useradd -m -s /bin/bash hive  # 🔹 Added Hive user

# Create required directories
RUN mkdir -p /hue/desktop/conf /tmp/gunicorn /home/hive/conf

# Set correct permissions
RUN chown -R hue:hue /hue /tmp/gunicorn
RUN chmod -R 777 /hue /tmp/gunicorn
RUN chown -R hive:hive /home/hive  # 🔹 Give Hive user ownership of its directory

# Set TMPDIR explicitly
ENV TMPDIR=/tmp/gunicorn


# Copy Hadoop and Hive tarballs
COPY downloads/hadoop-3.4.0.tar.gz /tmp/hadoop-3.4.0.tar.gz
RUN mkdir -p /home/hadoop && tar -xf /tmp/hadoop-3.4.0.tar.gz -C /home/hadoop --strip-components=1
RUN rm /tmp/hadoop-3.4.0.tar.gz

COPY downloads/apache-hive-4.0.0-bin.tar.gz /tmp/apache-hive-4.0.0-bin.tar.gz
RUN mkdir -p /home/hive && tar -xf /tmp/apache-hive-4.0.0-bin.tar.gz -C /home/hive/ --strip-components=1
RUN rm /tmp/apache-hive-4.0.0-bin.tar.gz

# Set up environment variables
ENV HIVE_HOME=/home/hive
ENV HADOOP_HOME=/home/hadoop
ENV PATH=$HIVE_HOME/bin:$PATH
ENV HIVE_CONF_DIR=/home/hive/conf

# PostgreSQL JDBC Driver
RUN wget https://jdbc.postgresql.org/download/postgresql-42.2.23.jar -P $HIVE_HOME/lib/

# Copy configuration files
COPY config/hive-site.xml /home/hive/conf/hive-site.xml
COPY config/hadoop-env.sh $HADOOP_HOME/etc/hadoop/hadoop-env.sh

# Expose ports for Hive services
EXPOSE 10000 10002

# Set correct user permissions
RUN chown -R hdfs:hdfs /home/hadoop
RUN chown -R hdfs:hdfs /home/hive
ENV HADOOP_USER_NAME=hdfs
ENV HDFS_NAMENODE_USER=hdfs
ENV HDFS_DATANODE_USER=hdfs
ENV HDFS_SECONDARYNAMENODE_USER=hdfs
ENV POSTGRES_PASSWORD=hivepassword

# Set TMPDIR properly
ENV TMPDIR=/tmp/gunicorn

# Copy and set up entrypoint script
COPY scripts/hive_entrypoint.sh /hive_entrypoint.sh
RUN chmod +x /hive_entrypoint.sh

# Command to run Hive
ENTRYPOINT [ "sh", "-c", "exec /hive_entrypoint.sh" ]
