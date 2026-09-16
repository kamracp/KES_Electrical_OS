#!/usr/bin/env bash
# Full regression: backend gate then frontend gate. Non-zero exit on the first failure.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
"${ROOT}/scripts/check_backend.sh"
"${ROOT}/scripts/check_frontend.sh"
echo "full regression: PASS"
