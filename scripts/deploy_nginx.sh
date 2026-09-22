#!/usr/bin/env bash
# KES Electrical OS — install the nginx site file and the security-headers snippet on the server.
# Nothing is edited by hand on the server: the two files travel from this repository.
# Env (same as scripts/deploy.sh): KEOS_SSH_HOST (user@host), KEOS_SSH_KEY (private key path).
# Usage: set -a; source ~/.keos-deploy.env; set +a; bash scripts/deploy_nginx.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

: "${KEOS_SSH_HOST:?set KEOS_SSH_HOST (user@host)}"
: "${KEOS_SSH_KEY:?set KEOS_SSH_KEY (path to the private key)}"
SITE_URL="${KEOS_SITE_URL:-https://electrical.kamraengineeringsolution.com}"

SITE_NAME="electrical.kamraengineeringsolution.com.conf"
SNIPPET_NAME="kes-security-headers.conf"
SITE_SRC="deployment/nginx/${SITE_NAME}"
SNIPPET_SRC="deployment/nginx/snippets/${SNIPPET_NAME}"
[[ -f "${SITE_SRC}" && -f "${SNIPPET_SRC}" ]] || { echo "missing ${SITE_SRC} or ${SNIPPET_SRC}"; exit 1; }

echo "== preflight: clean tree, master == origin/master"
[[ -z "$(git status --porcelain)" ]] || { echo "working tree not clean"; exit 1; }
git fetch -q origin
[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/master)" ]] || { echo "HEAD != origin/master"; exit 1; }
COMMIT="$(git rev-parse --short HEAD)"

SSH=(ssh -i "${KEOS_SSH_KEY}" -o StrictHostKeyChecking=accept-new "${KEOS_SSH_HOST}")
SCP=(scp -q -i "${KEOS_SSH_KEY}" -o StrictHostKeyChecking=accept-new)

echo "== copy ${COMMIT}: site file and snippet → /tmp on the server"
"${SCP[@]}" "${SITE_SRC}" "${KEOS_SSH_HOST}:/tmp/${SITE_NAME}"
"${SCP[@]}" "${SNIPPET_SRC}" "${KEOS_SSH_HOST}:/tmp/${SNIPPET_NAME}"

echo "== install, test, reload (backup of the old site file kept in /etc/nginx/backups)"
"${SSH[@]}" bash -s "${SITE_NAME}" "${SNIPPET_NAME}" <<'REMOTE'
set -euo pipefail
SITE="$1"; SNIP="$2"
STAMP="$(date +%Y%m%d-%H%M%S)"
sudo mkdir -p /etc/nginx/backups /etc/nginx/snippets
if [[ -f "/etc/nginx/sites-available/${SITE}" ]]; then
  sudo cp "/etc/nginx/sites-available/${SITE}" "/etc/nginx/backups/${SITE}.${STAMP}"
fi
if [[ -f "/etc/nginx/snippets/${SNIP}" ]]; then
  sudo cp "/etc/nginx/snippets/${SNIP}" "/etc/nginx/backups/${SNIP}.${STAMP}"
fi
sudo install -m 644 -o root -g root "/tmp/${SNIP}" "/etc/nginx/snippets/${SNIP}"
sudo install -m 644 -o root -g root "/tmp/${SITE}" "/etc/nginx/sites-available/${SITE}"
[[ -e "/etc/nginx/sites-enabled/${SITE}" ]] || sudo ln -s "/etc/nginx/sites-available/${SITE}" "/etc/nginx/sites-enabled/${SITE}"
if ! sudo nginx -t; then
  echo "nginx -t FAILED — restoring the previous site file"
  [[ -f "/etc/nginx/backups/${SITE}.${STAMP}" ]] && sudo cp "/etc/nginx/backups/${SITE}.${STAMP}" "/etc/nginx/sites-available/${SITE}"
  sudo nginx -t
  exit 1
fi
sudo systemctl reload nginx
rm -f "/tmp/${SITE}" "/tmp/${SNIP}"
echo "nginx reloaded (backup stamp ${STAMP})"
REMOTE

echo "== verify: security headers on ${SITE_URL}"
EXPECTED=(strict-transport-security x-content-type-options x-frame-options referrer-policy permissions-policy cross-origin-opener-policy content-security-policy)
status=0
for path in / /api/v1/health; do
  headers="$(curl -sI "${SITE_URL}${path}" | tr -d '\r' | tr 'A-Z' 'a-z')"
  missing=()
  for h in "${EXPECTED[@]}"; do
    grep -q "^${h}:" <<<"${headers}" || missing+=("${h}")
  done
  if (( ${#missing[@]} == 0 )); then
    echo "PASS ${path}: all ${#EXPECTED[@]} headers present"
  else
    echo "FAIL ${path}: missing ${missing[*]}"; status=1
  fi
done
exit "${status}"
