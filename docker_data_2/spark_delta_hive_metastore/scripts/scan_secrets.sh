#!/usr/bin/env bash
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${CYAN}${BOLD}============================================================${NC}"
echo -e "${CYAN}${BOLD}🔍 Automated Pre-Push Secrets & Credential Security Scanner${NC}"
echo -e "${CYAN}${BOLD}============================================================${NC}"

cd "${REPO_ROOT}"
LEAKS_FOUND=0

# 1. Regex Pattern Engine for High-Risk Cloud & API Keys
echo -e "\n${BOLD}[1/3] Scanning Working Tree for AWS & Cloud Credentials...${NC}"

PATTERNS=(
  "AKIA[0-9A-Z]{16}"
  "ASIA[0-9A-Z]{16}"
  "-----BEGIN (RSA|OPENSSH|EC|DSA)? PRIVATE KEY-----"
  "ghp_[a-zA-Z0-9]{36}"
  "xox[baprs]-[0-9a-zA-Z]{10,48}"
  "sk-[a-zA-Z0-9]{32,}"
  "sk_live_[a-zA-Z0-9]{24,}"
)

for PATTERN in "${PATTERNS[@]}"; do
  MATCHES=$(git grep -E -I -n -e "${PATTERN}" -- ':!tests/' ':!data/' ':!scripts/scan_secrets.sh' ':!.gitleaks.toml' || true)
  if [ -n "${MATCHES}" ]; then
    echo -e "${RED}❌ High-risk secret pattern matched: ${PATTERN}${NC}"
    echo -e "${RED}${MATCHES}${NC}"
    LEAKS_FOUND=$((LEAKS_FOUND + 1))
  fi
done

if [ ${LEAKS_FOUND} -eq 0 ]; then
  echo -e "${GREEN}✅ No unmasked AWS, Cloud, or Private API keys found in tracked source files.${NC}"
fi

# 2. Yelp detect-secrets Entropy & Heuristic Scanner
echo -e "\n${BOLD}[2/3] Running Yelp detect-secrets Entropy & Heuristic Scanner...${NC}"
if command -v detect-secrets >/dev/null 2>&1; then
  DETECT_OUTPUT=$(git ls-files | grep -v -E '(^tests/|^data/|package-lock.json|\.png|\.jpg|\.csv|\.parquet|\.lock)' | xargs detect-secrets scan 2>/dev/null || true)
  DETECT_COUNT=$(echo "${DETECT_OUTPUT}" | python3 -c '
import sys, json
try:
    data = json.load(sys.stdin)
    results = data.get("results", {})
    count = sum(len(v) for v in results.values())
    if count > 0:
        for f, items in results.items():
            for item in items:
                print(f"  - {f}: {item.get(\"type\")} (line {item.get(\"line_number\")})")
    print(f"COUNT:{count}")
except Exception:
    print("COUNT:0")
' 2>/dev/null || echo "COUNT:0")

  if [[ "${DETECT_COUNT}" == *"COUNT:0"* ]]; then
    echo -e "${GREEN}✅ detect-secrets passed: 0 high-entropy secrets detected.${NC}"
  else
    echo -e "${YELLOW}⚠️ detect-secrets findings:${NC}"
    echo "${DETECT_COUNT}"
  fi
else
  echo -e "${YELLOW}⚠️ detect-secrets CLI not installed in path; skipping step 2.${NC}"
fi

# 3. Gitleaks Deep Repository & Staged Changes Audit
echo -e "\n${BOLD}[3/3] Running Gitleaks Deep Commit & Staged Changes Audit...${NC}"
GITLEAKS_BIN="${REPO_ROOT}/scripts/bin/gitleaks"
if [ -x "${GITLEAKS_BIN}" ]; then
  if "${GITLEAKS_BIN}" detect --log-opts="HEAD~15..HEAD" --config="${REPO_ROOT}/.gitleaks.toml" --verbose; then
    echo -e "${GREEN}✅ Gitleaks audit passed: 0 secret leaks found across recent commits.${NC}"
  else
    echo -e "${RED}❌ Gitleaks detected secrets in commit range.${NC}"
    LEAKS_FOUND=$((LEAKS_FOUND + 1))
  fi
else
  echo -e "${YELLOW}⚠️ Gitleaks binary not found at ${GITLEAKS_BIN}.${NC}"
fi

echo -e "\n${CYAN}${BOLD}============================================================${NC}"
if [ ${LEAKS_FOUND} -eq 0 ]; then
  echo -e "${GREEN}${BOLD}🎉 Secrets Security Scan PASSED! Repository is safe for git push.${NC}"
  echo -e "${CYAN}${BOLD}============================================================${NC}"
  exit 0
else
  echo -e "${RED}${BOLD}🚨 Secrets Security Scan FAILED! ${LEAKS_FOUND} potential leak(s) found.${NC}"
  echo -e "${RED}Please redact or remove sensitive credentials before pushing.${NC}"
  echo -e "${CYAN}${BOLD}============================================================${NC}"
  exit 1
fi
