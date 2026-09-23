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
| P3 Org / RBAC / design basis | **Identity and access live** (EOS-01 a, 2026-09-20, `202a2ed`): organizations, users, roles OWNER / ENGINEER / VIEWER, server-side sessions, every engineering route behind sign-in; project spine (EOS-01 b) planned | jurisdiction profile now selectable per cable study (`jurisdiction_profile`, default IN); the project-level design-basis field is still to come (GAP-004, GAP-012) |
| P4 Load and demand | Backend/API implemented; UI pending | |
| P5 Sources (Tx/DG/UPS/PV) | Backend/API implemented; UI pending | |
| P6 Network / fault | **Second complete vertical slice** (EOS-04 Fault complete, 2026-09-19); SLD network UI not built | Fault study page with run persistence and the §19 layout `55313ea`, idempotent runs `0c78311`, Fault UI v2 (buses, sources, branches) with display rule A12 and readable validation messages `513c04c`, layout fix `1dda748`. Live smoke: SC-MSB-01 35.22 kA unchanged; two-bus SC-NET-01 12.52 kA at DB-01 against a hand check of 12.5197 kA. Declared limitation: symmetrical breaking, steady-state and thermal-equivalent currents are not evaluated (decay data blocked on REF-IEC-60909-0). |
| P7 Protection / relay | Backend foundations | |
| P8 Cable sizing | **First complete vertical slice** | Frontend slice `b7435b8`…`1312b57` (16 Sep), live smoke passed. Derating-not-established warnings `1ec83cb`…`4cddf3e`; smoke: ambient and grouping warnings confirmed in browser; negative case (30 °C, 1 circuit) not yet recorded |
| P9 Panels / IEC 61439 | Foundation | lifecycle incomplete |
| P10–P15 | Planned | no code |
| P16 Hardening / deployment | First release live 17 Sep 2026 (`5ee3188`) | `backend/.env.example`, `deployment/systemd`, `deployment/nginx`, `scripts/{check_backend,check_frontend,full_regression,healthcheck,deploy}.sh`, `Makefile`, `.github/workflows/ci.yml`, `docs/operations/deployment-runbook.md` (`fb74257`..`9b1ac55`). Ruff formatting/lint baselines applied repo-wide. Docker/compose deferred (shared systemd instance; see runbook §6). The `.gitignore` conflict noted earlier did not exist. Port 8040, subdomain electrical.kamraengineeringsolution.com |

## Releases

