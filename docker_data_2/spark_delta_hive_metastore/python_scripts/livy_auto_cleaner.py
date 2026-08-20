"""
Automated Livy Session Auto-Pruner & Garbage Collector
Periodically scans Livy for idle, abandoned, or dead sessions and cleans them up to prevent cluster memory exhaustion.
"""
import time
import json
import urllib.request
import urllib.error

LIVY_URL = "http://livy:8998"

def list_livy_sessions():
    """Lists all active and idle Livy sessions."""
    try:
        req = urllib.request.Request(f"{LIVY_URL}/sessions", headers={"User-Agent": "LivyCleaner/1.0"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            return data.get("sessions", [])
    except Exception:
        # Try localhost if running outside container
        try:
            req = urllib.request.Request("http://localhost:8998/sessions", headers={"User-Agent": "LivyCleaner/1.0"})
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                return data.get("sessions", [])
        except Exception:
            return []

def delete_livy_session(session_id):
    """Terminates a specific Livy session by ID."""
    for base in [LIVY_URL, "http://localhost:8998"]:
        try:
            del_req = urllib.request.Request(f"{base}/sessions/{session_id}", method="DELETE")
            with urllib.request.urlopen(del_req, timeout=3) as resp:
                return True
        except Exception:
            pass
    return False

def prune_idle_sessions(max_idle_seconds=120):
    """
    Prunes sessions that are:
    1. Dead, shutting_down, or error states.
    2. Idle sessions that have completed their queries.
    """
    sessions = list_livy_sessions()
    pruned = []
    
    for s in sessions:
        sid = s.get("id")
        state = s.get("state")
        
        # Dead or errored
        if state in ["dead", "error", "killed", "shutting_down"]:
            if delete_livy_session(sid):
                pruned.append((sid, state))
        # Idle sessions holding executors
        elif state == "idle":
            if delete_livy_session(sid):
                pruned.append((sid, "idle_pruned"))
                
    return pruned

def run_cleaner_loop(interval_sec=45):
    """Continuous background loop."""
    print(f"[*] Livy Auto-Pruner Daemon started. Monitoring interval: {interval_sec}s")
    while True:
        try:
            cleaned = prune_idle_sessions()
            if cleaned:
                print(f"[+] Pruned {len(cleaned)} abandoned Livy session(s): {cleaned}")
        except Exception as e:
            print(f"[!] Error during prune cycle: {e}")
        time.sleep(interval_sec)

if __name__ == "__main__":
    run_cleaner_loop()
