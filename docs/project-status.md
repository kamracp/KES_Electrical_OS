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
| 2026-09-17 | `5ee3188` | First release: https://electrical.kamraengineeringsolution.com — server prep per runbook §1, `scripts/deploy.sh` green (origin + public health), Certbot cert added after the zone SSL mode incident; nginx site recorded at `e47a9c7` |

## Active slice

None. GAP-013 closed at `a2797ee` (17 Sep): governing references are profile-derived. `GoverningReferences`
lives on the jurisdiction profile (IN/IEC carry IEC 60364-5-52 / IEC 60287 as UNVERIFIED; UK/EU/US/AU_NZ carry
none). The cable engine resolves references profile-first; request references are optional overrides that must
be given together and are reported as `REQUEST_OVERRIDE` deviations with a `GOVERNING_REFERENCE_OVERRIDDEN`
warning; an unresolved profile without override yields `NOT_ESTABLISHED` and a
`GOVERNING_REFERENCE_NOT_ESTABLISHED` warning. Contract gained `reference_source`; the References panel renders
"Reference pending" for null references. Backend 909 tests, frontend 82 tests. Deployment pending (see Releases).

Navigation shell (Slice F) closed at `fdb8023` (17 Sep); note commits `bd22162` and `169dcd6` carry the same
message (the second is the home-page test).

## Next slices (in order)

1. **Fault UI slice on the Cable pattern** (EOS-04): service/hook/form/result panel/warning panel/page, and
   close GAP-014 (fault `standard_reference` profile-derived; resolve the IEC 60909-0 edition first).
2. **Derating factors optional** — blank ambient/grouping factor must not silently mean 1.0.
3. CPWD Part IV and Part VII controlled copies (GAP-002, GAP-003); IS 3961/1554/7098 register rows (GAP-008);
   ADR for jurisdiction profiles; Master Prompt v2.1 amendment.
4. User manual (only after the first-release product scope above is complete), then announcement.

## Blocked / waiting

- GAP-001 CPWD Part I Ch 18 table mapping: waits for reference data layer design and independent review.
- GAP-005/006/007 IEC edition resolution: waits for licence or controlled-copy evidence.

## Environment facts

- Repo `~/projects/KES_Electrical_OS` (WSL Ubuntu-24.04). Backend venv `.venv` (hidden); validator
  venv `venv`. Backend dev port 8012 (port 8000 belongs to another product). Vite dev 5173 proxies `/api`.
- Controlled reference copies outside the repo: `~/projects/KES_Electrical_OS_refs/` (checksums in the register).
