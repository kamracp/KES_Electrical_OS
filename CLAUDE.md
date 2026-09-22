# CLAUDE.md — working rules for KES Electrical OS

## What this is
LV electrical design-check SaaS (FastAPI + SQLAlchemy 2 async + Alembic + PostgreSQL; React + Vite + TypeScript).
Live at electrical.kamraengineeringsolution.com. Governance: docs/governance/KES_Electrical_OS_Enterprise_Master_Prompt_v2_1.md.
Status register: docs/project-status.md (Active slice, Releases, Follow-ups). Read both before planning work.

## How work is done
- Work happens in numbered commits of one active slice ("commit N of M"); one concern per commit,
  a file and its test share a commit. Commit message format: `KEOS-<slice>: <what> (commit N of M)`.
- Before any commit run the gate: backend `bash scripts/check_backend.sh` (ruff format --check, ruff check,
  pytest); frontend `bash scripts/check_frontend.sh` if it exists, else `cd frontend && npm test`.
  Never commit with a failing gate. Show the founder the diff and the test count before committing; push after.
- Mirror the style of neighbouring files (repositories, services, schemas, API routers, tests) instead of
  inventing a new pattern. Code and comments in English only.
- Schema changes: change the ORM model, then `cd backend && ../.venv/bin/alembic revision --autogenerate`
  with a given --rev-id, review the file, prove locally with `alembic upgrade head && alembic check &&
  alembic downgrade -1 && alembic upgrade head`. A guard test fails if a model table has no migration.
- Engineering values are exact decimal strings, never binary floats. Product data is vendor-neutral.
  Reference data carries a verification status; never invent standard values.
- Never edit the server by hand. Releases go through scripts/deploy.sh (code, migrations, frontend) and
  scripts/deploy_nginx.sh (nginx). Back up the live database before a release that migrates it.
- Roles: OWNER / ENGINEER / VIEWER per organization; every API route is behind the protected router
  except health, version and auth login/logout. Reference-data writes OWNER only; study writes OWNER/ENGINEER.
- Keep docs/project-status.md truthful: the register entry opens a slice, the close records commits and
  live proof. Do not edit governance docs without the founder's decision.

## Tooling facts
- Python venv: `.venv` at repo root (`.venv/bin/python`, `.venv/bin/ruff`, `.venv/bin/alembic`).
- Local PostgreSQL is used for Alembic proofs; tests use in-memory SQLite (models must be imported in
  backend/tests/conftest.py and backend/migrations/env.py).
- The founder is not a software engineer: explain each new concept the first time, keep steps small,
  ask before destructive actions, never run commands against the live server.
