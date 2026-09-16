#!/usr/bin/env bash
# Health check against a running backend. Usage: scripts/healthcheck.sh [base_url]
# Default base_url is the local systemd/uvicorn port; pass https://electrical.kamraengineeringsolution.com after deploy.
set -euo pipefail
BASE="${1:-http://127.0.0.1:8040}"
PREFIX="${API_V1_PREFIX:-/api/v1}"
for path in "${PREFIX}/health" "${PREFIX}/version"; do
  code="$(curl -s -o /tmp/keos_hc_body -w '%{http_code}' --max-time 10 "${BASE}${path}")"
  body="$(cat /tmp/keos_hc_body)"
  echo "${path} -> HTTP ${code} ${body}"
  [ "${code}" = "200" ] || { echo "healthcheck: FAIL"; exit 1; }
done
echo "healthcheck: PASS"
