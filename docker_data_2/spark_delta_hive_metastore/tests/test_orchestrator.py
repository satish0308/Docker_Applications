"""
Unit & Integration Tests for Selective Pod Orchestrator & Dependency Resolver
"""

import pytest
import sys
import os

# Add admin_panel to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../admin_panel")))

import service_orchestrator

def test_service_registry_integrity():
    """Validates that all services in registry have valid metadata, ports, and dependencies."""
    registry = service_orchestrator.SERVICE_REGISTRY
    assert len(registry) >= 15, "Registry should contain all 15 platform services"

    for key, meta in registry.items():
        assert "name" in meta
        assert "container" in meta
        assert "compose_service" in meta
        assert "tier" in meta
        assert "icon" in meta
        assert "dependencies" in meta
        assert isinstance(meta["dependencies"], list)

        # Validate that all dependencies point to existing services in registry
        for dep in meta["dependencies"]:
            assert dep in registry, f"Dependency '{dep}' of '{key}' is not defined in SERVICE_REGISTRY"

def test_topological_dependency_resolution_hue():
    """Validates that selecting Hue Studio resolves all upstream foundational pods in correct order."""
    resolved = service_orchestrator.resolve_dependencies(["hue"])
    
    # Foundational services must precede Hue
    assert "postgres" in resolved
    assert "namenode" in resolved
    assert "datanode" in resolved
    assert "hive" in resolved
    assert "spark" in resolved
    assert "spark-worker" in resolved
    assert "livy" in resolved
    assert "hue" in resolved

    # Check topological order: postgres, namenode before spark; spark before livy; livy before hue
    assert resolved.index("postgres") < resolved.index("spark")
    assert resolved.index("namenode") < resolved.index("datanode")
    assert resolved.index("datanode") < resolved.index("spark")
    assert resolved.index("spark") < resolved.index("spark-worker")
    assert resolved.index("spark-worker") < resolved.index("livy")
    assert resolved.index("livy") < resolved.index("hue")

def test_topological_dependency_resolution_jupyter():
    """Validates that selecting Jupyter Notebooks resolves MinIO, Keycloak, and Spark in correct order."""
    resolved = service_orchestrator.resolve_dependencies(["jupyter"])

    assert "postgres" in resolved
    assert "keycloak" in resolved
    assert "minio" in resolved
    assert "spark" in resolved
    assert "jupyter" in resolved

    assert resolved.index("postgres") < resolved.index("keycloak")
    assert resolved.index("keycloak") < resolved.index("minio")
    assert resolved.index("spark") < resolved.index("jupyter")

def test_operational_presets_validity():
    """Validates that all 1-click operational presets resolve without errors."""
    presets = service_orchestrator.OPERATIONAL_PRESETS
    assert len(presets) >= 5

    for name, data in presets.items():
        assert "services" in data
        assert "desc" in data
        assert "est_ram" in data
        
        resolved = service_orchestrator.resolve_dependencies(data["services"])
        assert len(resolved) >= len(data["services"])

def test_get_downstream_dependents_cascade():
    """Validates that stopping postgres cascades downstream to keycloak, hive, spark, and hue."""
    running_services = ["postgres", "keycloak", "hive", "spark", "spark-worker", "livy", "hue"]
    downstream = service_orchestrator.get_downstream_dependents("postgres", running_services)

    assert "keycloak" in downstream
    assert "hive" in downstream
    assert "spark" in downstream
    assert "hue" in downstream
