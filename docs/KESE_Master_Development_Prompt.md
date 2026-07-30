# KESE Master Development Prompt

* **Document status:** Controlled — single source of truth for continuing development
* **Project:** KES Electrical OS (KESE)
* **Owner:** Kamra Engineering Solutions (KES)
* **Prepared:** 30 July 2026
* **Purpose:** This document is the master prompt to load at the start of any development
  session (human or AI-assisted) on KES Electrical OS. It replaces reliance on the
  repository README, which is not kept current mission-by-mission. Read this document
  fully before proposing or writing any code.

---

## 0. Addendum — 30 July 2026 Restructure (read this first)

The project was restructured into a monorepo on 30 July 2026 per **ADR-0003**
(`docs/adr/0003-multi-product-reusable-core.md`). Summary:

* The domain calculation layer (loads, transformer/generator sizing) moved out of
  `apps/kes-electrical-os/backend/app/domain/` into a standalone, zero-dependency
  package `packages/kes_electrical_core/`, importable by KES Electrical OS, Kamra
  BENAS, Kamra Climate OS, MEP, and BMS.
* This was a **move, not a rewrite** — all 346 tests still pass (303 in
  `kes_electrical_core`, 43 in the app shell). No calculation logic changed.
* CPWD (General Specifications for Electrical Works) is now the adopted authoritative
  Indian standards source; Schneider Electric technical resources are used as
  engineering-methodology reference only (never reproduced verbatim). See
  `docs/standards/README.md` — the CPWD PDF is still pending upload as of this writing.
* §2 and §6 below describe the **pre-restructure** single-app architecture and mission
  history; they remain historically accurate for what was built, but new missions
  should target the new `packages/` + `apps/` layout, not the old `backend/` layout
  described below.

---

## 1. What This Project Is

KES Electrical OS is the electrical engineering domain of Kamra Engineering Solutions.
It converts a controlled project design basis into traceable calculations, coordinated
equipment selections, engineering schedules, compliance evidence, reports, and
commissioning records.

Repository: `https://github.com/kamracp/KES_Electrical_OS`

### Product Principles (non-negotiable)

1. Standards and project applicability are resolved before compliance conclusions.
2. Engineering calculations remain independent of UI, database, and manufacturer catalogs.
3. Every input, assumption, formula, result, warning, revision, and approval is traceable.
4. Unknown standards editions or amendments block compliance-ready status.
5. Approved calculation runs are immutable and reproducible.
6. Manufacturer information is consumed through versioned adapters without vendor lock-in.
7. Safety-critical calculations require independent engineering review.

Any proposed work that would weaken one of these seven principles must be flagged
explicitly before implementation, not silently absorbed into a mission.

---

## 2. Architecture (ADR-0001 — Standards-First Layered Modular Architecture)

Backend implementation flow, in strict order, for every new capability:

```
Model → Schema → Repository → Service → API → Router Registration → Alembic Migration → Automated Tests
```

### Layers

1. **Domain layer** — pure Python engineering entities, value objects, calculation
   engines. `Decimal` arithmetic. Explicit units. Rounding/tolerance/warning/result-state
   policies. Standards-derived rules. **No imports from FastAPI, SQLAlchemy, PostgreSQL,
   or frontend code.** Mandatory for every calculation module.
2. **Schema layer** — Pydantic v2. Request validation, response serialization,
   field/range validation, cross-field business validation, strict unexpected-field
   rejection. No transaction logic.
3. **Repository layer** — async SQLAlchemy. Creation, UUID retrieval, unique-code
   lookup, stable list ordering, update, delete. Receives an `AsyncSession`. No HTTP
   response logic.
4. **Service layer** — use-case orchestration, business rules, schema→model
   conversion, partial-update handling, API↔repository coordination, integration with
   domain engines. Independent of HTTP status codes.
5. **Persistence layer** — PostgreSQL, SQLAlchemy 2.x async, UUID primary keys, audit
   timestamps, Alembic migrations, named constraints/indexes. **Approved calculation
   runs must be immutable.**
6. **API layer** — FastAPI, versioned REST endpoints, dependency-injected async
   sessions, strict validation, consistent HTTP status codes, UUID resource IDs,
   conflict/not-found handling, OpenAPI docs. No direct SQL.
7. **Presentation/integration layer** (planned) — React/TypeScript/Vite, DOCX/PDF/
   Excel/CSV reporting, manufacturer-data adapters, CAD/BIM, BMS/SCADA/IoT.
   Manufacturer data must stay outside core engineering formulas.

### Dependency direction

API → services/schemas → repositories/domain → SQLAlchemy models. Domain code never
depends upward. No circular imports.

### Database conventions

UUID primary keys, `created_at`/`updated_at`, explicit nullability, named constraints,
controlled indexes, Alembic migrations only — **no manual schema edits**.

---

## 3. Engineering Units, Decimal & Rounding Policy (ADR-0002)

