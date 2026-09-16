#!/usr/bin/env bash
# Backend gate: format check, lint, full pytest. Run from anywhere in the repo.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="${ROOT}/.venv/bin/python"
cd "${ROOT}/backend"
echo "== ruff format --check"; "${ROOT}/.venv/bin/ruff" format --check app tests
echo "== ruff check";          "${ROOT}/.venv/bin/ruff" check app tests
echo "== pytest";              "${PY}" -m pytest tests -q
echo "backend gate: PASS"