| Date | Commit | Notes |
|---|---|---|
| 2026-09-20 | `202a2ed` | EOS-01 (a) identity and access release (amendment A13; 23 commits `5eebdaf`..`202a2ed`): server-side sessions in an HttpOnly, Secure, SameSite=Strict cookie, argon2id passwords, organizations / users / memberships with OWNER / ENGINEER / VIEWER, lockout and audit trail, one protected router (every engineering route needs a session), owner bootstrap command, names on records from the session; frontend sign-in, change-password, route guards, topbar user, re-check of the session on HTTP 401 / 403, Users page for the owner. Backend 1079 / frontend 365 tests. **Released on the self-check, not independently reviewed (founder decision 2026-09-20)**: `docs/security/eos-01a-identity-access-review.md`. Server backup before the migration: `~/backups/kes_electrical_os-20260920-130958-before-eos01a.sql.gz` (7701 bytes, 5 tables, alembic `f3a9c2d1e8b7` inside); migration `f3a9c2d1e8b7` -> `a7d3e9b1c5f2`, 10 tables after; `deploy 202a2ed: DONE`, service `active`, healthcheck PASS, live bundle `index-DObQ5mZL.js` equal to the build. Owner created with `create_owner` on the server (organization `KES`; exactly one organization). Live proof: `/api/v1/units` answered 307 without a session before the release and answers 401 after it, as do `/auth/me`, `/users`, the Cable and Fault run routes and `POST /electrical/cable/calculate`; `/health` stays 200. Live smoke 7/7: redirect to the sign-in page, wrong-password message (audit trail `wrong password, attempt 1`), return to Cable sizing after sign-in, cookie `__Host-keos_session` with HttpOnly, Secure, SameSite=Strict, Path=/ and no Domain, CBL-001 run shown as `Calculated ... by <owner name> (<e-mail>)`, Users page and audit trail with the real client address, sign-out. Review checks at the release: `/docs`, `/redoc`, `/openapi.json` return the frontend `index.html` (F3); `pip-audit` no known vulnerabilities (the project package itself is not on PyPI and is skipped), `npm audit --omit=dev` 0; the page carries none of the security headers while the API carries three (F5 confirmed, fix is the first follow-up) |
| 2026-09-19 | `1dda748` | Fault form layout release: in `forms.css` a row fieldset inside a fieldset spans the full grid width and Add / Remove buttons sit on their own line at normal size (they had stretched into a full-height grid cell beside the row; a double click on Add branch had left an empty Branch 2 during the `513c04c` smoke). `deploy 1dda748: DONE`, live bundle `index-CeOJ5BtP.js` and `index-DHeKf3XJ.css` equal to the build (the CSS name changed from `index-D3o-VUix.css`). Live check 2026-09-19 (founder, screenshot; the first look showed the old layout from the browser cache): Add bus / Add source / Add branch are normal buttons under the rows, row fields spread into two columns, representation hint and empty-branches note in place. Frontend 235 tests. Closes EOS-04 Fault complete (16b). |
| 2026-09-18 | `513c04c` | EOS-04 (c1) Fault UI v2 and amendment A12 release (14 commits `50a2f7f`..`513c04c`, frontend only): shared `formatQuantity` - four significant figures with the exact engine decimal in the tooltip - in the Cable and Fault summaries and tables (A12); readable validation messages (`describeValidationIssue`, form label maps) in both forms; Fault form rebuilt on a draft model with bus / source / branch rows (stable row ids, Add / Remove, Fault at bus, Connected bus, In service, representation hint, same-bus warning); new Fault contract test mirroring the six backend enums; decimal message in field language. Frontend 235 tests / 30 files (was 126). `deploy 513c04c: DONE`, live bundle `index-8pgvQcAI.js` equal to the build. Live smoke 2026-09-19 (founder, browser) 6/6: SC-MSB-01 unchanged (35.22 kA, 84.58 kA, X/R 8.149, tooltip 35.219668322 kA); two-bus SC-NET-01 (TX-01 0.00087 + j0.00709 on MSB-01, cable CBL-01 0.0124 + j0.0080 to DB-01, c 1.05, fault at DB-01): Ik″ 12.52 kA against the hand check c·Un/(√3·Zk) = 12.5197 kA with Zk = 0.0200948 Ω, ip 19.30 kA (κ 1.090), X/R 1.137, sequence 0.01327 + j0.01509, path CBL-01, TX-01, three not-evaluated warnings; `Source 1 — Source name is required.` and, unplanned, `Branch 2 — Branch code is required.`; empty Cable form: `Study code is required.` |
| 2026-09-18 | `0c78311` | Amendment A11 release: idempotent runs — shared `reusable_run()` in the generic run service returns the latest revision when content hash and engine version are unchanged; Cable and Fault `create()` reuse it, the run APIs answer 200 instead of 201; governance `ca87d0b`, code `0c78311`; backend 933 / frontend 126 tests; via `scripts/deploy.sh`, restart `active`; live proof on SC-MSB-01 (founder, browser): three Calculates with unchanged inputs → the same run `3750ff34-010c-43d9-96d9-34a431204046`, revision 13, hash `dc9584fe…ff890c` each time; X changed 0.00709 → 0.00710 → new run `ce34e333-0d89-4fd3-9f2d-609ace02b263`, revision 14 (behaviour exists only in `0c78311`, so it also proves the restart); the 12 earlier revisions stay — runs are never deleted |
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

