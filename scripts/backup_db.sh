#!/usr/bin/env bash
# KES Electrical OS — take a verified dump of the live PostgreSQL database.
#
# Run this before every release that carries a migration; the printed path, size and Alembic
# head belong in the release entry of docs/project-status.md. The dump is written on the
# server, in the custom format pg_restore reads, and is verified before any older dump is
# removed. Restoring is deliberately NOT automated: see "Release with a migration" in
# docs/operations/deployment-runbook.md.
#
# Env (same as scripts/deploy.sh): KEOS_SSH_HOST (user@host), KEOS_SSH_KEY (private key path).
# Optional: KEOS_REMOTE_DIR (default /opt/kes-electrical-os), KEOS_BACKUP_KEEP (default 10).
# Usage: set -a; source ~/.keos-deploy.env; set +a; bash scripts/backup_db.sh [label]
#   label: optional, ends up in the file name, e.g. "before-eos01b".
set -euo pipefail

: "${KEOS_SSH_HOST:?set KEOS_SSH_HOST (user@host)}"
: "${KEOS_SSH_KEY:?set KEOS_SSH_KEY (path to the private key)}"
REMOTE_DIR="${KEOS_REMOTE_DIR:-/opt/kes-electrical-os}"
KEEP="${KEOS_BACKUP_KEEP:-10}"
LABEL="${1:-}"

# The label travels into a file name: keep it to characters that need no quoting.
if [[ -n "${LABEL}" && ! "${LABEL}" =~ ^[A-Za-z0-9._-]+$ ]]; then
  echo "label may use letters, digits, dot, dash or underscore only, for example before-eos01b"
  exit 1
fi

SSH=(ssh -i "${KEOS_SSH_KEY}" -o StrictHostKeyChecking=accept-new "${KEOS_SSH_HOST}")

# There is no git check here on purpose: a backup must be possible at any moment, whatever
# state the working tree is in. What has to hold is that the server can be reached and can
# make a dump at all.
echo "== preflight: server, checkout and PostgreSQL tools"
"${SSH[@]}" bash -s "${REMOTE_DIR}" <<'REMOTE'
set -euo pipefail
REMOTE_DIR="$1"
[[ -d "${REMOTE_DIR}/backend" ]] || { echo "no checkout at ${REMOTE_DIR}"; exit 1; }
[[ -x "${REMOTE_DIR}/.venv/bin/python" ]] || { echo "no virtualenv at ${REMOTE_DIR}/.venv"; exit 1; }
command -v pg_dump >/dev/null || { echo "pg_dump is not installed on the server"; exit 1; }
command -v pg_restore >/dev/null || { echo "pg_restore is not installed on the server"; exit 1; }
sudo -n -u postgres true 2>/dev/null || { echo "cannot run commands as the postgres user"; exit 1; }
echo "preflight OK"
REMOTE

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
echo "== dump ${STAMP} (UTC)"
"${SSH[@]}" bash -s "${REMOTE_DIR}" "${STAMP}" "${LABEL}" "${KEEP}" <<'REMOTE'
set -euo pipefail
REMOTE_DIR="$1"; STAMP="$2"; LABEL="$3"; KEEP="$4"

# The database name comes from the server's own backend/.env, through the settings object the
# service itself uses. Only the name is read; the password never leaves the file.
DB="$(cd "${REMOTE_DIR}/backend" && ../.venv/bin/python - <<'PY'
from urllib.parse import urlsplit

from app.core.config import settings

print(urlsplit(settings.DATABASE_URL).path.lstrip("/"))
PY
)"
if [[ -z "${DB}" ]]; then
  echo "could not read the database name from ${REMOTE_DIR}/backend/.env"
  exit 1
fi

BACKUP_DIR="${HOME}/backups"
mkdir -p "${BACKUP_DIR}"
NAME="kes-electrical-os-${STAMP}"
[[ -n "${LABEL}" ]] && NAME="${NAME}-${LABEL}"
FILE="${BACKUP_DIR}/${NAME}.dump"

echo "database: ${DB}"
if ! sudo -u postgres pg_dump --format=custom "${DB}" > "${FILE}"; then
  echo "pg_dump FAILED; removing the incomplete file"
  rm -f "${FILE}"
  exit 1
fi

# A dump is only a backup once it has been read back. An unreadable or suspiciously small
# file is deleted here rather than trusted on the day it is needed.
SIZE="$(stat -c %s "${FILE}")"
if (( SIZE < 1024 )); then
  echo "the dump is only ${SIZE} bytes; treating it as failed"
  rm -f "${FILE}"
  exit 1
fi
if ! LISTING="$(pg_restore --list "${FILE}")"; then
  echo "pg_restore --list FAILED: the dump cannot be read back"
  rm -f "${FILE}"
  exit 1
fi
TABLES="$(grep -c 'TABLE DATA' <<<"${LISTING}" || true)"

HEAD="$(cd "${REMOTE_DIR}/backend" && ../.venv/bin/alembic current 2>/dev/null | tail -n 1)"

echo "file:    ${FILE}"
echo "size:    ${SIZE} bytes ($(du -h "${FILE}" | cut -f1))"
echo "tables:  ${TABLES} with data"
echo "alembic: ${HEAD:-unknown}"

# Older dumps go only now, after this one has been verified.
REMOVED="$(ls -1t "${BACKUP_DIR}"/kes-electrical-os-*.dump 2>/dev/null | tail -n "+$((KEEP + 1))" || true)"
if [[ -n "${REMOVED}" ]]; then
  echo "removing dumps beyond the last ${KEEP}:"
  while IFS= read -r old; do
    echo "  ${old}"
    rm -f "${old}"
  done <<<"${REMOVED}"
fi

echo "backup ${NAME}: VERIFIED"
REMOTE

echo "backup: DONE — record the file, size and Alembic head in docs/project-status.md"
