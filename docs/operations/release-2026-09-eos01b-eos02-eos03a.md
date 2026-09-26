# Release checklist — EOS-01 (b) smoke + EOS-02 Load and demand + EOS-03a Transformer

One combined release (register: A15 / A16 release notes, 2026-09-23): `scripts/deploy.sh` ships the
whole of `master`, so EOS-02 and EOS-03a go live together, and the deferred EOS-01 (b) live smoke is
done in the same session. Procedure follows `docs/operations/deployment-runbook.md` sections 3A and 4.

Rules for this checklist:

- One command per box; paste only what is inside the box. Every box says what the output must show.
- A box whose output does not match: **stop**, copy the output, do not continue to the next step.
- The founder runs every server command. Steps marked *read-only* change nothing on the server.
- Laptop checkout: `/home/chander/projects/KES_Electrical_OS`. Server checkout: `/opt/kes-electrical-os`.
  Live database: `kes_electrical_os` (runbook 1.2; `backend/.env.example`).

Facts this checklist relies on (checked at `4863077`):

| Item | Value |
|---|---|
| Migrations in this release | `d2a8b6c4e1f9` (EOS-02: `calculation_runs` CHECK allows `LOAD_DEMAND`), then `e3b9d7f5a2c6` (EOS-03a: allows `TRANSFORMER_SIZING`). Both only widen one CHECK constraint; no table, column or row changes. |
| Expected live Alembic revision before the release | `c9f5a3b7d2e4` (EOS-01 (b), recorded as released, not closed) |
| New routes | `/api/v1/electrical/load-demand/runs`, `/api/v1/electrical/transformer-sizing/runs` |
| Old routes decided in step b | `/api/v1/electrical/calculation-runs`: writes `POST /`, `POST /{run_id}/submit`, `/approve`, `/reject`; reads `GET /pending-review`, `/history/{calculation_key}`, `/compare`, `/{run_id}` |
| Tests at `4863077` | backend 1308, frontend 661 |

---

## a) Laptop pre-flight

1. Clean tree on `master`:

   ```bash
   cd /home/chander/projects/KES_Electrical_OS && git status -sb
   ```

   Must show exactly `## master...origin/master` and nothing else.

2. HEAD pushed:

   ```bash
   cd /home/chander/projects/KES_Electrical_OS && git fetch -q && git rev-parse --short HEAD origin/master
   ```

   Must print the same hash twice.

3. Backend gate:

   ```bash
   cd /home/chander/projects/KES_Electrical_OS && bash scripts/check_backend.sh > /tmp/gate-backend.log 2>&1; echo "gate exit: $?"; tail -3 /tmp/gate-backend.log
   ```

   Must show `gate exit: 0`, a pytest line `1308 passed` (or more after commit 7) and `backend gate: PASS`.

4. Frontend gate:

   ```bash
   cd /home/chander/projects/KES_Electrical_OS && bash scripts/check_frontend.sh > /tmp/gate.log 2>&1; echo "gate exit: $?"; grep -E "Test Files|Tests |frontend gate" /tmp/gate.log
   ```

   Must show `gate exit: 0`, `Tests  661 passed (661)` (or more after commit 7) and `frontend gate: PASS`.

5. Load the deploy variables into this shell (needed by every server step below):

   ```bash
   set -a; source ~/.keos-deploy.env; set +a; echo "$KEOS_SSH_HOST"
   ```

   Must print `ubuntu@<instance-ip>`, not an empty line.

## b) Server, read-only: what is live, and the old load runs

1. The commit the server is on now (needed for a rollback in step f):

   ```bash
   ssh -i $KEOS_SSH_KEY $KEOS_SSH_HOST 'cd /opt/kes-electrical-os && git rev-parse --short HEAD'
   ```

   Write the hash down here: `PREVIOUS_SHA = ________`.

2. The live Alembic revision:

   ```bash
   ssh -i $KEOS_SSH_KEY $KEOS_SSH_HOST 'cd /opt/kes-electrical-os/backend && ../.venv/bin/alembic current'
   ```

   Must show `c9f5a3b7d2e4 (head)`. Anything else (for example `a7d3e9b1c5f2`, meaning EOS-01 (b) is
   not live yet): **stop** — the release would then run four migrations, which needs a founder decision.