**EOS-03a Transformer — in progress (A16).** Founder decision 2026-09-23: EOS-03 code work starts before the EOS-02 release (founder travelling, no server access); the deviation from the A9 one-module-at-a-time order is accepted by the founder; EOS-03 commits touch only EOS-03 files; release order stays EOS-02 first (with the EOS-01 (b) smoke), then the EOS-03 parts. Inspection at `c25ae0e`: four source engines exist under `backend/app/domain/electrical/sources/` (transformer, DG, UPS, PV; ~4,861 lines, ~208 domain tests), Decimal-strict and float-rejecting, but with silent invented defaults (`design_margin_factor` 1.10 and 1.20, `ups_efficiency` 0.94, PV 0.97 / 0.98, UPS runtime 30 min), unreferenced warning limits (90 / 40, 90 / 25, 1.25, 1.40 / 0.90), three different status vocabularies, no jurisdiction profile, no run persistence, no project link and no frontend; UPS and PV have no API route at all. Standard ratings already come from the request. `ht_panel_*` (KESE-S2-M9) and LT PCC live in the same area but belong to other modules and are not touched here. Plan (14 commits): 1 this entry + A16 + GAP-016; 2 transformer domain (A16 a/c/d); 3 schemas (optional factors, jurisdiction profile); 4 migration (`calculation_type` `TRANSFORMER_SIZING`); 5 `TransformerRunService` (A11, project scope); 6 `/electrical/transformer-sizing/runs` API; 7 frontend services; 8 draft; 9 form; 10 summary + result panels; 11 hook; 12 page + route + registry; 13 release; 14 close. Code complete 2026-09-23 (not released). Plan corrected to 15 commits (the page commit was missing; 12b added): 5 `ff386cb` service, 6 `7853d51` runs API, 7 `35be9c3` services, 8 `172a535` draft, 9 `d429f0d` form, 10 `c14e588` summary, 11 `534526a` panels, 12 `aa3ad58` hook, 12b `c4c7e2f` ratings order rule, 13 `6b418fa` page at `/transformer-sizing`, registry LIVE with a truthful summary. Backend 1308 tests, frontend 655. Release: together with EOS-02 (single release note below); the smoke adds a transformer run (blank margin → `REVIEW_REQUIRED`; demand beyond the schedule → `NO_SOLUTION`). Release note (2026-09-23): `deploy.sh` ships the whole of `master`, so the EOS-02 release will also carry every EOS-03a commit landed by then (both migrations `d2a8b6c4e1f9` and `e3b9d7f5a2c6`). EOS-03 stays BACKEND_ONLY in the registry until its own page commit; the transformer stateless API changes behaviour (no silent 1.10, `REVIEW_REQUIRED` on blank factors) — covered by a transformer API probe in that release's smoke. EOS-03a code commits so far: 2 `6622137`, 3 `53bd683`, 4 `0c9b659`.

