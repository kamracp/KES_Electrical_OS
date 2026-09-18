# KES Electrical OS — project status

Authoritative status record. Updated at the close of every slice; chat history is never a
source of truth. Read with `AGENTS.md`, `docs/references/electrical-master-reference-register.md`
and `docs/references/reference-gap-register.md`.

Baseline: `master` = `origin/master` at `9b1ac55` (2026-09-17). `scripts/full_regression.sh` PASS end-to-end
(backend ruff format + lint clean repo-wide, 892 tests; frontend typecheck, oxlint, 74 tests, build); GitHub Actions CI green.

## Product direction (decided 2026-09-16)

- **Global scope.** The OS is not limited to Indian projects. Jurisdiction is a project design-basis
  selection (planned profiles: IN, IEC, US, UK, AU-NZ, EU). Engine physics is universal; references,
  precedence, reference ambient conventions, defaults and compliance vocabulary are profile-scoped.
  Tracked as GAP-012; requires Master Prompt v2.1 (§3 boundary) and an ADR.
- **Vendor neutrality.** No manufacturer name appears in engines, contracts, UI, warnings or reports.
  Product data is keyed by product class, specification and rating; vendor identity lives only in
  project-supplied datasheet metadata. Manufacturer literature is a development-time methodology
  cross-check only. Tracked as GAP-009.
- **Single development channel.** All changes follow `AGENTS.md`: one file per commit (type-coupled
  files may share a commit when no green intermediate state exists, stated in the message), validator
  or gate evidence before every commit, exact-path `git add`, push to `master`, verify.

## Phase status (corrects Master Prompt v2.0 §9 where reality differs)

| Phase | Status | Evidence / note |
|---|---|---|
| P0 Governance | Active | Register `6100ce5`; `AGENTS.md` `bfd17b1`; CPWD 2023 verified `6e82126`, `88e30ab`; gap register `4aa4316`; this file. Remaining: ADR-0001 ID reconciliation (GAP-011), jurisdiction ADR (GAP-012), vendor-neutral register row (GAP-009) |
| P1 Backend foundation | Implemented | health/version, async DB, Alembic, pytest |
| P2 Units and standards | CRUD implemented; full registry pending | idempotent reference seed and applicability gate not built |
| P3 Org / RBAC / design basis | Planned | jurisdiction profile now selectable per cable study (`jurisdiction_profile`, default IN); the project-level design-basis field is still to come (GAP-004, GAP-012) |
| P4 Load and demand | Backend/API implemented; UI pending | |
| P5 Sources (Tx/DG/UPS/PV) | Backend/API implemented; UI pending | |
| P6 Network / fault | Backend implemented; **UI is a placeholder** | Prompt v2.0 says "Fault UI implemented" — incorrect. `FaultStudyPage` renders no form; `FaultStudyForm` exists unwired. Engine string `IEC 60909-0:2026` unverified (GAP-007) |
| P7 Protection / relay | Backend foundations | |
| P8 Cable sizing | **First complete vertical slice** | Frontend slice `b7435b8`…`1312b57` (16 Sep), live smoke passed. Derating-not-established warnings `1ec83cb`…`4cddf3e`; smoke: ambient and grouping warnings confirmed in browser; negative case (30 °C, 1 circuit) not yet recorded |
| P9 Panels / IEC 61439 | Foundation | lifecycle incomplete |
| P10–P15 | Planned | no code |
| P16 Hardening / deployment | First release live 17 Sep 2026 (`5ee3188`) | `backend/.env.example`, `deployment/systemd`, `deployment/nginx`, `scripts/{check_backend,check_frontend,full_regression,healthcheck,deploy}.sh`, `Makefile`, `.github/workflows/ci.yml`, `docs/operations/deployment-runbook.md` (`fb74257`..`9b1ac55`). Ruff formatting/lint baselines applied repo-wide. Docker/compose deferred (shared systemd instance; see runbook §6). The `.gitignore` conflict noted earlier did not exist. Port 8040, subdomain electrical.kamraengineeringsolution.com |

