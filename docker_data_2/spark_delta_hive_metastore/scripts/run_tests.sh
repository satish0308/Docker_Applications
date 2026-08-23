#!/usr/bin/env bash
# ==============================================================================
# BDP Platform Local Test Runner
# Executes test suites across Frontend, Backend APIs, and Topological Resolvers
# ==============================================================================
set -euo pipefail

echo "============================================================"
echo "🧪 Running BDP Platform Automated Test Suites"
echo "============================================================"

# Check if running inside container or host
if docker ps --format '{{.Names}}' | grep -q "^admin-panel$"; then
    echo "📦 Executing pytest test suites inside admin-panel container..."
    docker exec admin-panel pytest -o cache_dir=/tmp/.pytest_cache /workspace/tests/ -v
else
    echo "🐍 Executing pytest locally..."
    pytest tests/ -v
fi

echo "============================================================"
echo "✅ All platform component test suites passed successfully!"
echo "============================================================"
