"""
Unit & Integration Tests for Spark Dynamic Tuning & Resource Allocation Engine
"""

import pytest
import sys
import os

# Add admin_panel to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../admin_panel")))

import spark_tuning_manager

def test_tuning_profiles_defined():
    """Validates that all expected workload sizing profiles exist with necessary parameters."""
    profiles = spark_tuning_manager.PROFILES
    assert len(profiles) >= 5

    required_keys = [
        "driver_memory", "executor_memory", "executor_cores", 
        "max_cores", "shuffle_partitions", "aqe_enabled", 
        "memory_fraction", "storage_fraction", "offheap_enabled"
    ]

    for prof_name, params in profiles.items():
        for k in required_keys:
            assert k in params, f"Profile '{prof_name}' is missing parameter '{k}'"

def test_recommend_profile_for_filesize():
    """Validates automatic profile recommendation based on dataset input size."""
    # <100MB -> Light
    small_rec, size_mb = spark_tuning_manager.recommend_profile_for_filesize(50 * 1024 * 1024)
    assert "Light" in small_rec

    # 500MB -> Medium
    med_rec, _ = spark_tuning_manager.recommend_profile_for_filesize(500 * 1024 * 1024)
    assert "Medium" in med_rec

    # 5GB -> Heavy
    heavy_rec, _ = spark_tuning_manager.recommend_profile_for_filesize(5 * 1024 * 1024 * 1024)
    assert "Heavy" in heavy_rec

    # 50GB -> Extreme
    extreme_rec, _ = spark_tuning_manager.recommend_profile_for_filesize(50 * 1024 * 1024 * 1024)
    assert "Extreme" in extreme_rec

def test_build_spark_submit_conf_args():
    """Validates that CLI spark-submit arguments are correctly constructed from parameters."""
    params = {
        "driver_memory": "4g",
        "executor_memory": "8g",
        "executor_cores": 4,
        "max_cores": 8,
        "shuffle_partitions": 200,
        "aqe_enabled": True,
        "aqe_coalesce": True,
        "memory_fraction": 0.8,
        "storage_fraction": 0.4,
        "offheap_enabled": True,
        "offheap_size": "1g",
        "kryo_serializer": True
    }

    args = spark_tuning_manager.build_spark_submit_conf_args(params)
    assert "--driver-memory 4g" in args
    assert "--executor-memory 8g" in args
    assert "spark.executor.cores=4" in args
    assert "spark.sql.shuffle.partitions=200" in args
    assert "spark.sql.adaptive.enabled=true" in args
    assert "spark.memory.offHeap.enabled=true" in args
    assert "spark.memory.offHeap.size=1g" in args
    assert "KryoSerializer" in args
