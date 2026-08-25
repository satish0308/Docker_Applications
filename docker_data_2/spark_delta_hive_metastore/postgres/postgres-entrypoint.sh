#!/bin/bash
set -e

PG_DATA_DIR="${PGDATA:-/var/lib/postgresql/data}"

# ==============================================================================
# Self-Healing PostgreSQL Metastore Auto-Recovery Engine
# ==============================================================================
# If PG_VERSION is missing (uninitialized or corrupted volume) but the directory
# contains leftover files/folders, initdb will fail with "exists but is not empty".
# This self-healing check detects corrupted state and cleans it automatically.
# ==============================================================================

if [ -d "$PG_DATA_DIR" ] && [ ! -f "$PG_DATA_DIR/PG_VERSION" ]; then
    # Check if directory has any files/subdirectories
    NON_EMPTY=$(ls -A "$PG_DATA_DIR" 2>/dev/null || true)
    if [ -n "$NON_EMPTY" ]; then
        echo "======================================================================"
        echo "⚠️  [Self-Healing Metastore Engine] Detected corrupted data directory in $PG_DATA_DIR."
        echo "💡  Reason: Volume is not empty but missing valid PG_VERSION metadata."
        echo "🧹  Automatically purging corrupted artifacts for fresh clean initialization..."
        echo "======================================================================"
        find "$PG_DATA_DIR" -mindepth 1 -delete 2>/dev/null || rm -rf "$PG_DATA_DIR"/* "$PG_DATA_DIR"/.[!.]* 2>/dev/null || true
        echo "✅  Corrupted artifacts purged. Proceeding with clean initialization."
    fi
fi

# Delegate execution to official PostgreSQL entrypoint
exec /usr/local/bin/docker-entrypoint.sh "$@"