3. Rows in the old load runs table:

   ```bash
   ssh -i $KEOS_SSH_KEY $KEOS_SSH_HOST "sudo -u postgres psql -d kes_electrical_os -tAc 'SELECT count(*) FROM load_calculation_runs;'"
   ```

   Prints one number. Write it down: `LOAD_CALCULATION_RUNS_ROWS = ____`.

   - `0` → EOS-02 commit 7 removes the whole `/electrical/calculation-runs` router (the table stays).
   - more than `0` → commit 7 removes only the four write routes and keeps the four read routes, so
     the stored rows stay readable.

4. EOS-02 commit 7 is made on the laptop (normal commit flow, both gates, push). Then repeat
   steps a1–a4 before step c: the deploy ships the new `HEAD`.

## c) Backup

1. Verified dump (runbook 3A):

   ```bash
   cd /home/chander/projects/KES_Electrical_OS && bash scripts/backup_db.sh before-eos02-eos03a
   ```

   Must end with `backup kes-electrical-os-<stamp>-before-eos02-eos03a: VERIFIED` and `backup: DONE`,
   and show `alembic: c9f5a3b7d2e4 (head)`. Copy four lines into the release entry: `file:`, `size:`,
   `tables:`, `alembic:`. Any non-zero exit: **stop**, no deploy.

2. Prove the dump restores, in a scratch database (touches nothing that is in use; runbook 3A):

   ```bash
   ssh -i $KEOS_SSH_KEY $KEOS_SSH_HOST 'sudo -u postgres createdb kes_restore_check && sudo -u postgres pg_restore --dbname=kes_restore_check --no-owner ~/backups/<file>.dump && sudo -u postgres psql -d kes_restore_check -tAc "SELECT count(*) FROM calculation_runs;"; sudo -u postgres dropdb kes_restore_check'
   ```

   Replace `<file>` with the name from c1. Must print one number (the run count) and no `ERROR`.

## d) Deploy

1. Deploy, output kept in a file:

   ```bash
   cd /home/chander/projects/KES_Electrical_OS && bash scripts/deploy.sh > /tmp/deploy.log 2>&1; echo "deploy exit: $?"
   ```

   Takes several minutes (the full regression runs first). Must show `deploy exit: 0`.

2. What the deploy did:

   ```bash
   grep -E "deploying|Running upgrade|^active|healthcheck|DONE|FAIL" /tmp/deploy.log
   ```

   Must show, in this order:

   - `deploying <HEAD>`
   - `Running upgrade c9f5a3b7d2e4 -> d2a8b6c4e1f9`
   - `Running upgrade d2a8b6c4e1f9 -> e3b9d7f5a2c6`
   - `active`
   - `healthcheck: PASS`
   - `deploy <HEAD>: DONE`

3. Live Alembic revision:

   ```bash
   ssh -i $KEOS_SSH_KEY $KEOS_SSH_HOST 'cd /opt/kes-electrical-os/backend && ../.venv/bin/alembic current'
   ```

   Must show `e3b9d7f5a2c6 (head)`.

4. Live bundle equals the built bundle:

   ```bash
   cd /home/chander/projects/KES_Electrical_OS && ls frontend/dist/assets/ | grep -E '^index-.*\.js$'; curl -s https://electrical.kamraengineeringsolution.com/ | grep -oE 'index-[^"]+\.js'
   ```

   Must print the same `index-<hash>.js` name twice.

5. The new routes answer (new backend code is running; both must refuse without a session):

   ```bash
   for p in load-demand/runs transformer-sizing/runs; do curl -s -o /dev/null -w "$p %{http_code}\n" -X POST https://electrical.kamraengineeringsolution.com/api/v1/electrical/$p; done
   ```

   Must print `load-demand/runs 401` and `transformer-sizing/runs 401`. `404` means the old code
   is still running.

## e) Browser smoke (signed in as the owner)

Open a fresh browser window (the old bundle may be cached) at
`https://electrical.kamraengineeringsolution.com` and sign in. Tick each line; note what differs.

