"""
Unit & Integration Tests for Table Backup & Disaster Recovery Engine
"""

import pytest
import sys
import os
from fastapi.testclient import TestClient

# Add admin_panel to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../admin_panel")))

from backend.main import app
from backend import routes_backup

client = TestClient(app)

def test_backup_routes_registered():
    """Validates that Backup & Restore routes are registered."""
    routes = [r.path for r in routes_backup.router.routes]
    assert "/list" in routes or "/api/backup/list" in routes
    assert "/execute" in routes or "/api/backup/execute" in routes
    assert "/restore" in routes or "/api/backup/restore" in routes

def test_backup_list_empty_or_valid():
    """Validates that /api/backup/list returns a structured list of backups."""
    res = client.get("/api/backup/list")
    assert res.status_code == 200
    data = res.json()
    assert "backups" in data
    assert isinstance(data["backups"], list)

def test_execute_backup_command_construction(monkeypatch):
    """Validates that spark-submit backup command is constructed properly."""
    executed_cmds = []

    class MockContainer:
        def exec_run(self, cmd):
            executed_cmds.append(cmd)
            class MockResult:
                output = b"Backup completed successfully"
                exit_code = 0
            return MockResult()

    class MockDockerClient:
        class containers:
            @staticmethod
            def get(name):
                return MockContainer()

    monkeypatch.setattr(routes_backup.docker, "from_env", lambda: MockDockerClient())

    # Single Table Backup
    res1 = client.post("/api/backup/execute", json={
        "mode": "table",
        "database": "default",
        "table": "sales",
        "custom_backup_id": "backup_sales_test"
    })
    assert res1.status_code == 200
    assert "backup --table default.sales --backup-id backup_sales_test" in executed_cmds[-1]

    # Full Database Backup
    res2 = client.post("/api/backup/execute", json={
        "mode": "database",
        "database": "analytics"
    })
    assert res2.status_code == 200
    assert "backup-db --database analytics" in executed_cmds[-1]

def test_execute_restore_command_construction(monkeypatch):
    """Validates that spark-submit restore command is constructed properly."""
    executed_cmds = []

    class MockContainer:
        def exec_run(self, cmd):
            executed_cmds.append(cmd)
            class MockResult:
                output = b"Restore completed successfully"
                exit_code = 0
            return MockResult()

    class MockDockerClient:
        class containers:
            @staticmethod
            def get(name):
                return MockContainer()

    monkeypatch.setattr(routes_backup.docker, "from_env", lambda: MockDockerClient())

    res = client.post("/api/backup/restore", json={
        "backup_id": "backup_sales_2026",
        "mode": "table",
        "target_database": "default",
        "target_table": "sales_restored",
        "storage_dest": "s3a://warehouse/"
    })
    assert res.status_code == 200
    assert "restore --backup-id backup_sales_2026 --target-table sales_restored --storage-dest s3a://warehouse/" in executed_cmds[-1]
