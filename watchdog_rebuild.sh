#!/bin/bash
# Continuous Watchdog Script

# Configuration
REPO_ROOT="."
COMPOSE_DIR="$REPO_ROOT/docker_data_2/spark_delta_hive_metastore"
BRANCH="bdp_opt"
CHECK_INTERVAL=60 # seconds

echo "👀 Starting BDP environment watchdog on branch $BRANCH..."

while true; do
    echo "🔄 Checking for updates from origin/$BRANCH..."

    # Navigate to repo root
    cd "$REPO_ROOT"

    # Fetch latest changes
    git fetch origin

    # Check if local branch is behind origin
    LOCAL=$(git rev-parse HEAD)
    REMOTE=$(git rev-parse "origin/$BRANCH")

    if [ "$LOCAL" != "$REMOTE" ]; then
        echo "⬇️ Updates found. Pulling latest code..."
        git pull origin "$BRANCH"
        
        echo "🛑 Bringing down existing stack..."
        if [ -d "$COMPOSE_DIR" ]; then
            cd "$COMPOSE_DIR"
            docker compose down
            
            echo "🏗️ Rebuilding images and starting stack..."
            docker compose up -d --build
            
            echo "✅ Update and rebuild complete."
        else
            echo "❌ Directory $COMPOSE_DIR not found!"
        fi
    else
        echo "✅ No updates found."
    fi

    echo "💤 Sleeping for $CHECK_INTERVAL seconds..."
    sleep $CHECK_INTERVAL
done
