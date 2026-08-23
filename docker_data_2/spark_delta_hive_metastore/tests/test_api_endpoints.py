"""
FastAPI REST & WebSocket Endpoints Integration Tests
"""

import pytest
import sys
import os
from fastapi.testclient import TestClient

# Add admin_panel to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../admin_panel")))

from backend.main import app

client = TestClient(app)

def test_orchestrator_matrix_endpoint():
    """Validates /api/orchestrator/matrix returns valid services array and presets."""
    response = client.get("/api/orchestrator/matrix")
    assert response.status_code == 200
    data = response.json()
    assert "services" in data
    assert "presets" in data
    assert len(data["services"]) >= 15
    assert len(data["presets"]) >= 5

def test_orchestrator_resolve_endpoint():
    """Validates /api/orchestrator/resolve computes DAG dependency order correctly."""
    response = client.post("/api/orchestrator/resolve", json={"services": ["hue"]})
    assert response.status_code == 200
    data = response.json()
    assert "resolved_order" in data
    assert "postgres" in data["resolved_order"]
    assert "spark" in data["resolved_order"]
    assert "hue" in data["resolved_order"]

def test_sql_jobs_endpoint():
    """Validates /api/sql/jobs returns query job history."""
    response = client.get("/api/sql/jobs")
    assert response.status_code == 200
    data = response.json()
    assert "jobs" in data
    assert isinstance(data["jobs"], list)

def test_tuning_config_endpoint():
    """Validates /api/tuning/config returns active profile and presets."""
    response = client.get("/api/tuning/config")
    assert response.status_code == 200
    data = response.json()
    assert "active_profile" in data
    assert "presets" in data

def test_metastore_tables_endpoint():
    """Validates /api/metastore/tables endpoint responds with tables list."""
    response = client.get("/api/metastore/tables")
    assert response.status_code == 200
    data = response.json()
    assert "tables" in data
