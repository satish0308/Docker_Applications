"""
Unit & Integration Tests for Delta Lake Time-Travel & Maintenance Engine
"""

import pytest
import sys
import os
from fastapi.testclient import TestClient

# Add admin_panel to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../admin_panel")))

from backend.main import app
from backend import routes_delta

client = TestClient(app)

def test_delta_routes_registered():
    """Validates that Delta Lake maintenance routes are registered."""
    routes = [r.path for r in routes_delta.router.routes]
    assert "/history/{db}/{table}" in routes or "/api/delta/history/{db}/{table}" in routes
    assert "/snapshot/{db}/{table}" in routes or "/api/delta/snapshot/{db}/{table}" in routes
    assert "/optimize/{db}/{table}" in routes or "/api/delta/optimize/{db}/{table}" in routes
    assert "/vacuum/{db}/{table}" in routes or "/api/delta/vacuum/{db}/{table}" in routes
    assert "/restore/{db}/{table}" in routes or "/api/delta/restore/{db}/{table}" in routes

def test_optimize_sql_generation(monkeypatch):
    """Validates that OPTIMIZE and Z-Order SQL queries are generated accurately."""
    executed_queries = []

    def mock_execute_spark_sql(sql):
        executed_queries.append(sql)
        return {"success": True, "error": None, "output": "Compaction completed"}

    monkeypatch.setattr(routes_delta, "execute_spark_sql", mock_execute_spark_sql)

    # Test plain OPTIMIZE
    res1 = client.post("/api/delta/optimize/default/sales", json={"zorder_columns": ""})
    assert res1.status_code == 200
    assert "OPTIMIZE default.sales;" in executed_queries[-1]

    # Test OPTIMIZE with ZORDER
    res2 = client.post("/api/delta/optimize/default/sales", json={"zorder_columns": "date_key, store_id"})
    assert res2.status_code == 200
    assert "OPTIMIZE default.sales ZORDER BY (date_key, store_id);" in executed_queries[-1]

def test_vacuum_sql_generation(monkeypatch):
    """Validates that VACUUM SQL queries with custom retention hours are generated accurately."""
    executed_queries = []

    def mock_execute_spark_sql(sql):
        executed_queries.append(sql)
        return {"success": True, "error": None, "output": "Deleted 4 unreferenced files."}

    monkeypatch.setattr(routes_delta, "execute_spark_sql", mock_execute_spark_sql)

    res = client.post("/api/delta/vacuum/default/transactions", json={"retention_hours": 72})
    assert res.status_code == 200
    assert "VACUUM default.transactions RETAIN 72 HOURS;" in executed_queries[-1]

def test_restore_sql_generation(monkeypatch):
    """Validates that RESTORE table SQL queries are generated accurately."""
    executed_queries = []

    def mock_execute_spark_sql(sql):
        executed_queries.append(sql)
        return {"success": True, "error": None, "output": "Restored table to version 2."}

    monkeypatch.setattr(routes_delta, "execute_spark_sql", mock_execute_spark_sql)

    res = client.post("/api/delta/restore/default/customers", json={"version": 3})
    assert res.status_code == 200
    assert "RESTORE TABLE default.customers TO VERSION AS OF 3;" in executed_queries[-1]
