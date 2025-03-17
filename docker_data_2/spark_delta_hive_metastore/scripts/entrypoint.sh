#!/bin/bash
set -e  # Exit immediately if a command exits with a non-zero status

echo "Starting SSH service..."
service ssh start

echo "Exporting port 22..."
export SSH_PORT=22

# Ensure hadoop is part of hdfs group
echo "Adding hadoop user to hdfs group..."
usermod -aG hdfs hadoop

# Fix ownership: hdfs as owner, hadoop as group
echo "Setting ownership for Hadoop directories..."
chown -R hdfs:hadoop /home/hadoop
chmod -R 775 /home/hadoop

echo "Setting permissions for Hadoop log directory..."
mkdir -p /home/hadoop/logs
chown -R hdfs:hadoop /home/hadoop/logs
chmod -R 775 /home/hadoop/logs

# Ensure correct permissions for SSH
echo "Fixing SSH directory permissions..."
mkdir -p /home/hadoop/.ssh
chown -R hadoop:hadoop /home/hadoop/.ssh
chmod 700 /home/hadoop/.ssh

# Fix SSH key permissions
echo "Setting up passwordless SSH for hadoop user..."
if [ ! -f /home/hadoop/.ssh/id_rsa ]; then
  echo "Generating new SSH key for hadoop user..."
  su - hadoop -c "
    ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa -N '' &&
    cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys
  "
fi

# Ensure correct permissions for SSH keys
chmod 600 /home/hadoop/.ssh/id_rsa /home/hadoop/.ssh/authorized_keys
touch /home/hadoop/.ssh/known_hosts
chmod 600 /home/hadoop/.ssh/known_hosts

# Test passwordless SSH (should not ask for a password)
echo "Testing SSH connection for hadoop user..."
su - hadoop -c "ssh -o StrictHostKeyChecking=no localhost echo 'SSH Test Success!'" || echo "SSH test failed!"

# Ensure Hadoop directories exist
echo "Ensuring Hadoop directories are set up..."
mkdir -p /home/hadoop/tmp /home/hadoop/logs /home/hadoop/data
chown -R hdfs:hadoop /home/hadoop/tmp /home/hadoop/data
chmod -R 775 /home/hadoop/tmp /home/hadoop/data

echo "Setup complete!"



# Format NameNode (only for NameNode container)
if [[ $HOSTNAME == "namenode" ]]; then
  if [ ! -d "/home/hadoop/dfs/name/current" ]; then
    echo "Formatting NameNode..."
    $HADOOP_HOME/bin/hdfs namenode -format -force -nonInteractive
  else
    echo "NameNode already formatted."
  fi

  echo "Starting HDFS services..."
  $HADOOP_HOME/sbin/start-dfs.sh

  echo "Starting NameNode..."
  $HADOOP_HOME/bin/hdfs namenode
else
  echo "Starting DataNode..."
  $HADOOP_HOME/sbin/hadoop-daemon.sh start datanode
  tail -f /dev/null
fi