**EOS-02 Load and demand — in progress (A15).** Inspection at `feb5934`: backend engine exists (Decimal-strict, pure), stateless `/electrical/load-demand/calculate` and `/calculate-group`, persisted runs in the separate `load_calculation_runs` table under `/electrical/calculation-runs` (no project link, no org scope, identical hash → 409 instead of A11 reuse), blank factors default silently to 1, unreferenced 0.80 limits, no jurisdiction profile, no frontend. Plan (16 commits): 1 register + amendment + GAP-015; 2 domain (not-established factors, `REVIEW_REQUIRED`, limits removed, profile); 3 schemas (profile, optional factors, `project_revision_id`); 4 model + migration (`calculation_type` `LOAD_DEMAND`); 5 `LoadRunService` (A11, project scope, engine version); 6 `/electrical/load-demand/runs` API + route-protection test; 7 retire old `/electrical/calculation-runs` routes after a live row-count check (table kept); 8 `services/loadDemand.ts` + contract test; 9 `loadStudyDraft.ts`; 10 `LoadRow`; 11 `LoadStudyForm`; 12 `LoadResultSummary` (A12); 13 `LoadResultPanel`; 14 page + route + registry LIVE; 15 release with DB backup + live smoke; 16 close. Commit 7 (retire `/electrical/calculation-runs`) moved to just before the release — it needs a live row-count check of `load_calculation_runs` on the server first; frontend commits 8–14 go ahead. Backend done: 2 `33e9ef9`, 3 `5ee6075`, 4 `0695e83` (migration `d2a8b6c4e1f9`), 5 `3025eb5`, 6 `2a25a8b`. Code complete 2026-09-23 (not released). Frontend: 8 `f82ab8c` services, 9 `78f0283` draft, 10 `cbcc405` LoadRow, 11 `7f9f59f` form, 12 `b79eaef` summary, 13 `4bf9e53` warnings + result panel, 14a `2128109` hook, 14b `d8112a7` page at `/load-demand`, registry LIVE. Backend 1231 tests, frontend 541. Release order (founder back ~2026-09-25): live row count of `load_calculation_runs` → commit 7 retire old `/electrical/calculation-runs` routes (keep read access if rows exist) → commit 15 backup + deploy + migration `d2a8b6c4e1f9` + live smoke of EOS-01 (b) and EOS-02 together → commit 16 close both.

**EOS-01 (b) Project spine — in progress (A13 order, A14 decisions).** Started 2026-09-22 after reading the run models, the identity models, the run repositories and services and the shell. Facts: `calculation_runs` has no project link and a unique key (`module_code`, `calculation_key`, `revision_number`); `organizations` exists from (a); `load_calculation_runs` is a separate older table and stays unlinked (follow-up). Design: `sites` (unique code per organization) → `projects` (organization + site, unique code per organization, client, jurisdiction profile, ACTIVE/ARCHIVED) → `project_revisions` (revision number per project, label, OPEN/ISSUED/SUPERSEDED, exactly one OPEN per project); nullable `calculation_runs.project_revision_id` with two partial unique indexes (unassigned runs keep the old key, project runs are scoped by revision); run requests take an optional `project_revision_id` checked against the caller's organization and the OPEN state; writes by OWNER/ENGINEER, archive and issue by OWNER, reads by every member; topbar project selector (selection in sessionStorage), `/projects` page, Cable and Fault forms send the selected revision and the result shows project and revision, EOS-01 becomes LIVE in the module registry. First live schema change → database backup before the release. Plan, 16 commits: (1) this entry + A14; (2) project models; (3) migration with local Alembic proof; (4) repositories; (5) project service; (6) schemas; (7) `/projects` API with role tests; (8) run repository and service project-scoped, request field and checks; (9) run responses carry project and revision; (10) frontend project service; (11) project provider; (12) topbar selector; (13) projects page, route, registry LIVE; (14) Cable and Fault forms and result panels; (15) release with backup and live smoke; (16) close. Live smoke DEFERRED by founder decision 2026-09-23 — EOS-01 (b) stays RELEASED, NOT CLOSED; the 15b register close waits for the smoke. EOS-02 Load and demand — in progress (inspection done at `feb5934`).

**F5 nginx security headers — CLOSED 2026-09-22 (follow-up of the EOS-01 (a) security review, finding F5).** Evidence 2026-09-22 before the change: `curl -sI` on `/` shows no `Strict-Transport-Security`, `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy` or `Content-Security-Policy`; `/api/v1/health` carries the three baseline headers. The server file equals the repository file (comments aside), so the cause is the nginx `add_header` inheritance rule: `location /` and `location /assets/` each set `Cache-Control` and therefore drop every server-level header. Sources the built frontend loads: only `fonts.googleapis.com` (stylesheet) and `fonts.gstatic.com` (font files); no inline styles or scripts in `src/` or the built `index.html`. Plan, 5 commits: (1) this entry; (2) snippet `deployment/nginx/snippets/kes-security-headers.conf` (HSTS one year, nosniff, `X-Frame-Options DENY`, `Referrer-Policy strict-origin-when-cross-origin`, `Permissions-Policy`, `Cross-Origin-Opener-Policy same-origin`, strict `Content-Security-Policy` with `frame-ancestors 'none'`) included at server level and inside every location that sets a header; (3) `scripts/deploy_nginx.sh` — copies the site file and the snippet to the server, `nginx -t`, reload, `curl -sI` proof; (4) deployment runbook section; then apply on the server; (5) review doc F5 DONE and this register close with the after-headers.

