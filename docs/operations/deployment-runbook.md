# Deployment runbook — KES Electrical OS

Target: single AWS Lightsail instance (Ubuntu) shared with other KES products; nginx + Cloudflare
(zone SSL/TLS mode "Automatic", effectively Full: the origin serves 443 with Let's Encrypt certificates);
PostgreSQL local to the instance. This product uses port **8040**,
subdomain **electrical.kamraengineeringsolution.com**, checkout `/opt/kes-electrical-os`, web root
`/var/www/kes-electrical-os`, systemd unit `kes-electrical-os.service`.

Rules: nothing is edited by hand on the server; changes arrive by `git` (backend) or `rsync`
(frontend build) through `scripts/deploy.sh`. Only commits that are on `origin/master` and have
passed `scripts/full_regression.sh` are deployed.

## 1. One-time server preparation (first release only)

Run over SSH as the service user (`ubuntu` unless the instance differs; then edit the unit file).

```bash
# 1.1 Code checkout and virtualenv
sudo mkdir -p /opt/kes-electrical-os /var/www/kes-electrical-os
sudo chown -R ubuntu:ubuntu /opt/kes-electrical-os /var/www/kes-electrical-os
git clone https://github.com/kamracp/KES_Electrical_OS.git /opt/kes-electrical-os
cd /opt/kes-electrical-os && python3.12 -m venv .venv && .venv/bin/pip install -U pip && .venv/bin/pip install -e backend

# 1.2 Database and role (choose a strong password; it goes only into backend/.env)
sudo -u postgres psql -c "CREATE ROLE keos LOGIN PASSWORD '<password>';"
sudo -u postgres psql -c "CREATE DATABASE kes_electrical_os OWNER keos;"

# 1.3 Environment file (from the template; production values; mode 600)
#   Every key carries the KES_ prefix (settings env_prefix); unprefixed keys are silently ignored
#   and the API would start with development defaults.
cp backend/.env.example backend/.env && chmod 600 backend/.env && nano backend/.env
#   KES_ENVIRONMENT=production, KES_DEBUG=false, KES_DATABASE_URL=postgresql+psycopg://keos:...@127.0.0.1:5432/kes_electrical_os,
#   KES_BACKEND_CORS_ORIGINS=["https://electrical.kamraengineeringsolution.com"],
#   KES_ALLOWED_HOSTS=["electrical.kamraengineeringsolution.com","127.0.0.1"]
# Verify before migrating (must print 127.0.0.1 and production):
#   cd backend && ../.venv/bin/python -c "from app.core.config import settings as s; print(s.DATABASE_URL.split('@')[-1], s.ENVIRONMENT)" && cd ..

# 1.4 Schema
cd backend && ../.venv/bin/alembic upgrade head && cd ..

# 1.5 systemd unit and nginx site
sudo cp deployment/systemd/kes-electrical-os.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now kes-electrical-os
sudo cp deployment/nginx/electrical.kamraengineeringsolution.com.conf /etc/nginx/sites-available/
sudo mkdir -p /etc/nginx/snippets && sudo cp deployment/nginx/snippets/kes-security-headers.conf /etc/nginx/snippets/
sudo ln -sf /etc/nginx/sites-available/electrical.kamraengineeringsolution.com.conf /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
curl -s http://127.0.0.1:8040/api/v1/health

# 1.6 TLS certificate (required: Cloudflare connects to the origin on 443; without it another
#     site's 443 block answers for this host). Adds the 443 block and 80->443 redirect to the site file.
sudo certbot --nginx -d electrical.kamraengineeringsolution.com --redirect
sudo nginx -t && sudo systemctl reload nginx
```

Cloudflare: add an `A` record `electrical` → instance public IP, proxied (orange cloud). **Never change the
zone SSL/TLS mode** — it is shared by every product on this instance; switching it to Flexible on 17 Sep 2026
broke kamraengineeringsolution.com with a redirect loop until it was set back to Automatic.

## 2. Developer machine preparation (once)

```bash
cat > ~/.keos-deploy.env <<'ENV'
export KEOS_SSH_HOST=ubuntu@<instance-ip>
export KEOS_SSH_KEY=~/.ssh/bill-book-key.pem
ENV
chmod 600 ~/.keos-deploy.env
```

## 3. Release procedure (every release)

1. `git status` clean, on `master`, pushed; CI green on GitHub Actions for that commit.
2. `source ~/.keos-deploy.env && scripts/deploy.sh` — runs the full regression, checks out the exact
   commit on the server, installs, runs `alembic upgrade head`, rsyncs the frontend build, restarts
   the service, and checks `/api/v1/version` on the origin and the public URL.
3. Browser smoke: open `https://electrical.kamraengineeringsolution.com/cable-sizing`, run the CBL-001
   reference draft (see `docs/project-status.md`), confirm the result and warnings match the local smoke.
4. Record the deployed commit and date in `docs/project-status.md`.

## 3A. Release with a migration

A release that carries an Alembic migration changes the live database. Take a verified dump
first; it is the only way back if the migration turns out to be wrong.

```bash
set -a; source ~/.keos-deploy.env; set +a
bash scripts/backup_db.sh before-<slice>      # e.g. before-eos01b
source ~/.keos-deploy.env && scripts/deploy.sh
```

1. **Backup.** `scripts/backup_db.sh` reads the database name from the server's own
   `backend/.env` (never a password, never a hard-coded name), writes
   `~/backups/kes-electrical-os-<UTC stamp>[-<label>].dump` in the custom format, reads it back
   with `pg_restore --list`, and only then removes dumps beyond the last ten. It prints the file
   path, the size, the number of tables with data and the Alembic revision the server is on.
   Copy those four values into the release entry in `docs/project-status.md`. A failure at any
   step exits non-zero and leaves no partial file behind.
2. **Deploy.** `scripts/deploy.sh` runs the full regression, checks the commit out on the
   server, installs, runs `alembic upgrade head`, rsyncs the frontend, restarts the service and
   checks the version endpoint.
3. **Smoke.** Sign in and exercise the slice in the browser, then record what was seen in the
   register entry. Confirm the migration with
   `ssh -i $KEOS_SSH_KEY $KEOS_SSH_HOST 'cd /opt/kes-electrical-os/backend && ../.venv/bin/alembic current'`.

### Restoring from a dump

Restoring is written down, not automated: it overwrites live data and must be a decision, not a
script that can run by accident.

```bash
# 1. Prove the dump first, in a scratch database - this touches nothing that is in use.
sudo -u postgres createdb kes_restore_check
sudo -u postgres pg_restore --dbname=kes_restore_check --no-owner ~/backups/<file>.dump
sudo -u postgres psql -d kes_restore_check -c '\dt'
sudo -u postgres dropdb kes_restore_check

# 2. Only then the live database, with the service stopped so nothing writes during the restore.
sudo systemctl stop kes-electrical-os
sudo -u postgres pg_restore --clean --if-exists --no-owner --dbname=kes_electrical_os ~/backups/<file>.dump
sudo systemctl start kes-electrical-os
cd /opt/kes-electrical-os/backend && ../.venv/bin/alembic current
```

After a restore the code on the server is still the newer commit: check the Alembic revision the
dump carried and, if it is older than the code expects, roll the code back as in section 4.

## 4. Rollback

```bash
source ~/.keos-deploy.env
ssh -i $KEOS_SSH_KEY $KEOS_SSH_HOST 'cd /opt/kes-electrical-os && git checkout -q --detach <previous-sha> && .venv/bin/pip install -q -e backend && sudo systemctl restart kes-electrical-os'
```

Frontend: re-run `scripts/deploy.sh --skip-gate` from a local checkout of the previous commit, or keep
the previous `frontend/dist` and rsync it back. Alembic downgrades are not used in production; a
migration that must be reverted is handled by a new forward migration.

## 5. Operations

- Logs: `journalctl -u kes-electrical-os -f`; nginx `/var/log/nginx/kes-electrical-os.*.log`.
- nginx change (site file `deployment/nginx/*.conf` or the security-headers snippet
  `deployment/nginx/snippets/kes-security-headers.conf`): commit and push, then in a fresh shell
  `set -a; source ~/.keos-deploy.env; set +a; bash scripts/deploy_nginx.sh`. The script requires a clean
  tree at `origin/master`, keeps a dated copy of the old site file in `/etc/nginx/backups`, installs both
  files, runs `nginx -t` (a failed test restores the copy), reloads nginx and proves the seven security
  headers on `/` and `/api/v1/health`. `scripts/deploy.sh` never touches nginx. The headers are included
  inside every location that sets a header because nginx does not inherit `add_header` into such a location.
- Health: `scripts/healthcheck.sh https://electrical.kamraengineeringsolution.com`.
- Backups: before a migrating release take one with `bash scripts/backup_db.sh <label>` (section 3A,
  verified dump in `~/backups`, last ten kept). Independently of that, the instance's existing nightly
  PostgreSQL backup job must include `kes_electrical_os` (verify with the backup script's database
  list).
- Port map and shared-instance rules: see the KES server infrastructure notes; never bind 8000
  (belongs to another product) and never restart another product's service during a release.

## 6. Not in this release

Docker/compose files listed in the master prompt (§12) are deferred: the shared instance runs all
products as systemd services and introducing containers for one product would change the operating
model for all. Revisit when the platform moves to a dedicated host.
