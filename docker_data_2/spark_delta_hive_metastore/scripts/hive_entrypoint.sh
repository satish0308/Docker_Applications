#!/bin/bash
set -e

# Start Hadoop (necessary for Hive)
$HADOOP_HOME/sbin/start-dfs.sh

# echo "++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++"

# # Check if the Hive schema is already initialized using PostgreSQL directly
# SCHEMA_EXISTS=$(psql -U hiveuser -d metastore -tAc "SELECT COUNT(*) FROM BUCKETING_COLS;" 2>/dev/null || echo "0")

# if [[ "$SCHEMA_EXISTS" -gt 0 ]]; then
#     echo "Hive schema already initialized. Skipping initialization."
# else
#     echo "Initializing Hive schema..."
#     schematool -dbType postgres -initSchema || echo "Schema already initialized or encountered an error"
# fi

# echo "++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++"
# Check if schema exists before initializing
if ! schematool -info -dbType postgres > /dev/null 2>&1; then
    echo "Initializing Hive Metastore schema..."
    schematool -initSchema -dbType postgres
else
    echo "Hive Metastore schema already exists. Skipping initialization."
fi



# Start Hive Metastore in the background
hive --service metastore &

# Start HiveServer2 in the background
hive --service hiveserver2 &

# Keep the container running
tail -f /dev/null
