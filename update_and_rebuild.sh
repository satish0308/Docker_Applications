#!/bin/bash
set -e

# Configuration
REPO_ROOT="/workspaces/Docker_Applications"
COMPOSE_DIR="$REPO_ROOT/docker_data_2/spark_delta_hive_metastore"
BRANCH="bdp_opt"

echo "🔄 Checking for updates from origin/$BRANCH..."

# Navigate to repo root if not already there
if [ "$(pwd)" != "$REPO_ROOT" ]; then
    cd "$REPO_ROOT"
fi

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
        docker-compose down
    else
        echo "❌ Directory $COMPOSE_DIR not found!"
        exit 1
    fi
    
    echo "🏗️ Rebuilding images and starting stack..."
    docker-compose up -d --build --parallel
    
    echo "✅ Update and rebuild complete."
else
    echo "✅ No updates found. Environment is up to date."
fi