## Releases

| Date | Commit | Notes |
|---|---|---|
| 2026-09-18 | `55313ea` | EOS-04 run persistence + §19 layout release: generic `calculation_runs` reused for `SHORT_CIRCUIT` (no migration), `FaultRunService` (shared SHA-256 `content_hash`, values from the JSON-mode result), `POST/GET /api/v1/electrical/fault/runs`; frontend shared `calculationRun.ts` and `runExport.ts`, `createFaultRun`, `useFaultStudy` with run, `FaultResultSummary`, Fault page in §19 layout; backend 931 / frontend 126 tests; via `scripts/deploy.sh`; post-deploy contract probe `POST /fault/runs` with `{}` → HTTP 422 on live (new backend code proven running — restart step confirmed), live bundle names verified with `curl`; live smoke SC-MSB-01 three-phase 415 V (TX-01 R 0.00087 / X 0.00709 Ω) → Calculated with warnings, Ik'' 35.219668322 kA, ip 84.583705423 kA, X/R 8.149, 3 warnings (breaking / steady-state / thermal-equivalent not evaluated), order summary → warnings → traceability → detail, run `a2cb7a31-3f25-4788-8af4-a55b071c0c20` rev 1 `fault-engine 0.1.0`, `SC-MSB-01-rev1.json` downloaded and matches the screen; repeated Calculate with unchanged inputs → revisions 2, 3, … each with the identical content hash `ccd59175…983da` (founder-confirmed in the browser; live smoke 7/7) |
| 2026-09-18 | `a6a5f5e` | Amendment A10 release: shell back control — `BackButton` (browser-history back, Home fallback when the page is the first entry of the session, hidden on Home) rendered once in the shell topbar and styled from design tokens; governance `0ee2eca`, files `6e1c0d6`, `8084577`, `a6a5f5e`; backend 927 / frontend 114 tests; via `scripts/deploy.sh`, restart step `active`, live bundle names verified with `curl`; founder browser check 4/4 (absent on Home, present on Cable, Fault → Cable → Home via Back, direct `/cable-sizing` in a new tab → Home) |
| 2026-09-18 | `40dfe6f` | Item 16b(c) release (EOS-06 Cable complete): §19 study-page layout — collapsible inputs beside a result-first column (summary strip, warnings, traceability panel, detail tables) and "Download run JSON" for the persisted run; files `5bb02e0`, `1c16d2c`, `a722c74`, `35f2aa9`, `01dc4f2`, `40dfe6f`; backend 927 / frontend 109 tests; via `scripts/deploy.sh` (env loaded from `~/.keos-deploy.env`), restart step reported `active`; live smoke CBL-001 with blank factors → Engineering review required, 150 mm², utilization 0.8805, voltage drop 2.0545 % of 5 %, 5 warnings, run JSON downloaded, narrow window stacks results under inputs; founder browser check 6/6 |
| 2026-09-17 | `fdb8023` | Navigation shell release (Slice F) via `scripts/deploy.sh`; gate green |
| 2026-09-17 | `dbbeced` | GAP-013 release: profile-derived cable references via `scripts/deploy.sh`; gate green; US-profile smoke shows pending references and the not-registered warning |
| 2026-09-17 | `d874622` | Fault UI release (EOS-04 Live): hook, warning panel, result panel, page wiring, nav/home status, field-path validation messages via `scripts/deploy.sh`; gate green; live smoke SC-MSB-01 (Ik'' 35.22 kA, kappa 1.698, X/R 8.15) and SC-MSB-03 current-injection 2.5 kA |
| 2026-09-17 | `0dc673d` | GAP-014 release: fault references profile-derived, jurisdiction profile on the fault study via `scripts/deploy.sh`; gate green; live smoke SC-MSB-01 on IN (IEC 60909-0 / 60909-3, Unverified) and US (Reference pending, Not established, not-registered warning), Ik'' 35.22 kA on both |
| 2026-09-17 | `bc22fda` | Fault form release: optional negative-/zero-sequence source impedances; live smoke SC-MSB-02 single-phase-to-earth minimum I_k1 32.915 kA (hand check 32.9 kA), all three sequences available |
| 2026-09-17 | `5a9f97c` | Item 15 (Cable) release: generic `calculation_runs` table (migration `f3a9c2d1e8b7`, single head), `CalculationRunRepository`, `CableRunService` (engine + frozen input/result/warnings/references snapshots + SHA-256), `POST/GET /api/v1/electrical/cable/runs`; backend 927 tests; deploy + explicit restart; live smoke CBL-001 persisted as run `48a782d0-4331-4aa2-bcd0-f24f5016334a` rev 1, `REVIEW_REQUIRED`, 120 mm², 6 warnings; deploy gate caught repo-wide import order (validator lints only the target file) |
| 2026-09-17 | `6568af4` | Slice G release (EOS-06, item 14): derating factors optional — blank factor = not established, per-field `DERATING_FACTOR_NOT_ESTABLISHED` warnings, overall `REVIEW_REQUIRED` (Master Prompt v2.1 §4.10), ampacity `derating_established` + field list on API and panel; backend 924 / frontend 102 tests; via `scripts/deploy.sh` + manual `systemctl restart` (first attempt served old backend until restart — tooling follow-up); live smoke CBL-001 with blank factors → Engineering review required, five named factors, 150 mm² |
| 2026-09-17 | `7efc071` | Item 16a shell release: sidebar lists all fifteen modules from `frontend/src/app/modules.ts` with truthful status, home cards from the same registry, design tokens + IBM Plex Sans, form/table styling (`forms.css`), overflow guard; via `scripts/deploy.sh`; gate green 101 frontend tests; founder browser check confirmed cards, badges and styled Cable form |
| 2026-09-17 | `5ee3188` | First release: https://electrical.kamraengineeringsolution.com — server prep per runbook §1, `scripts/deploy.sh` green (origin + public health), Certbot cert added after the zone SSL mode incident; nginx site recorded at `e47a9c7` |

