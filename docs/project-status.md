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
| P16 Hardening / deployment | Utilities complete, first release pending | `backend/.env.example`, `deployment/systemd`, `deployment/nginx`, `scripts/{check_backend,check_frontend,full_regression,healthcheck,deploy}.sh`, `Makefile`, `.github/workflows/ci.yml`, `docs/operations/deployment-runbook.md` (`fb74257`..`9b1ac55`). Ruff formatting/lint baselines applied repo-wide. Docker/compose deferred (shared systemd instance; see runbook §6). The `.gitignore` conflict noted earlier did not exist. Port 8040, subdomain electrical.kamraengineeringsolution.com |

## Active slice

None. Item 12 deployment utilities closed at `9b1ac55`. Next action: first release per
`docs/operations/deployment-runbook.md` §1–§3 (server prep, then `scripts/deploy.sh`).

## Next slices (in order)

1. ~~Slice E — Jurisdiction profile~~ DONE `759ec99`..`59b9e4c` (17 Sep). Follow-up GAP-013: references from profile.
1a. **(was Slice E)** `JurisdictionProfile` enum and profile
   data (reference ambient air/ground, precedence chain, defaults) → `jurisdiction_profile` on the
   cable request (default `IN`) and `reference_verification_status` on responses → cable engine reads
   reference ambient through the profile → tests → frontend zod enum, `<select>` in
   `CableSizingForm`, verification badge in the result panel → smoke.
2. **§15 item 12 — Deployment utilities (P16).** Resolve `.gitignore` vs `deployment/`; then
   `deployment/docker/*`, `compose.*.yaml`, `deployment/env/production.env.example`, root `compose.yaml`,
   `.env.example`, `Makefile`, `scripts/*.sh`, `.github/workflows/*.yml`, `docs/operations/*-runbook.md`.
   Release scope for the first deployment: Cable slice live; deployment complete ≠ EOS-01..15 complete (§22).
3. Fault UI slice on the Cable pattern; navigation shell; CPWD Part IV and Part VII controlled copies
   (GAP-002, GAP-003); IS 3961/1554/7098 register rows (GAP-008).

## Blocked / waiting

- GAP-001 CPWD Part I Ch 18 table mapping: waits for reference data layer design and independent review.
- GAP-005/006/007 IEC edition resolution: waits for licence or controlled-copy evidence.

## Environment facts

- Repo `~/projects/KES_Electrical_OS` (WSL Ubuntu-24.04). Backend venv `.venv` (hidden); validator
  venv `venv`. Backend dev port 8012 (port 8000 belongs to another product). Vite dev 5173 proxies `/api`.
- Controlled reference copies outside the repo: `~/projects/KES_Electrical_OS_refs/` (checksums in the register).
