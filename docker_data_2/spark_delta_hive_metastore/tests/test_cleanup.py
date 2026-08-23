"""
Unit & Integration Tests for System Purge & Garbage Collection
"""

import pytest
import sys
import os
from fastapi.testclient import TestClient

# Add admin_panel to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../admin_panel")))

from backend.main import app
from backend import routes_cleanup

client = TestClient(app)

def test_cleanup_routes_registered():
    """Validates that cleanup purge endpoint is registered."""
    routes = [r.path for r in routes_cleanup.router.routes]
    assert "/purge" in routes or "/api/cleanup/purge" in routes

def test_execute_purge_endpoint(monkeypatch):
    """Validates that purge endpoint executes garbage collection safely."""
    monkeypatch.setattr(routes_cleanup.urllib.request, "urlopen", lambda req, timeout=3: type("MockRes", (), {"read": lambda: b'{"sessions": []}'})())
    
    class MockContainer:
        def exec_run(self, cmd):
            class MockResult:
                output = b"Done"
                exit_code = 0
            return MockResult()

    class MockDockerClient:
        class containers:
            @staticmethod
            def get(name):
                return MockContainer()

    monkeypatch.setattr(routes_cleanup.docker, "from_env", lambda: MockDockerClient())

    res = client.post("/api/cleanup/purge")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SUCCESS"
    assert "logs" in data
    assert len(data["logs"]) >= 1
