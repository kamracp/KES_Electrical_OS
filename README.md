# KES Electrical OS — Monorepo

**Standards-governed · Calculation-first · Audit-ready · Manufacturer-neutral**

This repository now contains two things:

1. **`packages/kes_electrical_core`** — a standalone, zero-dependency Python package
   with the electrical engineering calculation engines (load & demand, transformer and
   generator source sizing, Decimal/units policy). It has no FastAPI, SQLAlchemy, or
   database code in it and can be installed by any product that needs these
   calculations: KES Electrical OS, Kamra BENAS, Kamra Climate OS, MEP, BMS.
2. **`apps/kes-electrical-os`** — the standalone KES Electrical OS product: FastAPI
   API, PostgreSQL persistence, Alembic migrations, standards/units registries,
   calculation-run audit trail. It depends on `kes_electrical_core`.

See `docs/adr/0003-multi-product-reusable-core.md` for why this split exists and
`docs/KESE_Master_Development_Prompt.md` for the full project status, mission history,
and open items — **read that file before starting any new work**, it is the
controlled source of truth, not this README.

## Repository Layout

```text
KES_Electrical_OS/
├── packages/
│   └── kes_electrical_core/      # reusable calculation core (product-agnostic)
├── apps/
│   └── kes-electrical-os/        # standalone KES Electrical OS backend (FastAPI)
├── docs/
│   ├── adr/                      # architecture decisions (0001, 0002, 0003)
│   ├── domain-glossary.md        # controlled terminology
│   ├── KESE_Master_Development_Prompt.md
│   ├── specifications/
│   │   ├── completed/            # historical record of shipped missions
│   │   └── future/                # explicitly not-yet-built scope
│   └── standards/                 # CPWD / Schneider reference material
└── README.md
```

## Product Principles

- Standards and project applicability are resolved before compliance conclusions.
- Engineering calculations remain independent of UI, database, and manufacturer catalogs.
- Every input, assumption, formula, result, warning, revision, and approval is traceable.
- Unknown standards editions or amendments block compliance-ready status.
- Approved calculation runs are immutable and reproducible.
- Manufacturer information is consumed through versioned adapters without vendor lock-in.
- Safety-critical calculations require independent engineering review.

## Working On This Repository

Each package/app has its own virtual environment and its own test suite.

```bash
# Core (product-agnostic) package
cd packages/kes_electrical_core
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
pytest

# KES Electrical OS app shell — depends on the core package above
cd apps/kes-electrical-os/backend
python -m venv .venv && . .venv/bin/activate
pip install -e "../../../packages/kes_electrical_core"
pip install -e ".[dev]"
pytest
```

## Development Workflow

1. Implement one complete file or layer.
2. Run its defined validation.
3. Review the result before proceeding.
4. Add automated tests with every functional layer.
5. Commit only after the mission or controlled milestone is complete.
6. Update the master development prompt and README when a mission completes.
7. Keep code and comments in English.

## Verified Status (30 July 2026, post-restructure)

- `packages/kes_electrical_core`: 303 tests passing, 95.98% coverage.
- `apps/kes-electrical-os/backend`: 43 tests passing, 81.26% coverage.
- Combined: 346 tests passing (unchanged from pre-restructure — this was a move, not a
  rewrite).
- Live end-to-end check: PostgreSQL provisioned, Alembic migrations run clean to head,
  the FastAPI server booted, and real calculations (transformer sizing, load demand)
  and real CPWD standard records were exercised through the live API.
- Repository cleaned (30 July 2026): all `__pycache__`, `.ruff_cache`, `.pytest_cache`,
  and `*.egg-info` build artifacts purged; `docs/README-legacy-2026-07-25.md` removed
  as fully superseded by this README + `docs/KESE_Master_Development_Prompt.md` +
  `docs/adr/0003-multi-product-reusable-core.md`. `.gitignore` already excludes all of
  these so they won't reappear once this is a real git repository.
