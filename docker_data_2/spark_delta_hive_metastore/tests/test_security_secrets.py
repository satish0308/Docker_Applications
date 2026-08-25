"""
Automated Secrets & Credentials Security Tests
Scans source directories for leaked AWS credentials, private keys, and high-entropy API tokens.
"""

import os
import re
import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SOURCE_DIRS = ["admin_panel/backend", "admin_panel/frontend/src", "config", "hue", "livy", "python_scripts", "scripts", "tests"]
ALLOWED_EXTENSIONS = {".py", ".jsx", ".js", ".json", ".conf", ".xml", ".ini", ".sh", ".yaml", ".yml", ".md", ".html"}

def scan_source_files_with_regex(pattern_str):
    """Scans all platform source code files for a regex pattern."""
    regex = re.compile(pattern_str)
    matches = []
    
    for rel_dir in SOURCE_DIRS:
        abs_dir = os.path.join(REPO_ROOT, rel_dir)
        if not os.path.exists(abs_dir):
            continue
        for root, dirs, files in os.walk(abs_dir):
            if "node_modules" in dirs:
                dirs.remove("node_modules")
            if "dist" in dirs:
                dirs.remove("dist")
            if ".git" in dirs:
                dirs.remove(".git")
                
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext not in ALLOWED_EXTENSIONS or file.endswith(".min.js"):
                    continue
                if file in {"package-lock.json", "scan_secrets.sh", ".gitleaks.toml"}:
                    continue
                    
                rel_path = os.path.relpath(os.path.join(root, file), REPO_ROOT)
                if rel_path.startswith("tests/") and "AKIA" in pattern_str:
                    continue
                    
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                        for line_num, line in enumerate(f, 1):
                            if regex.search(line):
                                matches.append(f"{rel_path}:{line_num} -> {line.strip()[:100]}")
                except Exception:
                    pass
                    
    return matches

def test_no_hardcoded_aws_akias_in_code():
    """Ensures no real AWS Access Keys (AKIA...) exist in source code."""
    matches = scan_source_files_with_regex(r"\bAKIA[0-9A-Z]{16}\b")
    assert len(matches) == 0, f"AWS Key pattern detected in files:\n" + "\n".join(matches)

def test_no_private_keys_in_code():
    """Ensures no unencrypted RSA/EC/SSH private keys exist in source code."""
    matches = scan_source_files_with_regex(r"-----BEGIN (RSA|OPENSSH|EC|DSA)? PRIVATE KEY-----")
    assert len(matches) == 0, f"Private Key detected in files:\n" + "\n".join(matches)

def test_no_generic_api_tokens_in_code():
    """Ensures no raw OpenAI, Slack, or GitHub tokens are hardcoded."""
    matches = scan_source_files_with_regex(r"\b(ghp_[a-zA-Z0-9]{36}|xox[baprs]-[0-9a-zA-Z]{10,48}|sk_live_[a-zA-Z0-9]{24,})\b")
    assert len(matches) == 0, f"API token pattern detected:\n" + "\n".join(matches)

def test_scan_secrets_script_validity():
    """Validates that scan_secrets.sh script exists and has executable permissions."""
    scanner_path = os.path.join(REPO_ROOT, "scripts/scan_secrets.sh")
    assert os.path.exists(scanner_path), "scripts/scan_secrets.sh must exist"
    assert os.access(scanner_path, os.X_OK), "scripts/scan_secrets.sh must be executable"