Closed 2026-09-22. Commits: `1350dee` (entry), `1c12c75` (snippet + site file), `0ce79e4` (`deploy_nginx.sh`), `1230c1c` (runbook), `ca2a9c0` (outside the plan: the first live run showed the browser blocking `static.cloudflareinsights.com/beacon.min.js` — Cloudflare Web Analytics is on for the zone with automatic setup, which injects the beacon into every HTML answer of every proxied hostname; founder decision B: keep analytics, allow the beacon in `script-src` and `connect-src`), this entry. Applied with `scripts/deploy_nginx.sh` twice (exit 0, `nginx -t` ok, backup stamps 20260922-…, last 20260922-103147). After: `PASS /: all 7 headers present`, `PASS /api/v1/health: all 7 headers present`; fault study runs with a clean browser console. Next: EOS-01 (b) project spine.

**EOS-01 (a) Identity and access — CLOSED 2026-09-20, released at `202a2ed` (A13).** Slice plan decided 2026-09-19 after reading the backend and
frontend structure. Design: server-side sessions - a random token in an HttpOnly, Secure, SameSite=Strict cookie,
only its SHA-256 in the database, no JWT and no token in browser storage; argon2id password hashes (`argon2-cffi`,
the only new dependency); organizations, users and memberships with the roles OWNER / ENGINEER / VIEWER; no public
sign-up - the first owner is created by a server-side command that prompts for the password, the owner creates
the other users; lockout for 15 minutes after 5 failed logins and one message for an unknown e-mail and a wrong
password; auth event records; one protected router so that every engineering route needs a session (health and
version stay public) with a test that enumerates the routes against an allow-list; the existing API tests keep
running through an authenticated default test client; `calculated_by` comes from the session user. Finding: every
route is public today, including the write routes of the units and standards registries. Plan, 22 commits, backend
first: (1) this entry; (2) password and token helpers; (3) identity models; (4) migration; (5) settings;
(6) repositories; (7) auth service; (8) schemas; (9) auth API and `require_user`; (10) protected router and the
allow-list test; (11) user administration, owner only; (12) `create_owner` command and runbook; (13) `calculated_by`;
frontend (14) auth service; (15) auth provider and route guard; (16) login page; (17) topbar user and logout;
(18) 401 handling in the study services; (19) users page and EOS-01 in the module registry; then (20) security
review against a written checklist kept in the repo; (21) release with a database backup, owner creation and live
smoke; (22) close.

Closed 2026-09-20. Commits in plan order: `5eebdaf`, `c9a8cd6`, `1e079e9`, `0800b98`, `8f20869`, `a6c99ce`,
`354660d`, `fa20151`, `d5f70a4`, `eaf3a80`, `e74c18a`, `a35dc52`, `4e51aef` (backend complete, 1063 tests),
`d32d509`, `4157175`, `96839fc`, `0fe2524`, `8b16af5`, `1e5b996` (frontend complete, 365 tests), review `775c996`,
release of `202a2ed`, this entry. Outside the plan: `d552ce1` (home module-card text wraps; the card carried
`data-module-status` and caught `white-space: nowrap` from `shell.css`), `bee2af5` (Users tables left-aligned;
`forms.css` loads after the page styles) and `202a2ed` (review finding F1: the cookie name gets the `__Host-`
prefix whenever the cookie is Secure, derived in `Settings.session_cookie_name`, not typed into the server
`.env`). Deviations from the plan: the module registry was not changed in commit 19 - EOS-01 stays
`BACKEND_ONLY` until the project configuration page of (b) exists, and the Users page is reached from the topbar
(owner only); the fixed company name left the topbar, the organization of the session is shown once. The review
found sixteen points (F1-F16); F1 and F16 (a missing password hash raised instead of answering "no match"; not
reachable live because the column is NOT NULL) were fixed before the release, the others are follow-ups below.
Status of the slice: **self-checked, not independently reviewed**; the independent review stays open work.
Backend 1079 tests (was 933), frontend 365 tests in 41 files (was 235 in 30). F5 nginx security headers DONE 2026-09-22 (`f19a75a`). Next: EOS-01 (b) the project spine.

