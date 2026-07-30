# ADR-0003: Multi-Product Reusable Electrical Engineering Core

* **Status:** Accepted
* **Date:** 30 July 2026
* **Project:** KES Electrical OS
* **Decision owners:** Kamra Engineering Solutions
* **Supersedes/extends:** ADR-0001 (layers stay the same; this ADR changes *where the
  domain layer physically lives*)

## Context

The electrical engineering calculation core (load & demand, transformer/generator
source sizing, Decimal/units policy) is needed by more than one product:

* **KES Electrical OS** — standalone electrical engineering SaaS.
* **Kamra BENAS / ISOS** — Net Zero and ESG Intelligence Platform.
* **Kamra Climate OS** — planned climate/energy product.
* **MEP** — mechanical/electrical/plumbing coordination work.
* **BMS** — building management system integration.

ADR-0001 already required the domain layer to be independent of FastAPI, SQLAlchemy,
PostgreSQL, and frontend code. In practice it still lived inside a single FastAPI
project (`backend/app/domain/...`), which made it importable only by that one app.

## Decision

Extract the domain layer into a standalone, installable, zero-dependency Python
package — `kes_electrical_core` — inside a monorepo. Each product becomes a separate
consumer (an "app shell") that imports the core and adds its own persistence, API, and
standards data.

### New repository layout

```text
KES_Electrical_OS/
├── packages/
│   └── kes_electrical_core/          # reusable, product-agnostic
│       ├── src/kes_electrical_core/
│       │   ├── loads/                # load & demand domain engine
│       │   └── sources/              # transformer + generator sizing domain engines
│       └── tests/
├── apps/
│   └── kes-electrical-os/            # the standalone KES Electrical OS product
│       └── backend/                  # FastAPI, SQLAlchemy, Alembic, API, tests
├── docs/
│   ├── adr/
│   ├── specifications/
│   │   ├── completed/                # historical record of shipped missions
│   │   └── future/                   # explicitly not-yet-built scope
│   └── standards/                    # CPWD / Schneider reference material lands here
└── README.md
```

### What moved and why

* `app/domain/electrical/loads/*` → `packages/kes_electrical_core/src/kes_electrical_core/loads/`
* `app/domain/electrical/sources/*` → `packages/kes_electrical_core/src/kes_electrical_core/sources/`
* Their test suites moved with them, unchanged in substance (import paths only).
* Everything else — models, schemas, repositories, services, API, migrations — stayed
  in `apps/kes-electrical-os/backend/`, because those layers are inherently
  product-specific (KES Electrical OS's own database, its own API contract).

Nothing was deleted from the domain engines. They were already standards-agnostic
(no hardcoded CPWD/IEC/IEEE formulas), so moving them is a pure restructuring, not a
rewrite — consistent with the "restructure, don't discard tested code" scope decided
on 30 July 2026.

### What is explicitly NOT shared (yet)

The Standards Registry and Engineering Units Registry (`app/models/standard.py`,
`app/models/unit.py` and their CRUD stack) **stay inside** the KES Electrical OS app
shell for now. They are not yet extracted into a shared package because:

1. Each consuming product may need its own applicability rules and its own database.
2. The registry's data model is still evolving (see ADR future-scope note on the
   superseded standards-governance entity model).
3. Extracting a shared *governance* package (as opposed to a shared *calculation*
   package) is a separate, larger decision that should wait until at least one other
   product (BENAS or Climate OS) actually needs to consume the same standards data —
   at that point a `kes_standards_governance` package should be split out the same way
   `kes_electrical_core` was.

### Standards & reference data policy (CPWD, Schneider)

* **CPWD General Specifications for Electrical Works** is adopted as an authoritative
  Indian standards source for the Standards Registry (`EOS-02`). Parts (Part 1
  Internal, Part 2 DG Sets/External, Part 3, Part 4 Substation, as applicable) are
  registered as distinct standard records with edition/year, consistent with the
  existing `standards` table fields (`code`, `edition`, `publication_year`, `status`).
* **Schneider Electric technical resources** (e.g., their Electrical Installation
  Guide) are used as an **engineering-methodology reference**, not as a data source to
  be copied. Calculation methods derived from widely-used, publicly documented
  electrical engineering practice may be implemented in `kes_electrical_core`; Schneider's
  proprietary text, tables, or figures are not reproduced verbatim anywhere in the
  codebase or docs. Where a specific published table (e.g., cable derating factors) is
  used, it is treated as an `EvidenceSource` (see the future standards-governance model)
  requiring its own provenance record, not silently hardcoded.
* Raw reference PDFs, once supplied, are stored under `docs/standards/` for the
  team's own use in extracting structured registry data — they are not shipped as
  part of any product build artifact.

## Consequences

* Positive: BENAS, Climate OS, MEP, and BMS can each add `kes_electrical_core` as a
  dependency and reuse load/source-sizing calculations without depending on KES
  Electrical OS's FastAPI app, database, or API.
* Positive: the core package's own test suite (currently ported 1:1 from the app) can
  evolve independently and gets its own coverage gate.
* Negative / follow-up: `apps/kes-electrical-os/backend`'s import paths changed
  (`app.domain.electrical.*` → `kes_electrical_core.*`); this is a breaking change for
  any external code that imported the old paths directly. None currently exists
  outside this repository.
* Follow-up: `kes-electrical-core` is currently referenced as a plain PyPI-style
  dependency name in `apps/kes-electrical-os/backend/pyproject.toml`; until this
  monorepo is wired into a proper workspace tool (e.g., `uv workspace` or an internal
  package index), it must be installed with `pip install -e ../../packages/kes_electrical_core`
  in each app shell's virtual environment.