* Explicit engineering units for every dimensional input/output.
* Python `Decimal` for all engineering-domain calculations — constructed from strings,
  integers, or validated Decimal values. **`float` is prohibited inside the domain core.**
* Canonical SI-based internal calculation units, centralized/tested conversions.
* Unrounded values for engineering comparisons; explicit output quantization using
  `ROUND_HALF_UP`; module-specific tolerances.
* PostgreSQL `NUMERIC` for persisted engineering calculation values.

### ⚠ Known transitional gap (unresolved)

`Unit.conversion_factor` is still a SQLAlchemy **float** column, not `NUMERIC`. This was
accepted temporarily because the Units CRUD milestone validated persistence flow, not
calculation precision, and no calculation engine currently consumes persisted conversion
factors directly. **Before any calculation module reads persisted conversion factors**,
this must be fixed:

1. Migrate `conversion_factor` to PostgreSQL `NUMERIC`.
2. Update the Pydantic schema to accept/return Decimal-compatible values.
3. Add repository/service round-trip tests confirming exact Decimal preservation.
4. Review existing Unit records for conversion accuracy.

---

## 4. Controlled Terminology (see `docs/domain-glossary.md` for full list)

* **KESE** — controlled development-mission prefix (`KESE-S{season}-M{mission}`).
* **EOS-xx** — product-module identifier (see module table below).
* **Milestone/Mission** — a controlled development scope: defined scope, implemented
  files, validation evidence, migration where required, automated tests where required,
  commit, remote sync.
* **Raw Result** vs **Display Result** — raw unrounded result drives engineering
  decisions; display result is quantized for presentation. Never substitute one for
  the other.
* **Tolerance** — must be named and version-controlled; hidden global tolerances are
  prohibited.
* Controlled terms must not be renamed, combined, or reused with different meaning
  without an approved ADR.

---

## 5. Product Modules (target scope)

| ID | Module | Status |
|---|---|---|
| EOS-01 | Project Configuration | Not started |
| EOS-02 | Engineering Standards | ✅ CRUD complete (S1-M3) |
| EOS-02b | Engineering Units | ✅ CRUD complete (S1-M2/M4) |
| EOS-02c | Load & Demand | ✅ Complete (S2-M1–M3) |
| EOS-03 | Transformer, DG, UPS & PV | ⚠ Partial — Transformer + Generator sizing engines done (S2-M4–M7); UPS/PV/battery not started; **no persistence/audit trail** |
| EOS-04 | Short-Circuit & Earth-Fault | Not started |
| EOS-05 | Protection Coordination | Not started |
| EOS-06 | Cable Sizing | Not started |
| EOS-07 | Panels & IEC 61439 | Not started |
| EOS-08 | Earthing & Bonding | Not started |
| EOS-09 | Lightning Protection | Not started |
| EOS-10 | Surge Protection | Not started |
| EOS-11 | Power Factor & Harmonics | Not started |
| EOS-12 | Cable Tray & Routing | Not started |
| EOS-13 | Engineering Deliverables | Not started |
| EOS-14 | FAT, SAT & Commissioning | Not started |
| EOS-15 | Metering, BMS, SCADA & IoT | Not started |

Note: the module numbering above follows the original README table; the actually
implemented `EOS-02` code (Standards, Units) and `EOS-02c` (Load & Demand) predate a
full EOS-01 Project Configuration module. Project Configuration should be revisited
before modules start depending on project-scoped data (jurisdiction, project-standard
assignment) — currently every calculation is global, not project-scoped.

---

## 6. Mission History — Verified Against Actual Code (30 July 2026)

The README's "Current Status" section is **stale** (it still says "KEOS-S1-M1 foundation
work is in progress"). The real state, reconstructed from module headers, the domain
glossary, and migration history:

| Mission | Scope | Status | Evidence |
|---|---|---|---|
| S1-M1 | Backend & database foundation | ✅ Completed | domain-glossary.md |
| S1-M2 | Engineering Units CRUD | ✅ Completed (commit `b78fa26`) | domain-glossary.md |
| S1-M3 | Engineering Standards CRUD | ✅ Completed (commit `8ef97ea`) | spec + migration `c4f1a2b3d4e5` |
| S1-M4 | Unit conversion-factor precision hardening (partial — see §3 gap) | ⚠ Migration exists (`bc8032471425`) but ADR-0002 marks it transitional/incomplete | ADR-0002 |
| S2-M1 | Load domain engine (pure calculation core) | ✅ Completed | `app/domain/electrical/loads/engine.py` |
| S2-M2 | Load Demand API | ✅ Completed | `app/api/v1/load_demand.py` |
| S2-M3 | Load Calculation Run persistence (immutable audit + revision + approval workflow) | ✅ Completed | migration `2019c1a33308` |
| S2-M4 | Transformer sizing domain engine | ✅ Completed | `app/domain/electrical/sources/engine.py` |
| S2-M5 | Transformer sizing API | ✅ Completed | `app/api/v1/transformer_sizing.py` |
| S2-M6 | Generator sizing domain engine | ✅ Completed | `app/domain/electrical/sources/generator_engine.py` |
| S2-M7 | Generator sizing API | ✅ Completed | `app/api/v1/generator_sizing.py` |