**EOS-04 Fault complete (item 16b) — CLOSED 2026-09-19, released at `1dda748`.** (a) Run persistence CLOSED `c157522`, `6b25a4b`, `2e8c52f`,
`e5d8750` (generic `calculation_runs`, no migration, runs isolated per module). (b) §19 study-page layout CLOSED
`82bd4d6`, `dd9f31d`, `a2008c4`, `1a40366`, `fff952e`, `55313ea`; (a)+(b) released at `55313ea` with a live contract
probe and smoke SC-MSB-01 7/7. (c) was split on 2026-09-18 after inspecting the API contract and the engine.
(c1) Fault UI v2 — multiple buses, sources and branches (`ShortCircuitStudyRequest` already accepts all three), a
source-representation hint, readable validation messages and the A12 display rule; frontend only; slice plan: 15
commits (this register entry, shared formatter, four result components, validation helper, Cable form, Fault
contract check, bus / source / branch row components, Fault form, page reference case, release). (c2) decay data —
the engine has no decay model (breaking, steady-state and thermal-equivalent currents are returned as None with
not-evaluated warnings) and REF-IEC-60909-0 is UNRESOLVED, so (c2) is blocked (see Blocked / waiting) and does not
hold the EOS-04 close; the three values stay a declared limitation. (c1) CLOSED 2026-09-19 (next paragraph).
Layout fix released at `1dda748` on 2026-09-19 (live check by screenshot); (d) closed with it. Next: EOS-01
(a) identity and access, then (b) the project spine (item 17) - founder decision A13.

**EOS-04 (c1) Fault UI v2 and amendment A12 — CLOSED 2026-09-19, released at `513c04c`.** Fourteen commits
`50a2f7f`..`513c04c`, frontend only: shared `formatQuantity` (four significant figures, exact engine decimal in the
tooltip) in the Cable and Fault summaries and tables; `describeValidationIssue` with form label maps in both forms;
Fault contract test mirroring the six backend enums; Fault form rebuilt on a draft model (`faultStudyDraft.ts`, rows
with stable ids) with `FaultBusRow`, `FaultSourceRow`, `FaultBranchRow`, Add / Remove, Fault at bus and the
representation hint. The plan grew to 16 commits for the draft model and returned to 15 when the page reference case
was dropped (the page test replaces the form by a button); this register entry is commit 15. Frontend 235 tests
(was 126). Live smoke 6/6 on 2026-09-19: SC-MSB-01 unchanged at 35.22 kA; two-bus SC-NET-01 12.52 kA at DB-01
against a hand check of 12.5197 kA.

**Amendment A11 — idempotent runs — CLOSED 2026-09-18, released at `0c78311`.** Founder decision recorded in the
Master Prompt §1A at `ca87d0b` (with A12). A Calculate whose content hash and engine version equal the latest
revision's returns that run (HTTP 200); a new revision (HTTP 201) is created only when the evidence or the engine
changes; comparison is against the latest revision only (A → B → A gives revision 3). Backend 933 tests; live proof
on SC-MSB-01: revision 13 three times, revision 14 after an input change.

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
  `sources.0.name: Too small: expected string to have >=1 characters`); DONE, released `513c04c`.
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

- Reused runs (A11): `calculated_by` and `notes` of a repeated request are ignored because the stored run is returned
  unchanged; revisit with EOS-01 when users and notes become real inputs. `calculated_by`: DONE with EOS-01 (a),
  `4e51aef` - the name comes from the session and a request that sends one is refused; `notes` stays open.