## Active slice

**EOS-04 Fault complete (item 16b) — in progress.** (a) Run persistence CLOSED `c157522`, `6b25a4b`, `2e8c52f`,
`e5d8750` (generic `calculation_runs`, no migration, runs isolated per module). (b) §19 study-page layout CLOSED
`82bd4d6`, `dd9f31d`, `a2008c4`, `1a40366`, `fff952e`, `55313ea`; (a)+(b) released at `55313ea` with a live contract
probe and smoke SC-MSB-01 7/7. Remaining: (c) Fault UI v2 — multiple sources, branches, decay data, readable
validation messages; the slice plan is written before the first file; (d) close, release, smoke.

**Amendment A10 — shell back control — CLOSED 2026-09-18, released at `a6a5f5e`.** Founder requirement recorded in
the Master Prompt §1A at `0ee2eca`; `BackButton` `6e1c0d6`, shell wiring `8084577`, styles `a6a5f5e`. One control in
the shell topbar on every page except Home: browser-history back, Home fallback when there is no in-app history.
An unsaved-draft warning is deferred until EOS-01 drafts exist. Frontend 114 tests; live smoke 4/4.

**EOS-06 Cable complete (item 16b) — CLOSED 2026-09-18, released at `40dfe6f`.** (a) Slice G derating factors
optional `6568af4`; (b) item 15 Cable run persistence `5a9f97c` (`04b8573`..`ce371f1`; generic `calculation_runs`
for every module); (c) §19 study-page layout `5bb02e0`, `1c16d2c`, `a722c74`, `35f2aa9`, `01dc4f2`, `40dfe6f` —
Calculate persists a run, result summary first, warnings, traceability panel, collapsible inputs, JSON export of
the persisted run; (d) release and live smoke 6/6. Backend 927 / frontend 109 tests.

