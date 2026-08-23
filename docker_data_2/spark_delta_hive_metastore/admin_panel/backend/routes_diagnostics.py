"""
Cluster Diagnostics & Network Prober API Router
Executes automated full-mesh port connectivity probing across all cluster nodes.
"""

import subprocess
import os
from fastapi import APIRouter

router = APIRouter(prefix="/api/diagnostics", tags=["Cluster Diagnostics"])

@router.post("/run")
def run_diagnostics():
    """Runs the automated multi-port diagnostic script and returns output."""
    script_path = "/app/diagnose_cluster.sh" if os.path.exists("/app/diagnose_cluster.sh") else "diagnose_cluster.sh"
    try:
        proc = subprocess.run([script_path], capture_output=True, text=True, timeout=30)
        return {
            "exit_code": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr
        }
    except Exception as ex:
        return {
            "exit_code": 1,
            "stdout": "",
            "stderr": str(ex)
        }
