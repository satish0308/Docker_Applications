#!/bin/bash
set -ex  # Enable debug mode (-x) and exit on error (-e)

LOG_FILE="/var/log/hadoop_entrypoint.log"
exec > >(tee -a $LOG_FILE) 2>&1  # Log all output

echo "========================================"
echo "🚀 Starting Hadoop & Hive Initialization V4 (Debug Mode)"
echo "========================================"

# Ensure SSH service is running
echo "🚀 Starting SSH service..."
service ssh start || { echo "❌ ERROR: Failed to start SSH service"; exit 1; }

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

# Function to setup SSH for a user
setup_ssh() {
  local user=$1
  local home_dir=$(eval echo ~$user)

  echo "📁 Ensuring SSH directory exists for $user..."
  mkdir -p $home_dir/.ssh
  chmod 700 $home_dir/.ssh
  chown -R $user:$user $home_dir/.ssh

  # Generate SSH key if it doesn't exist
  if [ ! -f "$home_dir/.ssh/id_rsa" ]; then
    echo "🔑 Generating new SSH key for $user..."
    sudo -u $user ssh-keygen -t rsa -b 4096 -N "" -f $home_dir/.ssh/id_rsa
  fi

  chmod 600 $home_dir/.ssh/id_rsa
  chmod 644 $home_dir/.ssh/id_rsa.pub
  chown $user:$user $home_dir/.ssh/id_rsa $home_dir/.ssh/id_rsa.pub

  # Append public key to authorized_keys if not already added
  grep -qF "$(cat $home_dir/.ssh/id_rsa.pub)" $home_dir/.ssh/authorized_keys 2>/dev/null || cat $home_dir/.ssh/id_rsa.pub >> $home_dir/.ssh/authorized_keys
  chmod 600 $home_dir/.ssh/authorized_keys
  chown $user:$user $home_dir/.ssh/authorized_keys

  # Disable strict host key checking
  echo "StrictHostKeyChecking no" > $home_dir/.ssh/config
  chmod 600 $home_dir/.ssh/config
  chown $user:$user $home_dir/.ssh/config

  # Ensure localhost is a known host
  echo "🔍 Scanning localhost SSH keys..."
  ssh-keyscan -H localhost >> $home_dir/.ssh/known_hosts 2>/dev/null
  chmod 644 $home_dir/.ssh/known_hosts
  chown $user:$user $home_dir/.ssh/known_hosts
}

# Setup SSH for all users
setup_ssh hadoop
setup_ssh hdfs
setup_ssh yarn

# Validate passwordless SSH for each user
validate_ssh() {
    local user=$1
    local hosts=("localhost" "namenode" "datanode" "resourcemanager")  # Add all relevant hosts

    for host in "${hosts[@]}"; do
        echo "🔄 Testing passwordless SSH for $user to $host..."
        sudo -u $user ssh -o StrictHostKeyChecking=no -o BatchMode=yes $host exit || { 
            echo "❌ ERROR: Passwordless SSH setup for $user to $host failed!"; 
            exit 1; 
        }
    done
}




# Add users to appropriate groups
echo "👥 Adding Hadoop users to groups..."
usermod -aG hadoop hdfs
usermod -aG hadoop yarn
usermod -aG hdfs hadoop
usermod -aG hdfs yarn
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

# Update SSH configuration
echo "Configuring SSH..."

# Ensure required SSH configurations are set
sed -i '/^AllowUsers/d' /etc/ssh/sshd_config
sed -i '/^PubkeyAuthentication/d' /etc/ssh/sshd_config
sed -i '/^PasswordAuthentication/d' /etc/ssh/sshd_config
sed -i '/^AuthorizedKeysFile/d' /etc/ssh/sshd_config
sed -i '/^PermitRootLogin/d' /etc/ssh/sshd_config

# Append required configurations
echo "AllowUsers hadoop root hdfs yarn" >> /etc/ssh/sshd_config
echo "PubkeyAuthentication yes" >> /etc/ssh/sshd_config
echo "PasswordAuthentication no" >> /etc/ssh/sshd_config
echo "AuthorizedKeysFile .ssh/authorized_keys" >> /etc/ssh/sshd_config
echo "PermitRootLogin yes" >> /etc/ssh/sshd_config

# Restart SSH service
echo "Restarting SSH service..."
service ssh restart || systemctl restart ssh

if ! service ssh restart; then
    echo "⚠️ Warning: Failed to restart SSH via service command, trying systemctl..."
    systemctl restart ssh || { echo "❌ ERROR: SSH restart failed!"; exit 1; }
fi



echo "SSH configuration updated successfully!"

# validate_ssh hadoop
# validate_ssh hdfs
# validate_ssh yarn

# # Start Hadoop Services
# echo "🔄 Checking if this is the NameNode..."
# if [[ $HOSTNAME == "namenode" ]]; then
#     echo "🖥 Namenode detected!"
#     sleep 10
#     if [ ! -d "/home/hadoop/dfs/name/current" ]; then
#         echo "🛠 Formatting NameNode..."
#         su - hdfs -c "$HADOOP_HOME/bin/hdfs namenode -format -force -nonInteractive"
#     fi
#     echo "🚀 Starting HDFS services..."
#     su - hdfs -c "$HADOOP_HOME/sbin/start-dfs.sh"
#     su - yarn -c "$HADOOP_HOME/sbin/start-yarn.sh"
#     su - hdfs -c "$HADOOP_HOME/bin/hdfs namenode"
# else
#     echo "🖥 Starting DataNode..."
#     sleep 10
#     su - hdfs -c "$HADOOP_HOME/sbin/hadoop-daemon.sh start datanode"
#     tail -f /dev/null
# fi

#!/bin/bash


#!/bin/bash

#!/bin/bash

echo "🔄 Checking if this is the NameNode..."
if [[ $HOSTNAME == "namenode" ]]; then
    echo "🖥 Namenode detected!"
    sleep 10

    # Ensure PID file does not block NameNode startup
    if [ -f "/tmp/hadoop-hdfs-namenode.pid" ]; then
        echo "🛑 Stale PID file detected. Removing it..."
        rm -f /tmp/hadoop-hdfs-namenode.pid
    fi

    # Check if NameNode is already running
    if jps | grep -q "NameNode"; then
        echo "✅ NameNode is already running."
    else
        # Format only if necessary
        if [ ! -d "/home/hadoop/dfs/name/current" ]; then
            echo "🛠 Formatting NameNode..."
            su - hdfs -c "$HADOOP_HOME/bin/hdfs namenode -format -force -nonInteractive"
        fi
        
        echo "🚀 Starting HDFS services..."
        su - hdfs -c "$HADOOP_HOME/sbin/start-dfs.sh"

        sleep 60

        su - yarn -c "$HADOOP_HOME/sbin/start-yarn.sh"
    fi

    # Keep container running
    echo "📌 Keeping the container alive..."
    tail -f /dev/null  # This prevents the container from exiting
else
    echo "🖥 Starting DataNode..."
    sleep 10
    su - hdfs -c "$HADOOP_HOME/sbin/hadoop-daemon.sh start datanode"

    # Keep DataNode container running
    tail -f /dev/null
fi