**Migration chain (head = `2019c1a33308`):**
`143e87579da2` (initial) → `90c8a737dfe4` (add units) → `c4f1a2b3d4e5` (upgrade standards,
S1-M3) → `bc8032471425` (harden unit conversion_factor precision) → `2019c1a33308`
(S2-M3, add load_calculation_runs).

---

## 7. Verified Repository Health (as of 30 July 2026, from uploaded zip)

* **Tests:** 346/346 passing.
* **Coverage:** 88.91% (gate: 80%, `pyproject.toml` `fail_under = 80`).
* **Lint (ruff):** 20 issues, 18 auto-fixable (mostly import ordering) — not yet cleaned up.
* **mypy strict mode:** configured, not yet run in this session.
* No local `.git` history was present in the uploaded archive (zip export only) —
  commit hashes above are taken from spec/glossary documentation, not verified against
  actual git log.

---

## 8. Known Gaps / Technical Debt (open, prioritized)

1. **Audit-trail asymmetry (highest priority).** `LoadCalculationRun` gives Load & Demand
   calculations a full immutable/revision/approval workflow. Transformer and Generator
   sizing (`TransformerSizingService`, `GeneratorSizingService`) are stateless — no run
   is persisted, no approval workflow, no revision history. This directly contradicts
   Product Principle 3 and 5. Candidate next mission: **S2-M8**, generalizing calculation-
   run persistence to cover source-sizing calculation types, or adding a parallel
   `SourceSizingRun` model reusing the same audit/approval pattern as `LoadCalculationRun`.
2. **Unit conversion_factor precision gap** (§3) — must close before any future
   calculation module reads persisted conversion factors.
3. **EOS-01 Project Configuration missing** — every calculation today is global/
   unscoped; no project entity, no project-standard assignment, no jurisdiction control.
   This will need to exist before compliance-readiness gating (ADR-0001 "Standards
   Governance" section) can be implemented meaningfully.
4. **Ruff import-ordering issues** — 20 findings, 18 auto-fixable. Low priority but
   should be cleaned before the next mission's diff to avoid mixing unrelated changes.
5. **README is stale** — must be updated to reflect actual mission status once the
   next mission is agreed and started (see Development Workflow §9, step 6 below,
   which the project's own workflow already requires but which has clearly lapsed).
6. The original, more elaborate KEOS-S1-M1 standards-governance entity model
   (`StandardsOrganization` / `StandardFamily` / `StandardDocument` / `StandardEdition` /
   `StandardAmendment` / `ClauseReference` / `EvidenceSource` / `ProjectStandardAssignment`
   / `ApplicabilityDecision`, 16-record seed import) documented in
   `docs/specifications/legacy-standards-governance-roadmap.md` was **not built**. It was
   superseded by the simpler completed `KESE-S1-M3` single-table Standards CRUD. Treat
   the legacy roadmap file as aspirational/future scope, not a description of current
   code.

---

## 9. Development Workflow (must follow for every mission)

1. Implement one complete file or layer at a time.
2. Run its defined validation before moving to the next file.
3. Review the result before proceeding.
4. Add automated tests with every functional layer (unit, API, persistence, or
   integration as appropriate — use the pytest markers already defined:
   `unit`, `golden`, `api`, `persistence`, `integration`, `regression`).
5. Commit only after the mission or a controlled milestone is complete.
6. Update README, domain glossary, and this master prompt when a mission completes —
   do not let documented status drift from actual code (this has already happened once;
   do not repeat it).
7. Keep code and comments in English. Keep explanations and operating guidance simple.
8. Do not make manual database edits — every schema change goes through Alembic.
9. Do not silently replace an unknown/unverified standard edition or unit value with an
   assumed one — block and flag it instead.

---

## 10. Decision Point — Next Mission

Not yet decided by the project owner. Candidates on the table, in the order they were
proposed:

1. **S2-M8** — bring Transformer/Generator sizing into the same immutable audit-trail
   and approval-workflow persistence pattern as Load & Demand (closes the largest
   principle-3/principle-5 gap).
2. Fix the `Unit.conversion_factor` float→Decimal/NUMERIC gap (ADR-0002).
3. Start a new calculation module — most logical next candidate is **EOS-04
   Short-Circuit & Earth-Fault**, since Transformer/Generator source sizing (EOS-03) now
   provides the source data that fault calculations need.
4. Pure hygiene pass — fix the 20 ruff findings before starting new feature work.

Recommendation if asked: do (4) first as a fast, low-risk cleanup, then (1) before (3),
because building a fourth calculation module (short-circuit) on top of an already-known
audit-trail inconsistency compounds the debt rather than resolving it, and because EOS-04
will itself need immutable, approvable calculation runs from day one.

This section must be updated once the mission is chosen and again once it completes.