- Fault form: an empty form hides the impedance / current fields until a source representation is chosen and gives
  no hint of that (founder read it as missing fields on 2026-09-18); hint DONE, released `513c04c`.
- GAP-007 text is stale: a search of `backend/app` for the literal `60909-0:2026` finds nothing on 2026-09-18 (it
  went with GAP-014); reword GAP-007 to the remaining work — edition resolution and the engine-string test.
- FIRST - Fault form layout: the Add bus / Add source / Add branch buttons stretch into a full-height grid cell
  beside the row (seen live 2026-09-19; a double click on Add branch left an empty Branch 2); fix in the study
  CSS with its own release before the EOS-04 (d) close. DONE, released `1dda748` (`forms.css`, two rules).
- API 422 errors: `formatApiError` in `cable.ts` and `fault.ts` still prints the raw `loc` path; route it through
  `describeLocation`.
- Fault rows: the six impedance inputs are repeated in the source and branch rows and the bus label one-liner in
  three files; extract the shared pieces.
- `exactDecimalSchema` lives in `faultContract.ts` and Cable imports it from there; move it with the jurisdiction
  schemas to a module-neutral file.
- EOS-01 (b) live smoke — deferred 2026-09-23. Seen so far: SC-MSB-01 run with no open project revision
  selected returned the existing unassigned run (revision 15, 2026-09-18) — A11 reuse confirmed live;
  project-linked run not yet proven live. Resume at: check topbar selection and PRJ-001 revisions, then
  smoke steps 2–8.
- 15c PLANT-1 shown Inactive — NOT A DEFECT (code checked at `c9b99c0`: model default True + `server_default`
  true, `create_site` never sets `is_active`, `tests/api/test_projects_api.py` asserts a new site is active).
  The only path to Inactive is the one-click "Switch off" button in `ProjectsPage.tsx`. Follow-up: ask for
  confirmation before "Switch off".

From the EOS-01 (a) security review (`docs/security/eos-01a-identity-access-review.md`, findings F1-F16):

- ~~FIRST - nginx security headers (F5)~~ DONE 2026-09-22 (`1c12c75`..`f19a75a`, see Active slice): `location /` and `location /assets/` set their own `add_header`, so the
  three server-level headers are dropped there (nginx inheritance rule) and the page carries none; repeat them
  per location (one included snippet), add `Strict-Transport-Security` and `Content-Security-Policy:
  frame-ancestors 'none'`; through the repository file, installed with the commands in its header.
- Independent review of EOS-01 (a): open; section 8 of the review is the slot for it.
- OPERATING RULE until EOS-01 (b) is released (F2): exactly one organization on the live system - runs, the
  audit trail and the reference data are not scoped to an organization yet; (b) must scope runs and events.
- Second OWNER account (F8): there is no e-mail and no self-service reset; one lost password needs server access
  (`create_owner --recover`).
- Sign-in throttling per address (F6): lockout is per account only; a Cloudflare rate-limiting rule for
  `POST /api/v1/auth/login` and a per-address counter before outside users are invited.
- API documentation pages off in production (F3); `TrustedHostMiddleware` or removal of the unused
  `ALLOWED_HOSTS` / `BACKEND_CORS_ORIGINS` settings (F4); ports 80 / 443 of the instance open to Cloudflare only (F7).
- Review check 5: name the test that pins the 422 handler (no submitted values in the answer), or add one.
- `scripts/deploy.sh`: take the database backup itself before `alembic upgrade head` when a release carries a
  migration (done by hand in the release command on 2026-09-20); define a regular backup schedule in the runbook (F15).
- A session that ends while a form is half filled loses the entries (F12): sign in again in place.
- A VIEWER sees the Calculate button and gets the server's refusal (F13): hide or disable write actions by role.
- Later: four-eyes rule with the approvals slice (F14); breached-password check (F11); second factor, OWNER first (F10).
- Module registry: EOS-01 turns LIVE with the project configuration page of (b), not before.

