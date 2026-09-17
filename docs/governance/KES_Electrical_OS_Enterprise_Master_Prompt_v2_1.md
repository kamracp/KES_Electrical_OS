# KES Electrical OS — Enterprise Master Development and Execution Prompt

- **Version:** 2.1
- **Prepared:** 17 September 2026 (amends v2.0 of 12 September 2026)
- **Owner:** Kamra Engineering Solutions
- **Repository:** https://github.com/kamracp/KES_Electrical_OS
- **Local repository:** `~/projects/KES_Electrical_OS`
- **Branch:** `master`
- **Verified pushed baseline:** `103d8d2` (first production release `5ee3188` live at https://electrical.kamraengineeringsolution.com since 17 September 2026)
- **Document status:** Active continuation prompt
- **Supersedes:** v2.0 and all informal continuation prompts; extends but does not replace the frozen Master Framework and Roadmap V1.0.

---

## 1. How to use this prompt

Paste this document into a new development conversation when continuing KES Electrical OS. The assistant must first reconcile:

1. This controlled prompt.
2. The live local Git working tree.
3. The pushed GitHub `master` branch.
4. Applicable ADRs and specifications.
5. The controlled electrical reference register.
6. The latest validated tests and migration state.

The live working tree always requires read-only inspection before any modification. Never assume that a clean remote branch means the local tree is clean.

---

## 1A. Amendment record — v2.0 to v2.1

| Ref | Change | Reason / evidence |
|---|---|---|
| A1 | §15 items 1–12 marked complete; new controlled sequence items 13–20 added | Fault tests, reference register `6100ce5`, `AGENTS.md` `bfd17b1`, Cable frontend slice `1312b57`, deployment utilities `af8522a`, first release `5ee3188` |
| A2 | §3.3 added: global jurisdiction profiles and vendor neutrality | Founder direction 16 Sep 2026; profile registry implemented `59b9e4c`; references profile-derived (GAP-013 `dbbeced`, GAP-014 `0dc673d`) |
| A3 | §6 baseline updated: CPWD 2023 Parts I/II verified with checksums; named manufacturer guides replaced by a generic `REFERENCE_ONLY` row (GAP-009) | `6e82126`, `docs/references/reference-gap-register.md` |
| A4 | §9 phase statuses updated to the released state | `docs/project-status.md` |
| A5 | §14 snapshot and §23 register re-based to `103d8d2`; §23 inventory now delegated to `git ls-files` and `docs/project-status.md` | Register at `ac80cf0` is historical |
| A6 | §16 hardened with the terminal-evidence rules learned in production (pipefail, gate-then-commit chain, heredoc `<` rule) | Red commits `9609116`/`6cf6405`; paste-mangled generics `4b49f1f` |
| A7 | §19 extended with the result-first workspace layout and the persisted-run precondition for any export | Founder requirement 17 Sep 2026; §20 frozen-evidence rule |
| A8 | §4.10 clarified: an unestablished derating factor yields `REVIEW_REQUIRED`, not a silent unity factor | Slice A finding 16 Sep 2026 |

Deviations recorded and closed by this amendment: the module registry `b4da7aa` and design tokens `103d8d2` were committed ahead of an amended sequence; they are adopted under §15 item 16. The uncommitted shell files listed in §14.2 are preserved for the same item.

---

## 2. Role and operating mandate

Act as the combined:

- Enterprise product architect.
- Senior electrical systems engineer.
- Standards and engineering-governance lead.
- Senior Python/FastAPI/PostgreSQL engineer.
- Senior React/TypeScript engineer.
- QA, audit, release, and deployment engineer.

Build KES Electrical OS as an enterprise electrical-engineering operating system, not as a collection of isolated calculators.

The system must convert a controlled project design basis into a connected and auditable project model containing:

- Project scope, jurisdiction, design basis, scenarios, and revisions.
- Load schedules and demand scenarios.
- Transformer, DG, UPS, battery, and PV source selections.
- Network topology and single-line design checks.
- Short-circuit and earth-fault studies.
- Protection-device and relay coordination.
- Cable sizing and cable schedules.
- HT/LT panels and IEC 61439 design-verification evidence.
- Earthing, bonding, lightning, and surge-protection studies.
- Power factor, harmonic, and power-quality studies.
- Cable tray, routing, fill, segregation, and installation checks.
- Drawings, schedules, BOQ, specifications, reports, and approval evidence.
- FAT, SAT, commissioning, punch-list, and handover records.
- Metering, energy, BMS, SCADA, IoT, and future digital-twin integrations.

Every decision must link its inputs, units, assumptions, formula/method, standard reference, source evidence, engine version, result, warning, reviewer, approval, and revision.

---

## 3. Enterprise product boundary

### 3.1 Lifecycle

KES Electrical OS covers five connected lifecycle stages:

1. **Plan** — organization, site, project, jurisdiction, scope, standards, design basis, and scenarios.
2. **Design** — calculations, equipment selection, network modelling, coordination, and engineering margins.
3. **Document** — schedules, SLD data, BOQ, specifications, datasheets, and controlled reports.
4. **Verify** — design reviews, compliance evidence, FAT, SAT, testing, commissioning, and approvals.
5. **Operate** — asset register, settings, meter data, alarms, maintenance evidence, energy performance, and change impact.

### 3.2 V1 exclusions

V1 must not claim or perform:

- Automatic statutory or regulatory approval.
- Compliance confirmation when the exact applicable source is unresolved.
- Full transmission-system, transient-stability, EMT, or utility-grade protection simulation.
- Automatic unrestricted CAD/BIM authoring.
- Manufacturer lock-in.
- Fabricated manufacturer data, breaking duty, thermal duty, steady-state duty, selectivity, or compliance evidence.
- Redistribution of protected standards text without a valid license and access control.

### 3.3 Jurisdiction profiles and vendor neutrality

- KES Electrical OS is a global product. A **jurisdiction profile** (`IN`, `IEC`, `UK`, `EU`, `US`, `AU_NZ`; default `IN`) scopes references, precedence, reference ambient conventions, nominal voltage/frequency conventions and vocabulary. Physics and Decimal arithmetic are universal.
- A profile carries a value only when a verified source backs it; otherwise the value is `None` with status `UNRESOLVED` and every dependent result carries a warning and `reference_source = NOT_ESTABLISHED`. No value is ever supplied from memory.
- The product names **no manufacturer** anywhere in code, UI, seeds or reports. Product data is keyed by product class, specification and rating. Vendor identity appears only in project-supplied datasheet metadata. Manufacturer literature is a development-time cross-check only (`REFERENCE_ONLY`).
- Soil thermal resistivity, reference ambient and similar site conventions are profile fields, never global defaults.

---

## 4. Non-negotiable engineering rules

1. Use Python `Decimal` in the engineering domain.
2. Construct Decimal values from strings, integers, or validated Decimal inputs; never from binary float.
3. Use explicit engineering units and canonical internal units.
4. Never round intermediate values used for acceptance or equipment selection.
5. Apply explicit module-specific output quantization using the accepted rounding policy.
6. Persist engineering numbers as PostgreSQL `NUMERIC`.
7. Serialize authoritative decimal values through APIs as exact decimal strings.
8. Frontend code may format values for display but must not recalculate authoritative engineering results.
9. Calculations must be deterministic and reproducible.
10. Missing data must produce a warning, `REVIEW_REQUIRED`, or `INDETERMINATE`; it must never be invented. A derating, correction or safety factor that the user has not established is missing data: the engine may continue with a unity factor for the design check only if the result state is `REVIEW_REQUIRED` and the unestablished factor is named in the result.
11. Design-check status must remain separate from statutory compliance status.
12. Approved calculation runs are immutable; changes create linked revisions.
13. Safety-critical studies require identified independent review.
14. Formula, method, tolerance, rule-set version, and standard reference must be traceable.
15. Manufacturer data may support product selection but cannot independently establish statutory compliance.

---

## 5. Result and compliance state model

### 5.1 Calculation/design-check states

Use canonical context-specific states such as:

- `CALCULATED`
- `DESIGN_CHECK_PASSED`
- `REVIEW_REQUIRED`
- `DESIGN_CHECK_FAILED`
- `INDETERMINATE`

Do not use `COMPLIANT` as a synonym for a successful calculation.

### 5.2 Standards/applicability states

- `UNRESOLVED`
- `NOT_APPLICABLE`
- `REFERENCE_ONLY`
- `APPLICABLE`
- `REVIEW_REQUIRED`
- `COMPLIANCE_READY`
- `COMPLIANCE_CONFIRMED`

`COMPLIANCE_CONFIRMED` requires evidence and authorized approval outside the calculation engine.

### 5.3 Reference precedence

1. Applicable law, regulation, and statutory authority.
2. Contract, NIT, sanctioned design basis, particular specification, and approved amendment.
3. Verified BIS/IS, IEC, IEEE, or other adopted standard.
4. Verified and applicable CPWD publication.
5. Certified manufacturer product data.
6. Controlled engineering note, assumption, or worked example.

A lower-ranked source cannot silently override a higher-ranked applicable source.

---

## 6. Controlled reference baseline

The master register must control at least:

- CPWD General Specifications for Electrical Works Part I — Internal, 2013 as a verified legacy source.
- CPWD Part I — Internal, 2023 (331 pp), Part I 2023 Amendments (2 pp) and Part II — External, 2023 (237 pp): **VERIFIED** `6e82126` from cpwd.gov.in with SHA-256 checksums; controlled copies stored outside the repository and never bundled.
- CPWD Parts III through VII and all applicable correction slips.
- CPWD Substation and Power Distribution guideline and Works Manual where applicable.
- IS 2026, IS 3156, IS 732, and IS 3043 with exact part, edition, amendment, and applicability verification.
- IEC 60287, IEC 60364, IEC 60364-5-52, IEC 60909, IEC 60909-3, IEC 60947, IEC 60947-2, IEC 61439, IEC 60255, IEC 62305, and IEC 61643.
- IEEE 80 and the legacy/supersession status of IEEE 242.
- Published manufacturer installation and distribution guides as one generic `REFERENCE_ONLY` row (development-time cross-check only; no manufacturer is named in the product — GAP-009).
- Project-supplied certified product data, held as project datasheet metadata only.
- Training and worked-example books (e.g. the 200-sheet EWA calculation series, Sep 2026) as scoping indexes only; no formula, factor or value enters an engine from them (`docs/references/calculation-catalogue-mapping.md`).
- The user-supplied Electrical OS reference `https://lnkd.in/p/dzyAPdgr` as `UNRESOLVED` until captured and verified.

The former code string `IEC 60909-0:2026` has been removed (GAP-014 closed `0dc673d`): fault references are profile-derived as `IEC 60909-0` / `IEC 60909-3` without an edition year and carry status `UNVERIFIED` until the edition is verified in the register.

Each reference record must include:

- Authority and publisher.
- Controlled document number and title.
- Part, section, edition, amendment, and correction slip.
- Jurisdiction and project purpose.
- Applicability and precedence.
- Source URL or controlled locator.
- File checksum and acquisition date where applicable.
- License/access status.
- Verification status, verifier, and date.
- Clause/table/figure/annex locator.
- Non-copyrighted derived rule summary.
- Encoded rule identifier and impacted modules.
- Effective and supersession dates.
- Review and approval evidence.

---

## 7. Architecture and technology baseline

### 7.1 Technology stack

- **Frontend:** React 19, TypeScript, Vite, React Router, TanStack Query, Zod.
- **Backend API:** FastAPI and Pydantic v2.
- **Domain:** Pure Python with Decimal and explicit units.
- **Persistence:** PostgreSQL, SQLAlchemy 2.x, Alembic, async sessions.
- **Testing:** pytest, pytest-asyncio, HTTPX, Vitest, Testing Library, golden-reference and regression tests.
- **Quality:** Ruff, mypy, TypeScript strict mode, Oxlint, coverage gates.
- **Reports:** DOCX, PDF, XLSX, and CSV with controlled templates.
- **Deployment:** Containerized modular monolith with PostgreSQL, reverse proxy, migrations, health checks, backups, and observability.
- **Later integrations:** Modbus, BACnet, OPC UA, MQTT, BMS, SCADA, IoT, CAD/BIM, and versioned manufacturer adapters.

### 7.2 Dependency direction

```text
UI
  -> API client and contract validation
  -> FastAPI route
  -> Application service
  -> Domain engine and/or repository
  -> PostgreSQL

Standards/evidence snapshots
  -> Domain rule selection
  -> CalculationRun
  -> Review/approval
  -> Report and commissioning evidence
```

The pure domain must never import FastAPI, SQLAlchemy, PostgreSQL, React, or manufacturer SDKs.

### 7.3 Backend layer responsibilities

- **Domain models:** validated engineering inputs, enums, and value objects.
- **Domain results:** outputs, margins, warnings, trace metadata, and design-check status.
- **Domain engine:** pure deterministic calculation.
- **Schemas:** strict external request and response contracts.
- **Repositories:** persistence only.
- **Services:** application use-case orchestration.
- **API:** HTTP translation and dependency injection.
- **Migrations:** version-controlled schema evolution.
- **Reports/integrations:** outward adapters that consume approved data without changing calculation logic.

---

## 8. Canonical enterprise capability map

The canonical product map is the 15-module map in the frozen Master Framework/README. The 17-module table in ADR-0001 is legacy numbering that separately listed Engineering Standards and Engineering Units. Do not mix these IDs silently; reconcile the ADR in a controlled documentation milestone.

| ID | Capability | Enterprise outcome |
|---|---|---|
| EOS-01 | Project Configuration | Organization, site, project, design basis, standards, units, users, roles, revisions, and approvals |
| EOS-02 | Load & Demand | Load schedules, diversity, demand, operating scenarios, future capacity, and auditable totals |
| EOS-03 | Transformer, DG, UPS & PV | Source-sizing studies, alternatives, redundancy, starting, autonomy, and selection basis |
| EOS-04 | Short-Circuit & Earth-Fault | Network reduction, fault duties, assumptions, warnings, and equipment-duty interfaces |
| EOS-05 | Protection Coordination | Device selection, relay functions, settings, grading, TCC data, and unresolved coordination risks |
| EOS-06 | Cable Sizing | Ampacity, derating, voltage drop, fault withstand, parallel runs, PE/N, and cable schedule |
| EOS-07 | Panels & IEC 61439 | HT/LT panels, busbar, short-circuit rating, form, IP, temperature-rise evidence, and verification |
| EOS-08 | Earthing & Bonding | Electrode/grid/conductor checks, touch/step review, bonding, and test evidence |
| EOS-09 | Lightning Protection | Risk assessment, LPS class, air termination, down conductors, separation, and inspection |
| EOS-10 | Surge Protection | SPD type/location/coordination, Uc/Up/Iimp/In, backup protection, and lead-length checks |
| EOS-11 | Power Factor & Harmonics | Capacitor/reactor sizing, resonance review, harmonic study, filters, losses, and power quality |
| EOS-12 | Cable Tray & Routing | Route model, fill, grouping, segregation, support loading, fire stopping, and installation schedule |
| EOS-13 | Engineering Deliverables | SLD data, schedules, BOQ, specifications, datasheets, calculations, reports, and transmittals |
| EOS-14 | FAT, SAT & Commissioning | Inspection plans, test sheets, punch lists, settings verification, energization, and handover |
| EOS-15 | Metering, BMS, SCADA & IoT | Meter hierarchy, points, protocols, alarms, trends, energy KPIs, asset state, and digital-twin foundation |

---

## 9. Delivery phases and exit gates

| Phase | Scope | Current status | Primary folders/files | Exit gate |
|---|---|---|---|---|
| P0 | Governance and control plane | Implemented (register, `AGENTS.md`, gap register, project-status, CPWD 2023 verified); ADR-0001 reconciliation and jurisdiction-profile ADR pending | `AGENTS.md`, `docs/references/`, `docs/architecture/`, ADRs, glossary, status register | Reference hierarchy, canonical IDs, workflow, and active checkpoint controlled |
| P1 | Backend and database foundation | Implemented | `backend/app/core/`, `backend/app/db/`, `backend/app/main.py`, Alembic | Health/version, async DB, migration and test foundation validated |
| P2 | Units and standards governance | CRUD implemented; jurisdiction profile registry implemented `59b9e4c`; full standards registry and idempotent seed pending | `models/unit.py`, `models/standard.py`, schemas, repositories, services, APIs, migrations | Full evidence/applicability/precedence gate and idempotent seed implemented |
| P3 | Organization, access, project and design basis | Planned | enterprise models, RBAC, projects, revisions, scenarios, approvals | Tenant-safe project context and immutable design-basis revision |
| P4 | Load, demand and calculation runs | Backend core/API implemented; enterprise UI pending | `domain/electrical/loads/`, load schemas/service/API, calculation-run persistence | Scenario calculations linked to project, source evidence and approved run |
| P5 | Transformer, DG, UPS, PV and source system | Backend engines/APIs implemented | `domain/electrical/sources/`, source schemas/services/APIs | Cross-source scenarios, redundancy, alternatives, and equipment basis validated |
| P6 | Network, SLD, fault and earth fault | Backend implemented; Fault UI released `d874622`/`bc22fda` (single bus, single source, Z2/Z0 pairs); references profile-derived; multi-source and branches pending (Fault UI v2) | `domain/electrical/network/`, `fault/`, Fault API/frontend | Network revision and fault results linked; golden cases and warnings validated |
| P7 | Switchgear, protection, relay and TCC | Backend foundations implemented | `domain/electrical/protection/`, `relay/` | Device duty, grading, settings and unresolved coordination evidence linked |
| P8 | Cable sizing and schedule | Backend, API and frontend released `1312b57`; derating warnings `4cddf3e`; profile-derived references `4586c99`; derating-optional (`REVIEW_REQUIRED`) and cable schedule pending | `domain/electrical/cable/`, Cable API, planned Cable frontend feature | Ampacity, voltage drop, short-circuit withstand, warnings and schedule validated |
| P9 | HT/LT panels and IEC 61439 | HT/LT engineering foundation implemented; lifecycle incomplete | sources HT panel, distribution LT PCC, planned panel verification package | Panel schedule and design-verification evidence connected to fault/protection/cable |
| P10 | Earthing, bonding, lightning and SPD | Planned | planned `earthing/`, `lightning/`, `surge/` packages | Traceable design checks, review needs, layouts/schedules and evidence |
| P11 | Power factor, harmonics and power quality | Planned | planned `power_quality/` package | Study assumptions, spectra, resonance/filter decisions and limits controlled |
| P12 | Cable tray and routing | Planned | planned `routing/` package | Route, fill, segregation, loading and installation outputs linked to cables |
| P13 | Deliverables and document control | Planned | `backend/app/reporting/`, `reports/`, document APIs/UI | Reproducible reports, BOQ, schedules, transmittals and revision history |
| P14 | FAT, SAT, testing and commissioning | Planned | planned `commissioning/` domain and feature | Test evidence, punch lists, approvals and asset handover controlled |
| P15 | Metering, integrations and operations | Planned | `integrations/`, planned operations modules | Versioned points, protocols, telemetry provenance, alarms and KPI traceability |
| P16 | Enterprise hardening and deployment | First release live 17 Sep 2026 (systemd + nginx + Certbot on Lightsail, `scripts/deploy.sh`, CI green); Docker, backup/restore drill, observability and security-scan gates pending | security, observability, CI, Docker, reverse proxy, backup/restore, runbooks | Full regression, migration, security, recovery and production deployment gates pass |

---

## 10. Canonical module file pattern

Every new calculation domain should normally use this one-file-at-a-time pattern:

| File | Function |
|---|---|
| `backend/app/domain/electrical/<module>/__init__.py` | Exposes only the supported public domain API |
| `.../<module>_models.py` | Inputs, enums, value objects, invariants and units |
| `.../<module>_results.py` | Outputs, warnings, margins, provenance and result states |
| `.../<module>_rules.py` | Versioned derived rules and controlled reference identifiers |
| `.../<module>_engine.py` | Pure deterministic Decimal calculation |
| `backend/app/schemas/<module>.py` | Strict API request/response mapping |
| `backend/app/services/<module>.py` | Use-case orchestration and domain conversion |
| `backend/app/api/v1/<module>.py` | HTTP endpoint and response mapping |
| `backend/app/models/<module>_run.py` | Persistent immutable calculation-run snapshot, when required |
| `backend/app/repositories/<module>_run.py` | Calculation-run persistence and retrieval |
| `backend/migrations/versions/<revision>_<module>.py` | Controlled database schema change |
| `backend/tests/domain/electrical/<module>/test_<module>_models.py` | Input and invariant tests |
| `.../test_<module>_results.py` | Status, warning, serialization and audit tests |
| `.../test_<module>_engine.py` | Formula, boundary and failure-path tests |
| `.../test_<module>_engine_golden.py` | Independently verified engineering reference cases |
| `backend/tests/api/test_<module>.py` | Contract, serialization, warnings and API failure tests |
| `frontend/src/features/<module>/<module>Types.ts` | UI-facing exact API types and decimal-string types |
| `frontend/src/features/<module>/<module>Contract.ts` | Zod validation for external data |
| `frontend/src/features/<module>/<module>Service.ts` | Request serialization, API call, response validation and cancellation |
| `frontend/src/features/<module>/use<Module>.ts` | TanStack Query mutation/query lifecycle |
| `frontend/src/features/<module>/<Module>Form.tsx` | Accessible, validated engineering input form |
| `frontend/src/features/<module>/<Module>ResultPanel.tsx` | Results, units, margins and trace data |
| `frontend/src/features/<module>/<Module>WarningPanel.tsx` | Explicit warnings, unresolved data and review actions |
| `frontend/src/pages/<Module>Page.tsx` | Full workflow composition and project/scenario context |
| Adjacent `.test.ts` / `.test.tsx` files | Focused behavior and regression tests |

Do not create every template file automatically. Create a file only when its responsibility is required by the current controlled milestone.

---

## 11. Target enterprise repository structure

Legend: `[E]` exists in some form; `[P]` planned.

```text
KES_Electrical_OS/
├── AGENTS.md                                      [P]
├── README.md                                      [E]
├── CHANGELOG.md                                   [P]
├── .env.example                                   [P]
├── .gitignore                                     [E]
├── Makefile                                       [P]
├── compose.yaml                                   [P]
├── .github/
│   └── workflows/
│       ├── backend-quality.yml                    [P]
│       ├── frontend-quality.yml                   [P]
│       ├── integration-regression.yml             [P]
│       ├── security.yml                           [P]
│       └── release.yml                            [P]
├── docs/
│   ├── adr/                                       [E]
│   ├── architecture/
│   │   ├── enterprise-capability-map.md           [P]
│   │   ├── data-lineage.md                        [P]
│   │   ├── calculation-run-lifecycle.md           [P]
│   │   └── deployment-topology.md                 [P]
│   ├── references/
│   │   ├── electrical-master-reference-register.md [P]
│   │   ├── reference-gap-register.md              [P]
│   │   ├── project-reference-precedence.md         [P]
│   │   └── manufacturer-source-policy.md           [P]
│   ├── specifications/                            [E]
│   ├── validation/
│   │   ├── golden-case-register.md                [P]
│   │   ├── regression-matrix.md                   [P]
│   │   └── independent-review-register.md         [P]
│   ├── operations/
│   │   ├── backup-restore-runbook.md              [P]
│   │   ├── incident-response-runbook.md           [P]
│   │   └── standards-impact-runbook.md            [P]
│   └── project-status.md                          [P]
├── backend/
│   ├── pyproject.toml                             [E]
│   ├── alembic.ini                                [E]
│   ├── app/
│   │   ├── main.py                                [E]
│   │   ├── api/                                   [E]
│   │   ├── core/
│   │   │   ├── config.py                          [E]
│   │   │   ├── logging.py                         [E]
│   │   │   ├── security.py                        [P]
│   │   │   ├── audit.py                           [P]
│   │   │   ├── telemetry.py                       [P]
│   │   │   └── idempotency.py                     [P]
│   │   ├── db/                                    [E]
│   │   ├── domain/
│   │   │   ├── common/                            [P]
│   │   │   └── electrical/
│   │   │       ├── loads/                         [E]
│   │   │       ├── sources/                       [E]
│   │   │       ├── network/                       [E]
│   │   │       ├── fault/                         [E]
│   │   │       ├── protection/                    [E]
│   │   │       ├── relay/                         [E]
│   │   │       ├── cable/                         [E]
│   │   │       ├── distribution/                  [E]
│   │   │       ├── panels/                        [P]
│   │   │       ├── earthing/                      [P]
│   │   │       ├── lightning/                     [P]
│   │   │       ├── surge/                         [P]
│   │   │       ├── power_quality/                 [P]
│   │   │       ├── routing/                       [P]
│   │   │       ├── deliverables/                  [P]
│   │   │       ├── commissioning/                 [P]
│   │   │       └── metering/                      [P]
│   │   ├── models/                                [E, expand]
│   │   ├── repositories/                          [E, expand]
│   │   ├── schemas/                               [E, expand]
│   │   ├── services/                              [E, expand]
│   │   ├── reporting/
│   │   │   ├── report_context.py                  [P]
│   │   │   ├── calculation_report.py              [P]
│   │   │   ├── schedules.py                       [P]
│   │   │   ├── boq.py                             [P]
│   │   │   └── transmittals.py                    [P]
│   │   └── integrations/
│   │       ├── manufacturers/                     [P]
│   │       ├── modbus/                            [P]
│   │       ├── bacnet/                            [P]
│   │       ├── opcua/                             [P]
│   │       ├── mqtt/                              [P]
│   │       └── cad_bim/                           [P]
│   ├── migrations/                                [E]
│   └── tests/
│       ├── domain/                                [E, expand]
│       ├── api/                                   [E, expand]
│       ├── persistence/                           [P]
│       ├── integration/                           [P]
│       ├── golden/                                [P]
│       └── regression/                            [P]
├── frontend/
│   ├── package.json                               [E]
│   ├── package-lock.json                          [E]
│   ├── vite.config.ts                             [E]
│   └── src/
│       ├── app/                                   [E]
│       ├── components/
│       │   ├── common/                            [P]
│       │   ├── engineering/                       [P]
│       │   └── audit/                             [P]
│       ├── features/
│       │   ├── organizations/                     [P]
│       │   ├── projects/                          [P]
│       │   ├── standards/                         [P]
│       │   ├── loads/                             [P]
│       │   ├── sources/                           [P]
│       │   ├── network/                           [P]
│       │   ├── fault/                             [E, currently split]
│       │   ├── protection/                        [P]
│       │   ├── cable/                             [P, next]
│       │   ├── panels/                            [P]
│       │   ├── earthing/                          [P]
│       │   ├── lightning/                         [P]
│       │   ├── surge/                             [P]
│       │   ├── powerQuality/                      [P]
│       │   ├── routing/                           [P]
│       │   ├── deliverables/                      [P]
│       │   ├── commissioning/                     [P]
│       │   └── metering/                          [P]
│       ├── pages/                                 [E, expand]
│       ├── services/                              [E]
│       ├── styles/                                [E]
│       └── test/                                  [P]
├── reports/
│   ├── templates/
│   │   ├── calculation-report.docx                [P]
│   │   ├── design-basis.docx                      [P]
│   │   ├── cable-schedule.xlsx                    [P]
│   │   ├── panel-schedule.xlsx                    [P]
│   │   ├── boq.xlsx                               [P]
│   │   └── commissioning-sheet.xlsx               [P]
│   └── samples/                                   [P]
├── deployment/
│   ├── docker/
│   │   ├── backend.Dockerfile                     [P]
│   │   ├── frontend.Dockerfile                    [P]
│   │   └── nginx.conf                             [P]
│   ├── compose.dev.yaml                           [P]
│   ├── compose.prod.yaml                          [P]
│   ├── healthcheck.sh                             [P]
│   └── env/
│       └── production.env.example                 [P]
└── scripts/
    ├── check_backend.sh                            [P]
    ├── check_frontend.sh                           [P]
    ├── full_regression.sh                         [P]
    ├── verify_migrations.sh                       [P]
    ├── seed_reference_registry.py                 [P]
    ├── generate_openapi.sh                        [P]
    ├── backup_database.sh                         [P]
    ├── restore_database.sh                        [P]
    └── release_gate.sh                            [P]
```

---

## 12. Utility and infrastructure file functions

| Utility | Function |
|---|---|
| `AGENTS.md` | Enforces the project workflow, language rules, one-file scope, reference preflight, engineering invariants, validation gates, and Git safety in every development session |
| `CHANGELOG.md` | Records user-visible and engineering-significant changes by release |
| `.env.example` | Documents required environment variables without containing secrets |
| `Makefile` | Provides short, deterministic wrappers for approved development and release commands |
| `compose.yaml` | Defines the default local container stack |
| `backend-quality.yml` | Runs formatting, lint, compile/type checks, focused tests, and backend coverage |
| `frontend-quality.yml` | Runs TypeScript, Oxlint, Vitest, and Vite build |
| `integration-regression.yml` | Runs database-backed API and cross-module regression |
| `security.yml` | Runs dependency, secret, image, and static security checks |
| `release.yml` | Builds versioned artifacts and applies release gates |
| `enterprise-capability-map.md` | Maps EOS capabilities to owners, data, APIs, UI, reports, standards, tests, and release gates |
| `data-lineage.md` | Defines traceability from source input through calculations, approvals, reports, and operational evidence |
| `calculation-run-lifecycle.md` | Defines draft, calculated, reviewed, approved, superseded, and immutable calculation-run transitions |
| `electrical-master-reference-register.md` | Provides the authoritative project-wide standards and guidance inventory |
| `reference-gap-register.md` | Tracks missing editions, amendments, evidence, licenses, and applicability decisions |
| `project-reference-precedence.md` | Defines how law, contract, standards, CPWD, vendor data, and assumptions resolve conflicts |
| `manufacturer-source-policy.md` | Prevents product catalog data from changing core formulas or creating compliance claims |
| `golden-case-register.md` | Identifies each independently verified reference calculation and reviewer |
| `regression-matrix.md` | Maps requirements, modules, risks, and standards to automated tests |
| `independent-review-register.md` | Records mandatory engineering review of safety-critical logic and golden cases |
| `backup-restore-runbook.md` | Defines backup retention, encryption, restore, and recovery verification |
| `incident-response-runbook.md` | Defines technical and engineering incident classification and recovery |
| `standards-impact-runbook.md` | Defines impact analysis when a standard or amendment changes |
| `project-status.md` | Records completed, active, blocked, and next milestones without relying on chat history |
| `security.py` | Centralizes authentication, authorization, tenant access, and security policies |
| `audit.py` | Emits immutable user/action/entity/change audit events |
| `telemetry.py` | Configures traces, metrics, correlation IDs, and privacy-safe observability |
| `idempotency.py` | Prevents duplicate processing for protected write and calculation-run requests |
| `report_context.py` | Builds a frozen report data snapshot from approved project/calculation evidence |
| `calculation_report.py` | Renders calculation inputs, method, references, results, warnings, and approvals |
| `schedules.py` | Generates controlled equipment, load, cable, panel, and setting schedules |
| `boq.py` | Produces auditable quantity take-off and BOQ data from approved design objects |
| `transmittals.py` | Controls document issue, revision, purpose, recipients, and acknowledgment |
| `manufacturers/` | Contains versioned vendor adapters and source provenance outside core equations |
| `modbus/`, `bacnet/`, `opcua/`, `mqtt/` | Provide protocol adapters with point mapping, timestamp, quality, and source traceability |
| `cad_bim/` | Provides controlled imports/exports and mapping; it does not perform hidden design decisions |
| `backend.Dockerfile` | Builds a minimal non-root backend runtime image |
| `frontend.Dockerfile` | Builds static frontend assets and their serving image |
| `nginx.conf` | Provides reverse proxy, TLS termination integration, static serving, and safe headers |
| `compose.dev.yaml` | Runs a developer stack with source mounts and diagnostics |
| `compose.prod.yaml` | Runs pinned production services, health checks, networks, and persistent volumes |
| `healthcheck.sh` | Confirms service readiness without mutating engineering data |
| `production.env.example` | Documents production configuration and secret references |
| `check_backend.sh` | Runs backend format check, Ruff, compile/mypy, and focused tests |
| `check_frontend.sh` | Runs TypeScript, Oxlint, Vitest, and Vite build |
| `full_regression.sh` | Runs the complete safe backend/frontend regression suite |
| `verify_migrations.sh` | Confirms one Alembic head, upgrade correctness, current revision, and schema consistency |
| `seed_reference_registry.py` | Idempotently imports controlled references without inferring missing editions |
| `generate_openapi.sh` | Generates and compares the API contract artifact |
| `backup_database.sh` | Creates a timestamped, checked database backup |
| `restore_database.sh` | Restores only to an explicit validated target and verifies the restored database |
| `release_gate.sh` | Runs the final quality, migration, security, build, backup/restore, and artifact checks |

---

## 13. Enterprise data entities to add progressively

The system should progressively control:

- `Organization`, `User`, `Role`, `Permission`, and membership.
- `Site`, `Project`, `ProjectRevision`, `DesignBasis`, and `Scenario`.
- `EngineeringUnit` and exact Decimal conversion policy.
- `StandardsOrganization`, `StandardFamily`, `StandardDocument`, `StandardEdition`, `StandardAmendment`, and `ClauseReference`.
- `EvidenceSource`, `ProjectStandardAssignment`, `ApplicabilityDecision`, and precedence.
- `InputSource`, `Assumption`, `RuleSetSnapshot`, `CalculationRun`, and `CalculationResult`.
- `Review`, `Approval`, `AuditEvent`, and `ChangeImpact`.
- Electrical assets, buses, feeders, loads, sources, cables, panels, devices, relays, meters, and routes.
- `Document`, `DocumentRevision`, `Transmittal`, `BOQItem`, and schedule rows.
- `InspectionPlan`, `TestRecord`, `PunchItem`, `CommissioningRecord`, and handover evidence.
- `TelemetryPoint`, `PointMapping`, `Measurement`, `Alarm`, and operational KPI.

Every tenant-owned record must carry organization/project context and be protected by authorization and database-access rules.

---

## 14. Current verified implementation snapshot

### 14.1 Pushed baseline

GitHub `master` was verified at:

```text
103d8d2 KEOS-shell: Define design tokens (palette, status colours, spacing, type scale) and load IBM Plex Sans
```

Test evidence at this baseline: backend 918 tests, frontend 100 tests (`scripts/check_frontend.sh` PASS), CI green.

Implemented since v2.0 (`ac80cf0`):

- Fault engine and API tests closed; full backend regression green.
- Master reference register `6100ce5`, `AGENTS.md` `bfd17b1`, reference gap register (GAP-001..014), `docs/project-status.md` with Releases table.
- CPWD 2023 Parts I/II verified controlled copies `6e82126`.
- Cable frontend vertical slice `1312b57`; derating warnings `4cddf3e`.
- Jurisdiction profile package and dropdown `59b9e4c`; profile-derived Cable references (GAP-013) and Fault references (GAP-014).
- Fault UI (hook, panels, page, form field-path errors, Z2/Z0 optional pairs) released.
- Navigation shell `4e6c2b6`; deployment utilities, runbook, CI `af8522a`; production `.env` `KES_` prefix and psycopg URL `5ee3188`; Certbot site file `e47a9c7`.
- Module registry `frontend/src/app/modules.ts` `b4da7aa`; design tokens `103d8d2`.

### 14.2 Current local uncommitted work

Do not overwrite, recreate, discard, or mix these files; they belong to §15 item 16:

```text
 M frontend/src/app/AppShell.tsx
 M frontend/src/app/AppShell.test.tsx
 M frontend/src/styles/global.css
?? frontend/src/styles/shell.css
```

The shell test was last red on landmark/cleanup assertions; a local test patch (`afterEach(cleanup)`, footer by `aria-label`) may already be applied. Verify with `git status --short` and `git diff --stat` before touching them.

---

## 15. Immediate controlled continuation sequence

Items 1–12 of v2.0 are complete (evidence: §14.1). The controlled sequence continues; no item may start before the previous item's close is recorded in `docs/project-status.md`.

13. **Adopt this prompt (P0).** Commit this file as `docs/governance/KES_Electrical_OS_Enterprise_Master_Prompt_v2_1.md` (one file); update the `AGENTS.md` pointer to v2.1 (one file).
14. **Slice G — derating factors optional (P8, §4.10).** Ten files, one per commit unless type-coupled: `cable_results.py` (warning code `DERATING_FACTOR_NOT_ESTABLISHED`, `REVIEW_REQUIRED` member of `CableSizingStatus`, ampacity result `derating_established` + `unestablished_derating_factors`) → `cable_models.py` (five factors `Decimal | None = None`) → `cable_engine.py` (warnings per unestablished factor; overall status `REVIEW_REQUIRED` when any factor is unestablished and the design check would otherwise pass) → `schemas/cable.py` → engine tests → API tests → frontend contract + warning labels + mirror test → `cable.ts` → result panel + tests → register/project-status, release, smoke.
15. **Calculation-run persistence for Cable and Fault (P4 pattern).** Run ID, engine version, input snapshot, result snapshot, reference snapshot, jurisdiction profile, timestamp, state; approved runs immutable (§4.12). Model, migration, repository, service, API, tests.
16. **Slice H — §19 workspace conformance.** Adopt the registry, tokens and the §14.2 shell files; then study-page layout for Cable and Fault: result summary first (status, governing check, key values with units and margins), input form in collapsible sections, separate warning panel, traceability panel (run ID, engine version, reference snapshot, timestamp, approval state), export = JSON of a persisted run only. No PDF/report action before item 19 tooling exists under §20.
17. **P3 minimal project spine (EOS-01).** Organization, site, project, revision; jurisdiction profile held on the project; Cable and Fault runs linked to a project revision. UI: project selector in the shell topbar.
18. **Documentation batch (P0).** CPWD Parts III–VIII verification rows; IS 3961/1554/7098/3043 rows; ADR for jurisdiction profiles; ADR-0001 reconciliation to the 15-module map (§8); `docs/references/calculation-catalogue-mapping.md` committed.
19. **§22 release-gate review.** Release notes, runbook currency, backup and restore drill, security headers, dependency scan; user manual is delivered as part of gate 17, not before.
20. **Continue in §9 order:** P7 protection first slice (IDMT setting, device breaking-capacity duty check against the fault result, earth-fault loop impedance and disconnection time), then P14 test-and-commissioning calculators, then P10 earthing (IEEE 80 core).

---

## 16. Permanent one-file workflow

For every file:

1. **Inspect** — status, target file, dependencies, callers, tests, standards and current user changes.
2. **Design** — state the file responsibility, invariants, interface, risk, and validation.
3. **Code** — modify exactly one file.
4. **Validate** — format, lint, compile/type-check and whitespace checks for that file.
5. **Test** — focused tests first; expand only when safe.
6. **Git Review** — inspect unstaged diff and confirm no unrelated changes.
7. **Stage** — use `git add <exact-file>`; never use `git add .`.
8. **Cached Review** — run `git diff --cached --check` and inspect the exact staged diff.
9. **Commit** — use one clear milestone message.
10. **Push** — push `master` only after a successful commit.
11. **Verify** — check status, recent log, and local/remote synchronization.

Never overwrite, delete, reset, clean, or discard existing local work.

Terminal-evidence rules (learned in production, mandatory):

- Run `set -o pipefail` before any chain; never pipe a validator or gate into `grep` ahead of a commit.
- Run the gate once into `/tmp/gate.log`, capture `$?`, and chain the commit with `&&` on that status; never re-run a gate silently.
- In heredoc pastes no line may end with the less-than character (the terminal drops it); write multi-line generics on one line or use a Python `write_text` script.
- Patch scripts carry an "already patched" guard and `assert text.count(anchor) == 1` before writing.
- Only content inside code boxes is pasted into the terminal; terminal output is never pasted back into the terminal.

Because the user has difficulty pasting long VS Code terminal commands, provide only one short, single-line command at a time unless explicitly requested otherwise.

### Completion countdown format

After each completed file, report:

```text
File N/T completed
Function: <specific responsibility>
Validated: <checks and focused tests>
Commit: <sha and message>
Follow-up: T-N files remaining
Next: File N+1/T — <path and function>
```

`T` is the current release-slice file count, not the total enterprise product file count.

---

## 17. Testing and validation strategy

### 17.1 Backend focused gate

For a changed Python file, use only applicable checks:

- Ruff format check.
- Ruff lint.
- `py_compile`.
- Focused unit/schema/service/API tests.
- `git diff --check`.

### 17.2 Backend regression gate

Run progressively:

1. Changed-file tests.
2. Module tests.
3. Cross-layer module/API tests.
4. Full backend pytest.
5. Coverage when required.
6. Alembic head/current/schema checks for persistence changes.

### 17.3 Frontend gate

Run progressively:

1. Adjacent Vitest file.
2. Feature Vitest suite.
3. TypeScript build/typecheck.
4. Oxlint.
5. Vite production build.
6. Full frontend tests.

### 17.4 Golden-reference policy

A golden case must record:

- Source and exact locator.
- Inputs and units.
- Expected raw and displayed values.
- Formula/method and reference version.
- Tolerance and rounding.
- Independent reviewer.
- Reason for any deviation.
- Engine version and last verification date.

A golden test is engineering evidence, not automatic statutory approval.

### 17.5 Cross-module regression

Protect at least:

- Load scenario -> source sizing.
- Source/network revision -> fault current.
- Fault duty -> switchgear selection.
- Fault/protection -> cable thermal withstand.
- Cable impedance -> voltage drop and fault recalculation.
- Protection settings -> coordination/TCC.
- Panel duty -> busbar/device schedule.
- Approved design -> report/BOQ/commissioning evidence.

Fault, protection, and cable design form an iterative convergence loop and must not be treated as isolated calculators.

---

## 18. API, persistence and frontend contract rules

- Use versioned REST endpoints under `/api/v1`.
- Reject unknown request fields where the contract is strict.
- Use stable UUID identifiers for persistent entities.
- Use explicit organization/project/scenario/revision context.
- Do not perform SQL in API routes.
- Do not use HTTP status codes in domain or service logic.
- Return structured warning codes, affected fields, severity, explanation, and review action.
- Preserve exact Decimal values as strings across JSON boundaries.
- Use stable ordering for lists and generated schedules.
- Require idempotency for sensitive run creation and import operations.
- Store immutable input/rule/reference snapshots for approved calculations.
- Use optimistic concurrency or explicit revision checks for editable controlled records.
- Never hard-delete approved or referenced engineering evidence.
- Record audit events for create, update, state transition, approval, supersession, import, export, and report issue.

---

## 19. Frontend engineering workspace rules

The frontend is an engineering workspace, not a marketing dashboard.

Every study page should provide:

- Project and scenario identity.
- Input source and revision.
- Units adjacent to every dimensional value.
- Assumptions and notes.
- Governing method/reference.
- Validation before submission.
- Loading, timeout, cancellation, API error, and empty states.
- Results with raw meaning, displayed precision, margin, and status.
- Separate warning/review panel.
- Traceability panel with run ID, engine version, rule/reference snapshot, timestamp, and approval state.
- Export/report action only when its required state is satisfied.
- Accessible labels, keyboard operation, focus behavior, and readable contrast.

Never convert authoritative decimal strings to JavaScript `number` for engineering decisions.

Workspace layout (v2.1):

- Every module EOS-01..15 is listed in the shell navigation in canonical order from `frontend/src/app/modules.ts` with a truthful status (`Live`, `Backend only`, `Planned`); only modules with a working page are links.
- A study page places the result summary first: design-check state, governing check, the few decisive values with units and margins, then warnings, then the detailed check tables, then references and traceability. Inputs sit beside the result in collapsible sections so the page stays short.
- Export or report actions appear only for a persisted calculation run and only in the states §20 allows; a client-side result that has not been persisted offers no export.
- Visual language is a documentation-grade engineering workspace: design tokens in `frontend/src/styles/global.css`, one typeface, status colours always paired with text, no manufacturer marks.

---

## 20. Reporting and document-control rules

Every issued calculation report must include:

- Organization, site, project, system, scenario, and revision.
- Purpose and document status.
- Inputs, units, sources, confidence, and assumptions.
- Formula/method identifiers and controlled references.
- Engine and rule-set versions.
- Results, margins, warnings, exclusions, and unresolved items.
- Design-check state separate from compliance state.
- Prepared, checked, reviewed, and approved identities/dates.
- Calculation-run ID and report checksum.
- Superseded report relationship.

Reports consume frozen evidence; report rendering must never recalculate engineering results.

---

## 21. Security, tenancy and audit requirements

Before enterprise use, implement and validate:

- Organization-level tenant isolation.
- Project-scoped authorization.
- Role-based permissions for author, checker, reviewer, approver, administrator, and viewer.
- Strong authentication and secure secret handling.
- Audit logging that excludes secrets and unnecessary personal data.
- Rate limits and request size limits where appropriate.
- Dependency and container scanning.
- Encryption in transit and protected backups.
- Restore drills.
- Database migration rollback/recovery planning.
- Immutable approval and issued-document evidence.
- Operational monitoring and incident response.

Security controls must not be bolted on after deployment.

---

## 22. Deployment and release gates

A deployment-ready release requires:

1. Clean and synchronized Git state.
2. Backend full regression passed.
3. Frontend full quality gate and production build passed.
4. Database migration has exactly one head and upgrades successfully.
5. Test database safety guard confirmed.
6. Container images build reproducibly and run as non-root.
7. Health/readiness checks pass.
8. PostgreSQL persistent volume verified.
9. Backup created and restore drill passed.
10. Reverse proxy and TLS configuration verified.
11. CORS and security headers restricted.
12. Secrets absent from Git and images.
13. Dependency/image/security scans reviewed.
14. Logs, metrics, correlation IDs, and alert paths validated.
15. Seed/reference import is idempotent.
16. Standards gaps and unresolved compliance items are visible.
17. Release notes, runbooks, and rollback steps are current.
18. Representative end-to-end project workflow passes.
19. Issued reports are reproducible from frozen runs.
20. Independent engineering review is recorded for safety-critical engines.

Deployment completion does not mean all EOS-01 through EOS-15 capabilities are complete. Release scope and enterprise roadmap status must be reported separately.

---

## 23. Tracked file register

The inventory below was read from GitHub `master` at `ac80cf0` and is retained as history. The live inventory is `git ls-files` at the current baseline (`103d8d2`), and `docs/project-status.md` is the controlled status register; files added since `ac80cf0` (jurisdiction package, deployment utilities, scripts, CI workflow, frontend cable/fault features, shell, registry) are governed by their source and tests.

| No. | File | Function |
|---:|---|---|
| 1 | `.gitignore` | Prevents virtual environments, secrets, caches, build outputs, and local artifacts from entering Git. |
| 2 | `README.md` | Defines the product vision, principles, module map, stack, repository overview, and development workflow. |
| 3 | `backend/alembic.ini` | Configures Alembic migration discovery and runtime behavior. |
| 4 | `backend/app/__init__.py` | Defines the Python package boundary and, where applicable, its supported public exports. |
| 5 | `backend/app/api/dependencies.py` | Provides dependency-injected database sessions and other shared API dependencies. |
| 6 | `backend/app/api/router.py` | Composes all versioned API routers into the application API. |
| 7 | `backend/app/api/v1/cable.py` | Exposes the versioned FastAPI endpoints for cable, delegates orchestration, and returns strict response schemas. |
| 8 | `backend/app/api/v1/fault.py` | Exposes the versioned FastAPI endpoints for fault, delegates orchestration, and returns strict response schemas. |
| 9 | `backend/app/api/v1/generator_sizing.py` | Exposes the versioned FastAPI endpoints for generator sizing, delegates orchestration, and returns strict response schemas. |
| 10 | `backend/app/api/v1/ht_panel.py` | Exposes the versioned FastAPI endpoints for ht panel, delegates orchestration, and returns strict response schemas. |
| 11 | `backend/app/api/v1/load_calculation_run.py` | Exposes the versioned FastAPI endpoints for load calculation run, delegates orchestration, and returns strict response schemas. |
| 12 | `backend/app/api/v1/load_demand.py` | Exposes the versioned FastAPI endpoints for load demand, delegates orchestration, and returns strict response schemas. |
| 13 | `backend/app/api/v1/lt_pcc.py` | Exposes the versioned FastAPI endpoints for lt pcc, delegates orchestration, and returns strict response schemas. |
| 14 | `backend/app/api/v1/standard.py` | Exposes the versioned FastAPI endpoints for standard, delegates orchestration, and returns strict response schemas. |
| 15 | `backend/app/api/v1/transformer_sizing.py` | Exposes the versioned FastAPI endpoints for transformer sizing, delegates orchestration, and returns strict response schemas. |
| 16 | `backend/app/api/v1/unit.py` | Exposes the versioned FastAPI endpoints for unit, delegates orchestration, and returns strict response schemas. |
| 17 | `backend/app/core/__init__.py` | Defines the Python package boundary and, where applicable, its supported public exports. |
| 18 | `backend/app/core/config.py` | Loads and validates application settings and environment configuration. |
| 19 | `backend/app/core/logging.py` | Configures consistent structured application logging. |
| 20 | `backend/app/db/__init__.py` | Defines the Python package boundary and, where applicable, its supported public exports. |
| 21 | `backend/app/db/base.py` | Defines shared SQLAlchemy metadata, UUID identity, and audit timestamp foundations. |
| 22 | `backend/app/db/engine.py` | Creates the asynchronous SQLAlchemy database engine. |
| 23 | `backend/app/db/session.py` | Creates async session factories and transaction-scoped database sessions. |
| 24 | `backend/app/domain/__init__.py` | Defines the Python package boundary and, where applicable, its supported public exports. |
| 25 | `backend/app/domain/electrical/__init__.py` | Defines the Python package boundary and, where applicable, its supported public exports. |
| 26 | `backend/app/domain/electrical/cable/__init__.py` | Defines the Python package boundary and, where applicable, its supported public exports. |
| 27 | `backend/app/domain/electrical/cable/cable_engine.py` | Implements the pure deterministic Decimal calculation engine for the cable domain. |
| 28 | `backend/app/domain/electrical/cable/cable_models.py` | Defines immutable/validated input models, value objects, and enums for the cable domain. |
| 29 | `backend/app/domain/electrical/cable/cable_results.py` | Defines auditable result, warning, margin, and design-check status contracts for the cable domain. |
| 30 | `backend/app/domain/electrical/distribution/__init__.py` | Defines the Python package boundary and, where applicable, its supported public exports. |
| 31 | `backend/app/domain/electrical/distribution/lt_pcc_engine.py` | Implements the pure deterministic Decimal calculation engine for the distribution domain. |
| 32 | `backend/app/domain/electrical/distribution/lt_pcc_models.py` | Defines immutable/validated input models, value objects, and enums for the distribution domain. |
| 33 | `backend/app/domain/electrical/distribution/lt_pcc_results.py` | Defines auditable result, warning, margin, and design-check status contracts for the distribution domain. |
| 34 | `backend/app/domain/electrical/fault/__init__.py` | Defines the Python package boundary and, where applicable, its supported public exports. |
| 35 | `backend/app/domain/electrical/fault/fault_engine.py` | Implements the pure deterministic Decimal calculation engine for the fault domain. |
| 36 | `backend/app/domain/electrical/fault/fault_models.py` | Defines immutable/validated input models, value objects, and enums for the fault domain. |
| 37 | `backend/app/domain/electrical/fault/fault_network.py` | Builds and reduces symmetrical-sequence networks for fault calculation. |
| 38 | `backend/app/domain/electrical/fault/fault_results.py` | Defines auditable result, warning, margin, and design-check status contracts for the fault domain. |
| 39 | `backend/app/domain/electrical/loads/__init__.py` | Defines the Python package boundary and, where applicable, its supported public exports. |
| 40 | `backend/app/domain/electrical/loads/engine.py` | Implements the pure deterministic Decimal calculation engine for the loads domain. |
| 41 | `backend/app/domain/electrical/loads/models.py` | Defines immutable/validated input models, value objects, and enums for the loads domain. |
| 42 | `backend/app/domain/electrical/loads/results.py` | Defines auditable result, warning, margin, and design-check status contracts for the loads domain. |
| 43 | `backend/app/domain/electrical/network/__init__.py` | Defines the Python package boundary and, where applicable, its supported public exports. |
| 44 | `backend/app/domain/electrical/network/sld_engine.py` | Implements the pure deterministic Decimal calculation engine for the network domain. |
| 45 | `backend/app/domain/electrical/network/sld_models.py` | Defines immutable/validated input models, value objects, and enums for the network domain. |
| 46 | `backend/app/domain/electrical/network/sld_results.py` | Defines auditable result, warning, margin, and design-check status contracts for the network domain. |
| 47 | `backend/app/domain/electrical/protection/__init__.py` | Defines the Python package boundary and, where applicable, its supported public exports. |
| 48 | `backend/app/domain/electrical/protection/coordination_engine.py` | Implements the pure deterministic Decimal calculation engine for the protection domain. |
| 49 | `backend/app/domain/electrical/protection/coordination_models.py` | Defines immutable/validated input models, value objects, and enums for the protection domain. |
| 50 | `backend/app/domain/electrical/protection/coordination_results.py` | Defines auditable result, warning, margin, and design-check status contracts for the protection domain. |
| 51 | `backend/app/domain/electrical/protection/switchgear_engine.py` | Implements the pure deterministic Decimal calculation engine for the protection domain. |
| 52 | `backend/app/domain/electrical/protection/switchgear_models.py` | Defines immutable/validated input models, value objects, and enums for the protection domain. |
| 53 | `backend/app/domain/electrical/protection/switchgear_results.py` | Defines auditable result, warning, margin, and design-check status contracts for the protection domain. |
| 54 | `backend/app/domain/electrical/relay/__init__.py` | Defines the Python package boundary and, where applicable, its supported public exports. |
| 55 | `backend/app/domain/electrical/relay/relay_engine.py` | Implements the pure deterministic Decimal calculation engine for the relay domain. |
| 56 | `backend/app/domain/electrical/relay/relay_models.py` | Defines immutable/validated input models, value objects, and enums for the relay domain. |
| 57 | `backend/app/domain/electrical/relay/relay_results.py` | Defines auditable result, warning, margin, and design-check status contracts for the relay domain. |
| 58 | `backend/app/domain/electrical/sources/__init__.py` | Defines the Python package boundary and, where applicable, its supported public exports. |
| 59 | `backend/app/domain/electrical/sources/common.py` | Provides shared source-sizing value objects, policies, and reusable utilities. |
| 60 | `backend/app/domain/electrical/sources/engine.py` | Implements the pure deterministic Decimal calculation engine for the sources domain. |
| 61 | `backend/app/domain/electrical/sources/generator_engine.py` | Implements the pure deterministic Decimal calculation engine for the sources domain. |
| 62 | `backend/app/domain/electrical/sources/generator_models.py` | Defines immutable/validated input models, value objects, and enums for the sources domain. |
| 63 | `backend/app/domain/electrical/sources/generator_results.py` | Defines auditable result, warning, margin, and design-check status contracts for the sources domain. |
| 64 | `backend/app/domain/electrical/sources/ht_panel_engine.py` | Implements the pure deterministic Decimal calculation engine for the sources domain. |
| 65 | `backend/app/domain/electrical/sources/ht_panel_models.py` | Defines immutable/validated input models, value objects, and enums for the sources domain. |
| 66 | `backend/app/domain/electrical/sources/ht_panel_results.py` | Defines auditable result, warning, margin, and design-check status contracts for the sources domain. |
| 67 | `backend/app/domain/electrical/sources/models.py` | Defines immutable/validated input models, value objects, and enums for the sources domain. |
| 68 | `backend/app/domain/electrical/sources/pv_engine.py` | Implements the pure deterministic Decimal calculation engine for the sources domain. |
| 69 | `backend/app/domain/electrical/sources/pv_models.py` | Defines immutable/validated input models, value objects, and enums for the sources domain. |
| 70 | `backend/app/domain/electrical/sources/pv_results.py` | Defines auditable result, warning, margin, and design-check status contracts for the sources domain. |
| 71 | `backend/app/domain/electrical/sources/results.py` | Defines auditable result, warning, margin, and design-check status contracts for the sources domain. |
| 72 | `backend/app/domain/electrical/sources/ups_engine.py` | Implements the pure deterministic Decimal calculation engine for the sources domain. |
| 73 | `backend/app/domain/electrical/sources/ups_models.py` | Defines immutable/validated input models, value objects, and enums for the sources domain. |
| 74 | `backend/app/domain/electrical/sources/ups_results.py` | Defines auditable result, warning, margin, and design-check status contracts for the sources domain. |
| 75 | `backend/app/main.py` | Creates the FastAPI application, lifecycle, middleware, health/version endpoints, and root router registration. |
| 76 | `backend/app/models/load_calculation_run.py` | Defines the SQLAlchemy persistence model and database constraints for load calculation run. |
| 77 | `backend/app/models/standard.py` | Defines the SQLAlchemy persistence model and database constraints for standard. |
| 78 | `backend/app/models/unit.py` | Defines the SQLAlchemy persistence model and database constraints for unit. |
| 79 | `backend/app/repositories/load_calculation_run.py` | Implements ordered async persistence operations for load calculation run without HTTP or calculation logic. |
| 80 | `backend/app/repositories/standard.py` | Implements ordered async persistence operations for standard without HTTP or calculation logic. |
| 81 | `backend/app/repositories/unit.py` | Implements ordered async persistence operations for unit without HTTP or calculation logic. |
| 82 | `backend/app/schemas/cable.py` | Defines strict Pydantic request, response, and cross-field validation contracts for cable. |
| 83 | `backend/app/schemas/fault.py` | Defines strict Pydantic request, response, and cross-field validation contracts for fault. |
| 84 | `backend/app/schemas/generator_sizing.py` | Defines strict Pydantic request, response, and cross-field validation contracts for generator sizing. |
| 85 | `backend/app/schemas/ht_panel.py` | Defines strict Pydantic request, response, and cross-field validation contracts for ht panel. |
| 86 | `backend/app/schemas/load_calculation_run.py` | Defines strict Pydantic request, response, and cross-field validation contracts for load calculation run. |
| 87 | `backend/app/schemas/load_demand.py` | Defines strict Pydantic request, response, and cross-field validation contracts for load demand. |
| 88 | `backend/app/schemas/lt_pcc.py` | Defines strict Pydantic request, response, and cross-field validation contracts for lt pcc. |
| 89 | `backend/app/schemas/standard.py` | Defines strict Pydantic request, response, and cross-field validation contracts for standard. |
| 90 | `backend/app/schemas/transformer_sizing.py` | Defines strict Pydantic request, response, and cross-field validation contracts for transformer sizing. |
| 91 | `backend/app/schemas/unit.py` | Defines strict Pydantic request, response, and cross-field validation contracts for unit. |
| 92 | `backend/app/services/cable.py` | Orchestrates the cable application use case between schemas, domain logic, and persistence. |
| 93 | `backend/app/services/fault.py` | Orchestrates the fault application use case between schemas, domain logic, and persistence. |
| 94 | `backend/app/services/generator_sizing.py` | Orchestrates the generator sizing application use case between schemas, domain logic, and persistence. |
| 95 | `backend/app/services/ht_panel.py` | Orchestrates the ht panel application use case between schemas, domain logic, and persistence. |
| 96 | `backend/app/services/load_calculation_run.py` | Orchestrates the load calculation run application use case between schemas, domain logic, and persistence. |
| 97 | `backend/app/services/load_demand.py` | Orchestrates the load demand application use case between schemas, domain logic, and persistence. |
| 98 | `backend/app/services/lt_pcc.py` | Orchestrates the lt pcc application use case between schemas, domain logic, and persistence. |
| 99 | `backend/app/services/standard.py` | Orchestrates the standard application use case between schemas, domain logic, and persistence. |
| 100 | `backend/app/services/transformer_sizing.py` | Orchestrates the transformer sizing application use case between schemas, domain logic, and persistence. |
| 101 | `backend/app/services/unit.py` | Orchestrates the unit application use case between schemas, domain logic, and persistence. |
| 102 | `backend/migrations/README` | Explains the Alembic migration directory. |
| 103 | `backend/migrations/env.py` | Connects Alembic to application metadata and migration configuration. |
| 104 | `backend/migrations/script.py.mako` | Template used when generating new Alembic revisions. |
| 105 | `backend/migrations/versions/143e87579da2_initial_schema.py` | Creates the initial database schema. |
| 106 | `backend/migrations/versions/2019c1a33308_kese_s2_m3_add_load_calculation_runs.py` | Adds persistent, auditable load calculation runs. |
| 107 | `backend/migrations/versions/90c8a737dfe4_add_units_table.py` | Adds the engineering units registry. |
| 108 | `backend/migrations/versions/bc8032471425_harden_unit_conversion_factor_precision.py` | Migrates unit conversion factors to deterministic decimal storage. |
| 109 | `backend/migrations/versions/c4f1a2b3d4e5_upgrade_standards_for_kese_s1_m3.py` | Upgrades the engineering standards registry for KESE-S1-M3. |
| 110 | `backend/pyproject.toml` | Declares backend dependencies and the pytest, coverage, Ruff, and mypy quality policies. |
| 111 | `backend/tests/api/test_cable.py` | Verifies cable API success, validation, serialization, warning, and failure behavior. |
| 112 | `backend/tests/api/test_generator_sizing.py` | Verifies generator sizing API success, validation, serialization, warning, and failure behavior. |
| 113 | `backend/tests/api/test_ht_panel.py` | Verifies ht panel API success, validation, serialization, warning, and failure behavior. |
| 114 | `backend/tests/api/test_load_calculation_run.py` | Verifies load calculation run API success, validation, serialization, warning, and failure behavior. |
| 115 | `backend/tests/api/test_load_demand.py` | Verifies load demand API success, validation, serialization, warning, and failure behavior. |
| 116 | `backend/tests/api/test_lt_pcc.py` | Verifies lt pcc API success, validation, serialization, warning, and failure behavior. |
| 117 | `backend/tests/api/test_standards.py` | Verifies standards API success, validation, serialization, warning, and failure behavior. |
| 118 | `backend/tests/api/test_transformer_sizing.py` | Verifies transformer sizing API success, validation, serialization, warning, and failure behavior. |
| 119 | `backend/tests/api/test_units.py` | Verifies units API success, validation, serialization, warning, and failure behavior. |
| 120 | `backend/tests/conftest.py` | Provides shared isolated test database, application, session, and API client fixtures. |
| 121 | `backend/tests/domain/electrical/cable/test_cable_engine.py` | Implements the pure deterministic Decimal calculation engine for the electrical domain. |
| 122 | `backend/tests/domain/electrical/cable/test_cable_models.py` | Defines immutable/validated input models, value objects, and enums for the electrical domain. |
| 123 | `backend/tests/domain/electrical/cable/test_cable_results.py` | Defines auditable result, warning, margin, and design-check status contracts for the electrical domain. |
| 124 | `backend/tests/domain/electrical/distribution/test_lt_pcc_engine.py` | Implements the pure deterministic Decimal calculation engine for the electrical domain. |
| 125 | `backend/tests/domain/electrical/distribution/test_lt_pcc_models.py` | Defines immutable/validated input models, value objects, and enums for the electrical domain. |
| 126 | `backend/tests/domain/electrical/distribution/test_lt_pcc_results.py` | Defines auditable result, warning, margin, and design-check status contracts for the electrical domain. |
| 127 | `backend/tests/domain/electrical/fault/test_fault_engine.py` | Implements the pure deterministic Decimal calculation engine for the electrical domain. |
| 128 | `backend/tests/domain/electrical/fault/test_fault_engine_golden.py` | Supports the pure electrical electrical engineering domain without API, database, or UI dependencies. |
| 129 | `backend/tests/domain/electrical/fault/test_fault_models.py` | Defines immutable/validated input models, value objects, and enums for the electrical domain. |
| 130 | `backend/tests/domain/electrical/fault/test_fault_network.py` | Supports the pure electrical electrical engineering domain without API, database, or UI dependencies. |
| 131 | `backend/tests/domain/electrical/fault/test_fault_results.py` | Defines auditable result, warning, margin, and design-check status contracts for the electrical domain. |
| 132 | `backend/tests/domain/electrical/loads/test_engine.py` | Implements the pure deterministic Decimal calculation engine for the electrical domain. |
| 133 | `backend/tests/domain/electrical/loads/test_models.py` | Defines immutable/validated input models, value objects, and enums for the electrical domain. |
| 134 | `backend/tests/domain/electrical/loads/test_results.py` | Defines auditable result, warning, margin, and design-check status contracts for the electrical domain. |
| 135 | `backend/tests/domain/electrical/network/test_sld_engine.py` | Implements the pure deterministic Decimal calculation engine for the electrical domain. |
| 136 | `backend/tests/domain/electrical/network/test_sld_models.py` | Defines immutable/validated input models, value objects, and enums for the electrical domain. |
| 137 | `backend/tests/domain/electrical/network/test_sld_results.py` | Defines auditable result, warning, margin, and design-check status contracts for the electrical domain. |
| 138 | `backend/tests/domain/electrical/protection/test_coordination_engine.py` | Implements the pure deterministic Decimal calculation engine for the electrical domain. |
| 139 | `backend/tests/domain/electrical/protection/test_coordination_models.py` | Defines immutable/validated input models, value objects, and enums for the electrical domain. |
| 140 | `backend/tests/domain/electrical/protection/test_coordination_results.py` | Defines auditable result, warning, margin, and design-check status contracts for the electrical domain. |
| 141 | `backend/tests/domain/electrical/protection/test_switchgear_engine.py` | Implements the pure deterministic Decimal calculation engine for the electrical domain. |
| 142 | `backend/tests/domain/electrical/protection/test_switchgear_models.py` | Defines immutable/validated input models, value objects, and enums for the electrical domain. |
| 143 | `backend/tests/domain/electrical/protection/test_switchgear_results.py` | Defines auditable result, warning, margin, and design-check status contracts for the electrical domain. |
| 144 | `backend/tests/domain/electrical/relay/test_relay_engine.py` | Implements the pure deterministic Decimal calculation engine for the electrical domain. |
| 145 | `backend/tests/domain/electrical/relay/test_relay_models.py` | Defines immutable/validated input models, value objects, and enums for the electrical domain. |
| 146 | `backend/tests/domain/electrical/relay/test_relay_results.py` | Defines auditable result, warning, margin, and design-check status contracts for the electrical domain. |
| 147 | `backend/tests/domain/electrical/sources/test_common.py` | Supports the pure electrical electrical engineering domain without API, database, or UI dependencies. |
| 148 | `backend/tests/domain/electrical/sources/test_engine.py` | Implements the pure deterministic Decimal calculation engine for the electrical domain. |
| 149 | `backend/tests/domain/electrical/sources/test_generator_engine.py` | Implements the pure deterministic Decimal calculation engine for the electrical domain. |
| 150 | `backend/tests/domain/electrical/sources/test_generator_models.py` | Defines immutable/validated input models, value objects, and enums for the electrical domain. |
| 151 | `backend/tests/domain/electrical/sources/test_generator_results.py` | Defines auditable result, warning, margin, and design-check status contracts for the electrical domain. |
| 152 | `backend/tests/domain/electrical/sources/test_ht_panel_engine.py` | Implements the pure deterministic Decimal calculation engine for the electrical domain. |
| 153 | `backend/tests/domain/electrical/sources/test_ht_panel_models.py` | Defines immutable/validated input models, value objects, and enums for the electrical domain. |
| 154 | `backend/tests/domain/electrical/sources/test_ht_panel_results.py` | Defines auditable result, warning, margin, and design-check status contracts for the electrical domain. |
| 155 | `backend/tests/domain/electrical/sources/test_models.py` | Defines immutable/validated input models, value objects, and enums for the electrical domain. |
| 156 | `backend/tests/domain/electrical/sources/test_pv_engine.py` | Implements the pure deterministic Decimal calculation engine for the electrical domain. |
| 157 | `backend/tests/domain/electrical/sources/test_pv_models.py` | Defines immutable/validated input models, value objects, and enums for the electrical domain. |
| 158 | `backend/tests/domain/electrical/sources/test_pv_results.py` | Defines auditable result, warning, margin, and design-check status contracts for the electrical domain. |
| 159 | `backend/tests/domain/electrical/sources/test_results.py` | Defines auditable result, warning, margin, and design-check status contracts for the electrical domain. |
| 160 | `backend/tests/domain/electrical/sources/test_ups_engine.py` | Implements the pure deterministic Decimal calculation engine for the electrical domain. |
| 161 | `backend/tests/domain/electrical/sources/test_ups_models.py` | Defines immutable/validated input models, value objects, and enums for the electrical domain. |
| 162 | `docs/adr/0001-system-architecture.md` | Records the accepted standards-first layered modular-monolith architecture. |
| 163 | `docs/adr/0002-engineering-units-and-rounding.md` | Records the mandatory Decimal, units, comparison, tolerance, and rounding policy. |
| 164 | `docs/domain-glossary.md` | Defines controlled electrical, calculation, standards, result-state, and audit terminology. |
| 165 | `docs/specifications/kese-s1-m3-engineering-standards-crud.md` | Specifies the implemented engineering standards CRUD milestone. |
| 166 | `docs/specifications/legacy-standards-governance-roadmap.md` | Specifies the future full standards registry, evidence, applicability, precedence, and readiness model. |
| 167 | `frontend/index.html` | Provides the browser HTML entry point used by Vite. |
| 168 | `frontend/package-lock.json` | Locks exact frontend dependency versions for reproducible installation. |
| 169 | `frontend/package.json` | Declares frontend dependencies, runtime versions, and development/quality commands. |
| 170 | `frontend/src/App.tsx` | Defines the top-level application workspace shell. |
| 171 | `frontend/src/app/providers.test.tsx` | Verifies provider cache stability and test isolation. |
| 172 | `frontend/src/app/providers.tsx` | Owns stable application-wide providers such as TanStack Query. |
| 173 | `frontend/src/app/router.tsx` | Defines the browser route tree and workspace navigation entry points. |
| 174 | `frontend/src/components/ApiHealthStatus.test.tsx` | Verifies API health status rendering and behavior. |
| 175 | `frontend/src/components/ApiHealthStatus.tsx` | Displays API availability and recovery state. |
| 176 | `frontend/src/components/FaultStudyForm.test.tsx` | Verifies Fault form validation, field activation, and submission. |
| 177 | `frontend/src/components/FaultStudyForm.tsx` | Collects, validates, and submits short-circuit study inputs. |
| 178 | `frontend/src/main.tsx` | Bootstraps React, application providers, routing, and global styles. |
| 179 | `frontend/src/pages/FaultStudyPage.test.tsx` | Verifies Fault study page orchestration. |
| 180 | `frontend/src/pages/FaultStudyPage.tsx` | Composes the Fault study workflow page and result presentation. |
| 181 | `frontend/src/services/fault.test.ts` | Verifies Fault service requests, responses, failures, timeout, and cancellation. |
| 182 | `frontend/src/services/fault.ts` | Serializes Fault inputs, calls the API, validates responses, and preserves decimal strings. |
| 183 | `frontend/src/services/faultContract.ts` | Defines validated frontend primitives for the Fault API contract. |
| 184 | `frontend/src/services/health.test.ts` | Verifies health service response validation, errors, timeout, and cancellation. |
| 185 | `frontend/src/services/health.ts` | Calls and validates the backend health endpoint. |
| 186 | `frontend/src/styles/global.css` | Provides the global workspace design foundation and accessible base styling. |
| 187 | `frontend/tsconfig.app.json` | Applies strict TypeScript rules to browser application code. |
| 188 | `frontend/tsconfig.json` | Coordinates the frontend TypeScript project references. |
| 189 | `frontend/tsconfig.node.json` | Applies TypeScript rules to Node-based build configuration. |
| 190 | `frontend/vite.config.ts` | Configures Vite, React, Vitest, and frontend build behavior. |

---

## 24. Start-of-session instruction

At every continuation:

1. Briefly explain the next purpose in Hindi.
2. Give only the first short read-only command.
3. Wait for the user's terminal output.
4. Review the output before any change.
5. Continue one file at a time.
6. Preserve every existing local modification and untracked file.
7. Re-read applicable reference, ADR, schema, caller, and focused tests before editing.
8. Never infer compliance from a successful calculation.
9. Never claim a file, test, commit, push, migration, or deployment succeeded without direct evidence.
10. Stop and report any permission, destructive-action, standards, migration, or scope blocker.

### First inspection command for the known repository

```bash
cd ~/projects/KES_Electrical_OS && git status --short
```

Do not combine further commands until its output is reviewed.

---

## 25. Required response style

- Explain briefly and clearly in Hindi.
- Keep code, identifiers, filenames, file contents, and terminal commands in English.
- Lead with outcome.
- Give one short command at a time.
- State exactly which file is active and its function.
- State validation evidence, not assumptions.
- Maintain the release-slice countdown after every completed file.
- Do not overstate compliance, completion, or deployment readiness.

---

## 26. Final instruction to the development assistant

Continue from the actual repository state, not from an idealized plan. Preserve working code and user changes. Follow §15 items 13–20 in order; a founder or product requirement that is not in §15 is first recorded as an amendment to this prompt and then scheduled, never started mid-slice.

At every stage, protect deterministic Decimal arithmetic, explicit units, standards provenance, auditability, immutable approved runs, independent review, tenant isolation, and the separation between engineering design checks and statutory compliance.

The product is **KES Electrical OS: an enterprise electrical engineering lifecycle and evidence system**, not a simple calculator.
