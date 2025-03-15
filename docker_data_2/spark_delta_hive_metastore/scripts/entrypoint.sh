#!/bin/bash
set -e


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