Founder decisions (2026-09-18, recorded in the Master Prompt §1A at `ca87d0b`):

- A11 idempotent runs — DONE, released `0c78311` (see above).
- A12 display precision — 4 significant figures in summaries and tables, exact value kept on the page (tooltip), in
  the run and in the JSON export; one shared formatter for Cable and Fault; DONE, released `513c04c`.

Founder decision (2026-09-19, recorded in the Master Prompt §1A at `989971c`):

- A13 access control before project data - EOS-01 (a) identity and access (organizations, users, roles, login
  with a server-side session, every engineering API behind authentication, independent review before release)
  is built and released before EOS-01 (b) the project spine; until then no organization, site, project or
  client name goes on the live system. Two spine questions stay open for (b): old runs unassigned or moved to a
  sandbox project, and whether a study may still be calculated without a project.

Founder decisions (2026-09-20):

- EOS-01 (a) is released on the self-check. The slice plan asked for an independent review before the release;
  no independent reviewer was available. Reason for not waiting: the live system had no sign-in at all and every
  route, including the write routes of the units and standards registries, was public; this release closes that.
  The status stays "self-checked, not independently reviewed" until section 8 of the review is filled.
- The choice of the production cookie name (review finding F1) was delegated to the implementer: the `__Host-`
  prefix is derived in code whenever the cookie is Secure (`202a2ed`), so no server `.env` is edited by hand.

Previously: item 16a shell closed at `7efc071`; Fault UI slice at `bc22fda`; GAP-013 at `a2797ee`; Slice F at `fdb8023`.

## Next slices (in order — Master Prompt v2.1 §15, A9, A10, A11, A12)

1. ~~**EOS-06 Cable complete (16b)**~~ DONE — released `40dfe6f` (2026-09-18).
2. ~~**A10 shell back button**~~ DONE — released `a6a5f5e` (2026-09-18).
3. ~~**EOS-04 Fault complete (16b)**~~ DONE — released `1dda748` (2026-09-19): (a) ~~run persistence~~ DONE `e5d8750`; (b) ~~§19 layout~~ DONE, released
   `55313ea`; A11 idempotent runs DONE `0c78311`; (c1) ~~Fault UI v2 + A12~~ DONE, released `513c04c` (smoke
   2026-09-19); ~~Add-button layout fix~~ DONE `1dda748`; ~~(d) close~~ DONE. (c2) decay data stays BLOCKED on
   REF-IEC-60909-0.
4. **EOS-01 Project Configuration (order per A13):** (a) ~~identity and access~~ DONE - released `202a2ed`
   (2026-09-20) on the self-check, independent review open; F5 nginx security headers done 2026-09-22;
   (b) project spine (item 17) - site/project/revision, profile on project, runs linked, project
   selector in the topbar.
5. Then EOS-02, EOS-03, EOS-05, EOS-07, EOS-08 … in §9 order; item 18 docs batch and item 19 §22 gate review
   (user manual = gate 17) scheduled between modules when a gate or reference row blocks the next module.

## Blocked / waiting

- GAP-001 CPWD Part I Ch 18 table mapping: waits for reference data layer design and independent review.
- GAP-005/006/007 IEC edition resolution: waits for licence or controlled-copy evidence.
- EOS-04 (c2) decay data (symmetrical breaking, steady-state and thermal-equivalent currents): waits for a
  controlled copy of IEC 60909-0 (REF-IEC-60909-0 UNRESOLVED); then domain model, engine, independent review, API
  and UI, in that order.

## Environment facts

- Repo `~/projects/KES_Electrical_OS` (WSL Ubuntu-24.04). Backend venv `.venv` (hidden); validator
  venv `venv`. Backend dev port 8012 (port 8000 belongs to another product). Vite dev 5173 proxies `/api`.
- Controlled reference copies outside the repo: `~/projects/KES_Electrical_OS_refs/` (checksums in the register).
