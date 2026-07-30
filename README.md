# KES Electrical OS

**Standards-governed · Calculation-first · Audit-ready · Manufacturer-neutral**

KES Electrical OS is the electrical engineering domain of Kamra Engineering Solutions. It converts a controlled project design basis into traceable calculations, coordinated equipment selections, engineering schedules, compliance evidence, reports, and commissioning records.

## Product Principles

- Standards and project applicability are resolved before compliance conclusions.
- Engineering calculations remain independent of UI, database, and manufacturer catalogs.
- Every input, assumption, formula, result, warning, revision, and approval is traceable.
- Unknown standards editions or amendments block compliance-ready status.
- Approved calculation runs are immutable and reproducible.
- Manufacturer information is consumed through versioned adapters without vendor lock-in.
- Safety-critical calculations require independent engineering review.

## Current Mission

### KEOS-S1-M1 — Standards Registry & Compliance Matrix

The first implementation mission will provide:

- Standards, editions, amendments, parts, and clause records.
- Evidence-source and provenance records.
- Project-level standards assignment and precedence.
- Applicability and jurisdiction controls.
- Compliance workflow states.
- Searchable registry and applicability matrix.
- Repository, service, persistence, API, and automated tests.
- Import of the controlled 16-record initial registry seed.

No unknown or unverified standard edition may produce a compliance-ready conclusion.

## Next Mission

### KEOS-S1-M2 — Load, Demand & Source Sizing

The first engineering calculation vertical slice will cover:

- Connected and demand load.
- Utilization and coincidence factors.
- Normal, emergency, outage, starting, UPS, PV, and future scenarios.
- Transformer, DG, UPS, battery, and PV source-sizing basis.
- Explicit units, Decimal arithmetic, rounding, assumptions, and warnings.
- Immutable calculation runs and approved golden-reference tests.

## Product Modules

| ID | Module |
|---|---|
| EOS-01 | Project Configuration |
| EOS-02 | Load & Demand |
| EOS-03 | Transformer, DG, UPS & PV |
| EOS-04 | Short-Circuit & Earth-Fault |
| EOS-05 | Protection Coordination |
| EOS-06 | Cable Sizing |
| EOS-07 | Panels & IEC 61439 |
| EOS-08 | Earthing & Bonding |
| EOS-09 | Lightning Protection |
| EOS-10 | Surge Protection |
| EOS-11 | Power Factor & Harmonics |
| EOS-12 | Cable Tray & Routing |
| EOS-13 | Engineering Deliverables |
| EOS-14 | FAT, SAT & Commissioning |
| EOS-15 | Metering, BMS, SCADA & IoT |

## Technology Stack

- **Frontend:** React, Vite, TypeScript
- **API:** FastAPI, Pydantic v2
- **Domain core:** Pure Python, Decimal, unit-aware value objects
- **Persistence:** PostgreSQL, SQLAlchemy 2.x, Alembic
- **Testing:** pytest, API, integration, persistence, golden-reference, and regression tests
- **Reporting:** DOCX, PDF, Excel, and CSV
- **Deployment:** Docker-ready modular architecture

## Repository Structure

```text
KES_Electrical_OS/
├── backend/
│   ├── app/api/v1/electrical/
│   ├── app/core/
│   ├── app/domain/electrical/
│   ├── app/models/
│   ├── app/repositories/
│   ├── app/schemas/
│   ├── app/services/
│   ├── migrations/
│   └── tests/
├── frontend/
├── reports/
├── docs/
│   └── adr/
└── deployment/
```

## Development Workflow

1. Implement one complete file or layer.
2. Run its defined validation.
3. Review the result before proceeding.
4. Add automated tests with every functional layer.
5. Commit only after the mission or controlled milestone is complete.
6. Keep explanations and operating guidance simple; keep code and comments in English.

## Current Status

- Master Framework and Implementation Roadmap V1.0 frozen on 25 July 2026.
- Git repository initialized on the `master` branch.
- Initial enterprise directory structure created.
- Root `.gitignore` created and functionally validated.
- `KEOS-S1-M1` foundation work is in progress.