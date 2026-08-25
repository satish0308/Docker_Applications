"""
Unit and integration tests for AWS S3 Cloud Stream & File Explorer APIs
"""

import pytest
import sys
import os
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../admin_panel")))

from backend.main import app
from backend import routes_ingestion

client = TestClient(app)

def test_s3_routes_registered():
    """Validates that AWS S3 streaming and browser endpoints are mounted in FastAPI router."""
    routes = [r.path for r in routes_ingestion.router.routes]
    assert any("/s3/test-connection" in r for r in routes)
    assert any("/s3/list-buckets" in r for r in routes)
    assert any("/s3/browse" in r for r in routes)
    assert any("/s3/preview-schema" in r for r in routes)
    assert any("/s3/submit-stream" in r for r in routes)

def test_s3_test_connection_validation():
    """Validates 400 rejection when required AWS keys are missing."""
    resp = client.post("/api/ingestion/s3/test-connection", json={
        "aws_access_key": "",
        "aws_secret_key": "",
        "aws_region": "us-east-1"
    })
    assert resp.status_code == 400

@patch("backend.routes_ingestion.get_s3_client")
def test_s3_test_connection_success(mock_get_client):
    """Validates S3 connection test with mock boto3 client."""
    mock_s3 = MagicMock()
    mock_s3.list_buckets.return_value = {
        "Buckets": [{"Name": "analytics-raw-bucket"}, {"Name": "sales-lake"}]
    }
    mock_get_client.return_value = mock_s3

    resp = client.post("/api/ingestion/s3/test-connection", json={
        "aws_access_key": "MOCK_AWS_ACCESS_KEY_ID_1234",
        "aws_secret_key": "MOCK_AWS_SECRET_ACCESS_KEY_5678",
        "aws_region": "us-east-1"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SUCCESS"
    assert "analytics-raw-bucket" in data["buckets"]
    assert "sales-lake" in data["buckets"]

@patch("backend.routes_ingestion.get_s3_client")
def test_s3_browse_folders_and_files(mock_get_client):
    """Validates S3 folder explorer parsing common prefixes and file objects."""
    mock_s3 = MagicMock()
    paginator_mock = MagicMock()
    mock_s3.get_paginator.return_value = paginator_mock
    
    # Mock pagination response
    paginator_mock.paginate.return_value = [{
        "CommonPrefixes": [{"Prefix": "sales/2026/08/"}, {"Prefix": "sales/2026/09/"}],
        "Contents": [
            {
                "Key": "sales/2026/part-001.parquet",
                "Size": 2097152,
                "LastModified": None
            },
            {
                "Key": "sales/2026/customers.csv",
                "Size": 102400,
                "LastModified": None
            }
        ]
    }]
    mock_get_client.return_value = mock_s3

    resp = client.post("/api/ingestion/s3/browse", json={
        "aws_access_key": "MOCK_AWS_ACCESS_KEY_ID_1234",
        "aws_secret_key": "MOCK_AWS_SECRET_ACCESS_KEY_5678",
        "aws_region": "us-east-1",
        "bucket": "sales-lake",
        "prefix": "sales/2026/"
      })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SUCCESS"
    assert data["bucket"] == "sales-lake"
    assert len(data["folders"]) == 2
    assert len(data["files"]) == 2
    filenames = [f["name"] for f in data["files"]]
    assert "part-001.parquet" in filenames
    assert "customers.csv" in filenames

@patch("backend.routes_ingestion.get_s3_client")
def test_s3_submit_stream_job_construction(mock_get_client):
    """Validates submission of S3 streaming job into persistent job queue."""
    mock_s3 = MagicMock()
    mock_get_client.return_value = mock_s3

    resp = client.post("/api/ingestion/s3/submit-stream", json={
        "aws_access_key": "MOCK_AWS_ACCESS_KEY_ID_1234",
        "aws_secret_key": "MOCK_AWS_SECRET_ACCESS_KEY_5678",
        "aws_region": "us-east-1",
        "bucket": "sales-lake",
        "source_prefix": "sales/2026/",
        "selected_files": ["sales/2026/part-001.parquet"],
        "mode": "batch",
        "target_database": "default",
        "target_table": "sales_lake_s3",
        "table_format": "delta",
        "write_mode": "append",
        "dest_storage": "s3",
        "partition_cols": "country"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SUCCESS"
    assert "s3_stream_sales_lake_s3" in data["job_id"]
