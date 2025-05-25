#!/bin/bash
set -e  # Exit on error

LOG_FILE="/var/log/hadoop_entrypoint.log"
exec > >(tee -a $LOG_FILE) 2>&1  # Log all output



echo "========================================"
echo "🚀 Starting Hadoop & Hive Initialization V2"
echo "========================================"

# Ensure SSH service is running
echo "🚀 Starting SSH service..."
service ssh start

# Set environment variables
export HADOOP_HOME=/home/hadoop
export PATH=$HADOOP_HOME/bin:$HADOOP_HOME/sbin:$PATH
export HADOOP_CONF_DIR=$HADOOP_HOME/etc/hadoop
export JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64  # Ensure this path is correct

export YARN_RESOURCEMANAGER_HOSTNAME=resourceManager
export YARN_NODEMANAGER_HOSTNAME=nodeManager

echo "✅ Environment Variables Set:"
echo "HADOOP_HOME: $HADOOP_HOME"
echo "PATH: $PATH"
echo "HADOOP_CONF_DIR: $HADOOP_CONF_DIR"
echo "JAVA_HOME: $JAVA_HOME"
echo "YARN_RESOURCEMANAGER_HOSTNAME: $YARN_RESOURCEMANAGER_HOSTNAME"
echo "YARN_NODEMANAGER_HOSTNAME: $YARN_NODEMANAGER_HOSTNAME"

setup_ssh() {
  local user=$1
  local home_dir=$(eval echo ~$user)

  echo "📁 Ensuring SSH directory exists for $user..."
  mkdir -p $home_dir/.ssh
  chmod 700 $home_dir/.ssh
  chown -R $user:$user $home_dir/.ssh

  if [ ! -f "$home_dir/.ssh/id_rsa" ]; then
    echo "🔑 Generating SSH key for $user..."
    sudo -u $user ssh-keygen -t rsa -b 4096 -N "" -f $home_dir/.ssh/id_rsa
  fi

  # Ensure correct file permissions
  chmod 600 $home_dir/.ssh/id_rsa
  chmod 644 $home_dir/.ssh/id_rsa.pub
  chown $user:$user $home_dir/.ssh/id_rsa $home_dir/.ssh/id_rsa.pub

  # Ensure authorized_keys exists before appending
  touch $home_dir/.ssh/authorized_keys
  chmod 600 $home_dir/.ssh/authorized_keys
  chown $user:$user $home_dir/.ssh/authorized_keys

  # Append public key to authorized_keys if not already added
  grep -qF "$(cat $home_dir/.ssh/id_rsa.pub)" $home_dir/.ssh/authorized_keys || cat $home_dir/.ssh/id_rsa.pub >> $home_dir/.ssh/authorized_keys

  # Disable strict host key checking
  echo "StrictHostKeyChecking no" >> $home_dir/.ssh/config
  chmod 600 $home_dir/.ssh/config
  chown $user:$user $home_dir/.ssh/config

  # Ensure SSH service is running
  service ssh start

  # Add localhost to known_hosts to prevent SSH failures
  sudo -u $user ssh-keyscan -H localhost >> $home_dir/.ssh/known_hosts
  chmod 644 $home_dir/.ssh/known_hosts
  chown $user:$user $home_dir/.ssh/known_hosts

  # Validate SSH connection
  echo "🔄 Testing passwordless SSH for $user..."
  if ! sudo -u $user ssh -o StrictHostKeyChecking=no localhost exit; then
    echo "❌ ERROR: Passwordless SSH setup for $user failed. Check permissions!"
    exit 1
  else
    echo "✅ Passwordless SSH setup successful for $user!"
  fi
}



# Setup SSH for all users
setup_ssh hadoop
setup_ssh hdfs
setup_ssh yarn



# Validate passwordless SSH for each user
validate_ssh() {
    local user=$1
    echo "🔄 Testing passwordless SSH for $user..."
    if ! sudo -u $user ssh -o StrictHostKeyChecking=no localhost exit; then
        echo "❌ ERROR: SSH setup for $user failed. Check permissions!"
        exit 1
    else
        echo "✅ Passwordless SSH setup successful for $user!"
    fi
}

validate_ssh hadoop
validate_ssh hdfs
validate_ssh yarn

# Add users to appropriate groups
echo "👥 Adding Hadoop users to groups..."
usermod -aG hadoop hdfsusermod -aG hadoop hdfs\usermod -aG hadoop yarn
usermod -aG hdfs hadoopusermod -aG hdfs hadoop\usermod -aG hdfs yarn
usermod -aG yarn hadoop
usermod -aG yarn hdfs

# Set correct ownership and permissions for Hadoop directories
echo "🔧 Setting correct ownership and permissions for Hadoop directories..."
mkdir -p /home/hadoop/dfs/name /home/hadoop/dfs/data /home/hadoop/tmp /home/hadoop/logs /var/lib/hadoop
chown -R hdfs:hadoop /home/hadoop/dfs/name /home/hadoop/dfs/data /var/lib/hadoop
chmod -R 775 /home/hadoop/dfs/name /home/hadoop/dfs/data /var/lib/hadoop
chmod -R 775 /home/hadoop/tmp /home/hadoop/logs

# Configure passwordless sudo for Hadoop users
echo "🔧 Configuring passwordless sudo for Hadoop users..."
echo "hadoop ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers
echo "hdfs ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers
echo "yarn ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers

# Start Hadoop Services
echo "🔄 Checking if this is the NameNode..."
if [[ $HOSTNAME == "namenode" ]]; then
    echo "🖥 Namenode detected!"
    sleep 5
    if [ ! -d "/home/hadoop/dfs/name/current" ]; then
        echo "🛠 Formatting NameNode..."
        su - hdfs -c "$HADOOP_HOME/bin/hdfs namenode -format -force -nonInteractive"
    fi
    echo "🚀 Starting HDFS services..."
    su - hdfs -c "$HADOOP_HOME/sbin/start-dfs.sh"
    su - yarn -c "$HADOOP_HOME/sbin/start-yarn.sh"
    su - hdfs -c "$HADOOP_HOME/bin/hdfs namenode"
else
    echo "🖥 Starting DataNode..."
    sleep 10
    su - hdfs -c "$HADOOP_HOME/sbin/hadoop-daemon.sh start datanode"
    tail -f /dev/null
fi