### e1) EOS-01 (b) project spine (resumes the smoke deferred on 2026-09-23)

| # | Action | Must show |
|---|---|---|
| 1 | Topbar `Project` selector | `No project (unassigned runs)` and `PRJ-001 — <name>` with `Rev 1 · Open` |
| 2 | `/projects` → PRJ-001 | Revision table: Rev 1 `Open`; buttons `Use in studies`, `New revision`, `Issue revision`, `Archive project` |
| 3 | Topbar: `No project (unassigned runs)`; Fault study SC-MSB-01 (three-phase 415 V, TX-01 R 0.00087 / X 0.00709 Ω) → Calculate | `No project — this run will be unassigned.` before the run; Ik″ 35.22 kA; Traceability `Project: Unassigned`; A11 reuse: the existing unassigned run comes back (revision 15 on 2026-09-23) |
| 4 | Topbar: PRJ-001 Rev 1; same SC-MSB-01 → Calculate | Before the run `Project PRJ-001 — <name> · Rev 1 (Open)`; Ik″ 35.22 kA; Traceability `Project: PRJ-001 — <name> · Rev 1 (revision 1)`, `Revision 1`; new Run ID |
| 5 | `/projects` → PRJ-001 → `New revision`, Label `Rev 2` → `Open revision` | `Rev 2 is now the open revision of PRJ-001.`; Rev 1 `Superseded`, Rev 2 `Open` |
| 6 | `Use in studies` | `Studies are now saved in PRJ-001.`; topbar shows `Rev 2 · Open` |

Steps e2 and e3 run with PRJ-001 Rev 2 selected. Step e1-7 (issue) comes after e3, because an issued
revision takes no further runs.

### e2) EOS-02 Load and demand — `/load-demand`

Study code `LD-SMOKE-01`, Study name `Release smoke`, Jurisdiction profile India, Coincidence factor `1`.

| Field | Load 1 | Load 2 (`Add load`) |
|---|---|---|
| Load code / name | `L-01` / `Pump motor` | `L-02` / `Battery charger` |
| Quantity | `2` | `1` |
| Rated power (kW) | `30` | `5` |
| Phase system | Three-phase | DC |
| Voltage (V) | `415` | `220` |
| Power factor | `0.85` | disabled (`DC: power factor is 1.`) |
| Power basis | Electrical input | Electrical input |
| Utilization factor | `0.8` | blank |
| Demand factor | `0.9` | blank |

`Calculate load study` → must show:

- Status `Engineering review required`
- Connected power 65.0000 kW, Demand before coincidence 48.2000 kW, Demand power 48.2000 kW,
  Apparent power 55.1365 kVA, Reactive power 26.7730 kvar (screen shows four significant figures;
  the exact value is in the tooltip)
- Loads 2, Factors not established 2 (utilization and demand factor of L-02)
- Traceability: a Run ID, `Revision 1`, `Project: PRJ-001 — <name> · Rev 2 (revision 2)`;
  `Download run JSON` gives `LD-SMOKE-01-rev1.json`
- `Calculate load study` again with nothing changed → the same Run ID (A11 reuse)

(Expected values computed with the local engine at `4863077`.)

### e3) EOS-03a Transformer sizing — `/transformer-sizing`

Study code `TX-SMOKE-01`, Study name `Release smoke`, Jurisdiction India, Demand power (kW) `800`,
Power factor `0.80`, Duty units `1`, Redundancy mode `None (no standby unit)`.

| Case | Factors (growth / margin / ambient / altitude / harmonic) | Unit ratings | Must show |
|---|---|---|---|
| T1 | `1` / `1.20` / `1` / `1` / `1` | `1000`, `1250`, `1600` | `Calculated` (VALID); Required unit rating 1200 kVA; Selected unit rating `1250 kVA`; Loading 96 %; Spare derated capacity 50 kVA; no warnings |
| T2 | as T1, margin **blank** | `1000`, `1250`, `1600` | `Engineering review required`; Required unit rating 1000 kVA (tooltip `1000.0000`); Selected `1000 kVA`; Loading 100 %; warning: design margin not established |
| T3 | as T1 | `500`, `630` | `No standard rating fits` and `No rating in the schedule covers 1200 kVA.`; Selected `—`; shown as a result with a Run ID, not as an error |