Follow-ups (not blocking):

- `scripts/deploy.sh` restart: PROVEN on 2026-09-18 — after a real backend change the live contract probe
  (`POST /api/v1/electrical/fault/runs` with `{}` → HTTP 422, not 404) showed the new code running. Make this
  probe a permanent post-deploy step of `deploy.sh` (one new-in-this-release endpoint per release).
- `scripts/deploy.sh` environment: load `~/.keos-deploy.env` itself when present (today a new shell needs
  `set -a; source ~/.keos-deploy.env; set +a` first, otherwise the script exits 1 on `KEOS_SSH_HOST`).
- Form validation messages: show the field label and a readable sentence instead of the raw path — seen twice on
  2026-09-18 (`cable.number_of_loaded_conductors: Too small: expected number to be >=1`,
  `sources.0.name: Too small: expected string to have >=1 characters`); scheduled with Fault UI v2.
- Cable API contract: the engine already computes `governing_criterion`; expose it on the response so the result
  summary can show it.
- Engine version strings (`cable-engine`, `fault-engine`) live in `services/calculation_run.py`; move them onto
  the engines.
- `createCableRun` has no service-level tests (`cable.test.ts` covers only `calculateCableSizing`); copy the six
  `createFaultRun` tests.
- Shared frontend contract schemas: `fault.ts` imports `jurisdictionProfileSchema` and
  `referenceVerificationStatusSchema` from `cableContract`; move them to a module-neutral file.
- Session close: run `git status --short` before ending a session (on 2026-09-17 the 16b(c) page and `study.css`
  never reached the repo and were rebuilt on 2026-09-18).

Founder decisions pending (would amend the Master Prompt, so recorded before any code):

- Idempotent runs (proposed A11): every Calculate creates a new revision even when nothing changed — observed
  live on 2026-09-18 (revisions 1, 2, 3 … with one identical content hash). Proposal: when the new `content_hash`
  equals the latest revision's hash for the same study code, return that run instead of creating a revision; one
  change in the generic run service, for Cable and Fault alike.
- Display precision: the result summary shows exact engine decimals (`35.219668322 kA`). Proposal: a display rule
  of 4 significant figures in summaries and tables, with the exact value kept in the detail, the run and the JSON.

Previously: item 16a shell closed at `7efc071`; Fault UI slice at `bc22fda`; GAP-013 at `a2797ee`; Slice F at `fdb8023`.

## Next slices (in order — Master Prompt v2.1 §15, A9, A10)

1. ~~**EOS-06 Cable complete (16b)**~~ DONE — released `40dfe6f` (2026-09-18).
2. ~~**A10 shell back button**~~ DONE — released `a6a5f5e` (2026-09-18).
3. **EOS-04 Fault complete (16b):** (a) ~~run persistence~~ DONE `e5d8750`; (b) ~~§19 layout~~ DONE, released
   `55313ea`; (c) Fault UI v2 (multiple sources, branches, decay data, readable validation messages); (d) close.
4. **EOS-01 project spine (item 17):** organization/site/project/revision, profile on project, runs linked.
5. Then EOS-02, EOS-03, EOS-05, EOS-07, EOS-08 … in §9 order; item 18 docs batch and item 19 §22 gate review
   (user manual = gate 17) scheduled between modules when a gate or reference row blocks the next module.

## Blocked / waiting

- GAP-001 CPWD Part I Ch 18 table mapping: waits for reference data layer design and independent review.
- GAP-005/006/007 IEC edition resolution: waits for licence or controlled-copy evidence.

## Environment facts

- Repo `~/projects/KES_Electrical_OS` (WSL Ubuntu-24.04). Backend venv `.venv` (hidden); validator
  venv `venv`. Backend dev port 8012 (port 8000 belongs to another product). Vite dev 5173 proxies `/api`.
- Controlled reference copies outside the repo: `~/projects/KES_Electrical_OS_refs/` (checksums in the register).
