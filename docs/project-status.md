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
| 2026-09-17 | `fdb8023` | Navigation shell release (Slice F) via `scripts/deploy.sh`; gate green |
| 2026-09-17 | `dbbeced` | GAP-013 release: profile-derived cable references via `scripts/deploy.sh`; gate green; US-profile smoke shows pending references and the not-registered warning |
| 2026-09-17 | `d874622` | Fault UI release (EOS-04 Live): hook, warning panel, result panel, page wiring, nav/home status, field-path validation messages via `scripts/deploy.sh`; gate green; live smoke SC-MSB-01 (Ik'' 35.22 kA, kappa 1.698, X/R 8.15) and SC-MSB-03 current-injection 2.5 kA |
| 2026-09-17 | `0dc673d` | GAP-014 release: fault references profile-derived, jurisdiction profile on the fault study via `scripts/deploy.sh`; gate green; live smoke SC-MSB-01 on IN (IEC 60909-0 / 60909-3, Unverified) and US (Reference pending, Not established, not-registered warning), Ik'' 35.22 kA on both |
| 2026-09-17 | `bc22fda` | Fault form release: optional negative-/zero-sequence source impedances; live smoke SC-MSB-02 single-phase-to-earth minimum I_k1 32.915 kA (hand check 32.9 kA), all three sequences available |
| 2026-09-17 | `7efc071` | Item 16a shell release: sidebar lists all fifteen modules from `frontend/src/app/modules.ts` with truthful status, home cards from the same registry, design tokens + IBM Plex Sans, form/table styling (`forms.css`), overflow guard; via `scripts/deploy.sh`; gate green 101 frontend tests; founder browser check confirmed cards, badges and styled Cable form |
| 2026-09-17 | `5ee3188` | First release: https://electrical.kamraengineeringsolution.com — server prep per runbook §1, `scripts/deploy.sh` green (origin + public health), Certbot cert added after the zone SSL mode incident; nginx site recorded at `e47a9c7` |

## Active slice

None. **Item 16a (product shell) CLOSED at `7efc071`** (17 Sep), governed by Master Prompt v2.1 §15 execution
order A9: registry `b4da7aa`, tokens `103d8d2`, sidebar/topbar/footer `a23b485`, home cards `e1de68d`,
form/table styling `7efc071`. Frontend 101 tests. Live check by the founder: fifteen modules with status badges,
styled Cable form. Not yet done (belongs to 16b per module): result summary first, traceability panel, collapsible
input sections, export of persisted runs.

Previously: Fault UI slice closed at `bc22fda`; GAP-013 closed at `a2797ee`; navigation shell (Slice F) at `fdb8023`.

## Next slices (in order — Master Prompt v2.1 §15, A9)

1. **EOS-06 Cable complete (16b):** (a) item 14 Slice G — derating factors optional with `REVIEW_REQUIRED`
   (§4.10); (b) item 15 — calculation-run persistence (run ID, engine version, snapshots); (c) §19 study-page
   layout — result summary first, warnings, traceability panel, collapsible inputs, JSON export of a persisted
   run; (d) register/project-status close, release, live smoke.
2. **EOS-04 Fault complete (16b):** run persistence, §19 layout, Fault UI v2 (multiple sources, branches,
   decay data).
3. **EOS-01 project spine (item 17):** organization/site/project/revision, profile on project, runs linked.
4. Then EOS-02, EOS-03, EOS-05, EOS-07, EOS-08 … in §9 order; item 18 docs batch and item 19 §22 gate review
   (user manual = gate 17) scheduled between modules when a gate or reference row blocks the next module.

## Blocked / waiting

- GAP-001 CPWD Part I Ch 18 table mapping: waits for reference data layer design and independent review.
- GAP-005/006/007 IEC edition resolution: waits for licence or controlled-copy evidence.

## Environment facts

- Repo `~/projects/KES_Electrical_OS` (WSL Ubuntu-24.04). Backend venv `.venv` (hidden); validator
  venv `venv`. Backend dev port 8012 (port 8000 belongs to another product). Vite dev 5173 proxies `/api`.
- Controlled reference copies outside the repo: `~/projects/KES_Electrical_OS_refs/` (checksums in the register).
