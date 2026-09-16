#!/usr/bin/env bash
# Frontend gate: typecheck, lint, tests, production build. Run from anywhere in the repo.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}/frontend"
echo "== typecheck"; npm run --silent typecheck
echo "== lint";      npm run --silent lint
echo "== test";      npm run --silent test
echo "== build";     rm -rf dist && npm run --silent build
echo "frontend gate: PASS"
