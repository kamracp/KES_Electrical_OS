#!/usr/bin/env bash
# Deploy KES Electrical OS to the Lightsail instance.
#   Backend: git checkout of the pushed commit on the server, pip install, Alembic upgrade, systemd restart.
#   Frontend: built locally, rsynced to the nginx web root (no Node.js required on the server).
# Nothing is edited by hand on the server; every change arrives via git or rsync.
#
# Usage: scripts/deploy.sh [--skip-gate]
# Required environment (put in ~/.keos-deploy.env and `source` it; never commit):
#   KEOS_SSH_HOST   e.g. ubuntu@1.2.3.4
#   KEOS_SSH_KEY    e.g. ~/.ssh/bill-book-key.pem
# Optional:
#   KEOS_REMOTE_DIR  default /opt/kes-electrical-os
#   KEOS_WEB_ROOT    default /var/www/kes-electrical-os
#   KEOS_PUBLIC_URL  default https://electrical.kamraengineeringsolution.com
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

: "${KEOS_SSH_HOST:?set KEOS_SSH_HOST (user@host)}"
: "${KEOS_SSH_KEY:?set KEOS_SSH_KEY (path to private key)}"
REMOTE_DIR="${KEOS_REMOTE_DIR:-/opt/kes-electrical-os}"
WEB_ROOT="${KEOS_WEB_ROOT:-/var/www/kes-electrical-os}"
PUBLIC_URL="${KEOS_PUBLIC_URL:-https://electrical.kamraengineeringsolution.com}"
SSH=(ssh -i "${KEOS_SSH_KEY}" -o StrictHostKeyChecking=accept-new "${KEOS_SSH_HOST}")

echo "== preflight"
[ -z "$(git status --porcelain)" ] || { echo "working tree is not clean; commit or stash first"; exit 1; }
BRANCH="$(git rev-parse --abbrev-ref HEAD)"
[ "${BRANCH}" = "master" ] || { echo "deploy only from master (on ${BRANCH})"; exit 1; }
git fetch -q origin
SHA="$(git rev-parse HEAD)"
[ "${SHA}" = "$(git rev-parse origin/master)" ] || { echo "HEAD is not pushed to origin/master"; exit 1; }
echo "deploying ${SHA:0:7}"

if [ "${1:-}" != "--skip-gate" ]; then
  echo "== release gate"
  "${ROOT}/scripts/full_regression.sh"
else
  echo "== release gate skipped by flag (frontend build still required)"
  (cd frontend && rm -rf dist && npm run --silent build)
fi
[ -f frontend/dist/index.html ] || { echo "frontend/dist/index.html missing"; exit 1; }

echo "== backend: checkout ${SHA:0:7} on server, install, migrate"
"${SSH[@]}" bash -s <<REMOTE
set -euo pipefail
cd "${REMOTE_DIR}"
git fetch -q origin
git checkout -q --detach "${SHA}"
.venv/bin/pip install -q -e backend
cd backend && ../.venv/bin/alembic upgrade head
REMOTE

echo "== frontend: rsync dist → ${WEB_ROOT}"
rsync -az --delete -e "ssh -i ${KEOS_SSH_KEY}" frontend/dist/ "${KEOS_SSH_HOST}:${WEB_ROOT}/"

echo "== restart backend service"
"${SSH[@]}" "sudo systemctl restart kes-electrical-os && sleep 2 && systemctl is-active kes-electrical-os"

echo "== health (origin, via ssh)"
"${SSH[@]}" "curl -sf http://127.0.0.1:8040/api/v1/version"
echo
echo "== health (public)"
"${ROOT}/scripts/healthcheck.sh" "${PUBLIC_URL}"
echo "deploy ${SHA:0:7}: DONE"