Each case: Traceability shows `Project: PRJ-001 — <name> · Rev 2 (revision 2)`.
(Expected values computed with the local engine at `4863077`.)

### e1-7) Issue with confirmation (last)

| # | Action | Must show |
|---|---|---|
| 7a | `/projects` → PRJ-001 → `Issue revision` → **Cancel** | Question `Issue revision 2 of PRJ-001? An issued revision is frozen and cannot be edited or reopened.`; after Cancel nothing changes, Rev 2 stays `Open` |
| 7b | `Issue revision` → **OK** | `Rev 2 of PRJ-001 was issued and is now frozen.`; Rev 2 `Issued` with owner name and time |
| 7c | Topbar | `No open revision — new runs will not be linked to this project.` |

`Archive project` is **not** clicked in this smoke: an archived project cannot be restored.

## f) Rollback

**Triggers** — any one of:

- `deploy exit` not 0, `Running upgrade` missing or followed by an error, service not `active`,
  `healthcheck: FAIL` (step d1–d2);
- `alembic current` not `e3b9d7f5a2c6` after the deploy (d3);
- sign-in fails, or an earlier live result changes: SC-MSB-01 no longer 35.22 kA (e1-3), existing
  runs or projects missing;
- a new module saves nothing or shows numbers different from the tables above in a way that is not a
  display question.

A wrong number in EOS-02 or EOS-03a alone, with everything else fine, is a defect for a follow-up
commit, not a rollback: the two migrations only widen a CHECK constraint.

**Code back to the previous commit** (runbook 4; `PREVIOUS_SHA` from b1). The older code works on the
widened constraint, so no database step is needed for this:

```bash
ssh -i $KEOS_SSH_KEY $KEOS_SSH_HOST 'cd /opt/kes-electrical-os && git checkout -q --detach <PREVIOUS_SHA> && .venv/bin/pip install -q -e backend && sudo systemctl restart kes-electrical-os && systemctl is-active kes-electrical-os'
```

Must print `active`. Frontend: check out `PREVIOUS_SHA` on the laptop and run
`bash scripts/deploy.sh --skip-gate`, then return the laptop to `master`.

**Database restore** only if data was damaged (runbook 3A "Restoring from a dump"; founder decision,
never automatic). It overwrites everything written after the backup, including smoke runs:

```bash
ssh -i $KEOS_SSH_KEY $KEOS_SSH_HOST 'sudo systemctl stop kes-electrical-os && sudo -u postgres pg_restore --clean --if-exists --no-owner --dbname=kes_electrical_os ~/backups/<file>.dump && sudo systemctl start kes-electrical-os && cd /opt/kes-electrical-os/backend && ../.venv/bin/alembic current'
```

Must end with `c9f5a3b7d2e4 (head)`; after a restore the code must also be at `PREVIOUS_SHA` (above).
Alembic downgrades are not used in production (runbook 4).

## g) Close

Register commits after a green smoke (each its own commit):

| Slice | Commit | Hash |
|---|---|---|
| EOS-02 | 7 — retire `/electrical/calculation-runs` (step b) | `________` |
| EOS-02 | 16 — close, release row | `________` |
| EOS-03a | 15 — close, release row | `________` |
| EOS-01 (b) | 15b — close with the live smoke (e1) | `________` |

The release row records: deployed hash, date, backup `file` / `size` / `tables` / `alembic` (c1),
migration `c9f5a3b7d2e4` -> `d2a8b6c4e1f9` -> `e3b9d7f5a2c6`, `deploy <hash>: DONE`, service `active`,
healthcheck PASS, live bundle name (d4), the 401 probe (d5), `LOAD_CALCULATION_RUNS_ROWS` (b3), smoke
results e1–e3 and e1-7, backend and frontend test counts.

Follow-ups to record as DONE in the register:

- Issue revision and Archive project ask for confirmation (`5f1a6d5`), next to 15c Switch off (`f466fcc`).
- `CLAUDE.md`: never run Prettier in this repo (`4863077`).
