"""
Unit & Integration Tests for Scheduled Ingestion Jobs
"""

import pytest
import sys
import os
from fastapi.testclient import TestClient

# Add admin_panel to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../admin_panel")))

from backend.main import app
from backend import routes_schedule

client = TestClient(app)

def test_schedule_routes_registered():
    """Validates that scheduled jobs endpoints are mounted on FastAPI."""
    routes = [r.path for r in routes_schedule.router.routes]
    assert "/jobs" in routes or "/api/schedule/jobs" in routes
    assert "/create" in routes or "/api/schedule/create" in routes

def test_create_and_delete_scheduled_job():
    """Validates creating, toggling, and deleting a scheduled pipeline definition."""
    # 1. Create Job
    res = client.post("/api/schedule/create", json={
        "name": "test_pipeline",
        "watch_path": "/tmp/*.csv",
        "target_database": "default",
        "target_table": "test_tbl",
        "format": "delta",
        "interval": "Hourly"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SUCCESS"
    job_id = data["job"]["job_id"]

    # 2. Toggle Job
    res_toggle = client.post(f"/api/schedule/toggle/{job_id}")
    assert res_toggle.status_code == 200

    # 3. Delete Job
    res_del = client.delete(f"/api/schedule/{job_id}")
    assert res_del.status_code == 200
