# ADR-0001: Standards-First Layered Modular Architecture

* **Status:** Accepted
* **Date:** 25 July 2026
* **Last reviewed:** 26 July 2026
* **Project:** KES Electrical OS
* **Decision owners:** Kamra Engineering Solutions

## Context

KES Electrical OS must support traceable electrical engineering calculations, standards governance, engineering units, project configuration, equipment selection, reports, approvals, and commissioning evidence.

The engineering calculation core must remain independent of web frameworks, database libraries, user interfaces, and manufacturer-specific catalogs.

The initial implementation requires a practical backend structure that supports controlled incremental development while preserving a clear path toward a dedicated engineering domain core.

## Decision

KES Electrical OS will begin as a layered modular monolith with explicit electrical-engineering boundaries.

The backend will use the following implementation flow:

```text
Model
  ↓
Schema
  ↓
Repository
  ↓
Service
  ↓
API
  ↓
Router Registration
  ↓
Alembic Migration
  ↓
Automated Tests
```

As calculation modules are introduced, pure engineering logic will be placed in a separate domain layer that remains independent of FastAPI, SQLAlchemy, PostgreSQL, and frontend code.

## Architecture Layers

### 1. Domain Layer

The domain layer will contain:

* Pure Python engineering entities and value objects.
* Electrical calculation engines.
* Decimal arithmetic for deterministic calculations.
* Explicit engineering units and conversion rules.
* Rounding, tolerance, warning, and result-state policies.
* Standards-derived engineering rules.
* No imports from FastAPI, SQLAlchemy, PostgreSQL, or frontend code.

This layer will become mandatory when engineering calculation missions begin.

### 2. Schema Layer

The schema layer uses Pydantic v2 for:

* API request validation.
* API response serialization.
* Field-length and range validation.
* Cross-field business validation.
* Strict handling of unexpected request fields.
* Conversion between API data and application objects.

Schemas must not contain database transaction logic.

### 3. Repository Layer

The repository layer provides:

* Async SQLAlchemy database operations.
* Entity creation and persistence.
* UUID-based retrieval.
* Unique-code lookup.
* Stable list ordering.
* Update persistence.
* Delete operations.

Repositories receive an SQLAlchemy `AsyncSession`.

Repositories must not contain HTTP response logic.

### 4. Service Layer

The service layer provides:

* Application use-case orchestration.
* Business-rule execution.
* Conversion of validated schemas into persistence models.
* Partial-update handling.
* Coordination between API and repository layers.
* Future integration with pure domain calculation engines.

Services must remain independent of HTTP status codes.

### 5. Persistence Layer

The persistence layer uses:

* PostgreSQL as the production database.
* SQLAlchemy 2.x.
* Async SQLAlchemy sessions.
* UUID primary keys.
* Audit timestamps.
* Alembic-controlled migrations.
* Database constraints and indexes.
* Repository-based data access.

Approved calculation runs will be immutable when calculation-run modules are introduced.

### 6. API Layer

The API layer uses FastAPI and provides:

* Versioned REST endpoints.
* Dependency-injected async database sessions.
* Strict request and response validation.
* Consistent HTTP status codes.
* UUID resource identifiers.
* Duplicate-record conflict responses.
* Resource-not-found responses.
* OpenAPI and Swagger documentation.

API endpoints may coordinate services but must not implement direct SQL queries.

### 7. Presentation and Integration Layer

The planned presentation and integration layer includes:

* React.
* TypeScript.
* Vite.
* Controlled DOCX, PDF, Excel, and CSV reporting.
* Manufacturer-data adapters.
* CAD and BIM integrations.
* BMS, SCADA, and IoT integrations.

Manufacturer-specific data must remain outside core engineering formulas.

## Dependency Direction

Dependencies must point toward controlled business logic:

* API depends on services and schemas.
* Services depend on repositories, schemas, and domain logic.
* Repositories depend on SQLAlchemy models and sessions.
* Models depend only on shared database infrastructure.
* Domain calculation code must not depend on API, persistence, reporting, or UI code.
* Manufacturer adapters must not introduce vendor-specific assumptions into engineering formulas.

Circular imports between layers are not permitted.

## Database Conventions

All persistent engineering entities should use:

* UUID primary keys.
* `created_at` timestamps.
* `updated_at` timestamps.
* Explicit nullable declarations.
* Named database constraints.
* Controlled indexes.
* Alembic migrations.
* PostgreSQL-compatible data types.

Database changes must not be made manually without a corresponding migration.

## Standards Governance

Every compliance-sensitive result must eventually retain:

* Governing standard and standard family.
* Issuing organization.
* Exact edition and publication year.
* Applicable amendment or part.
* Project jurisdiction.
* Applicability decision.
* Clause or controlled engineering-rule reference.
* Evidence source and provenance.
* Review and approval status.

Unknown or unverified editions must block compliance-ready conclusions.

Protected standards text will not be redistributed. The system will store controlled metadata, references, derived engineering rules, project applicability, and licensed-source provenance.

## Engineering Units Governance

Engineering calculations must use controlled units.

The Engineering Units Registry stores:

* Unit code.
* Unit name.
* Symbol.
* Engineering quantity.
* Unit system.
* Corresponding SI unit.
* Conversion factor.
* Base-unit status.
* Description and remarks.
* Active status.

Calculation modules must not use unexplained unit conversions or hidden conversion factors.

## Calculation Governance

Every future calculation run must record:

* Project identifier.
* Scenario identifier.
* Input revision.
* Engine version.
* Rule-set version.
* Input values and units.
* Input source and confidence.
* Formula or method identifier.
* Assumptions.
* Tolerances.
* Warnings.
* Output values and units.
* Engineering margins.
* Result state.
* Review status.
* Approval status.
* Report reference.

Approved runs will be immutable.

Recalculation will create a new linked revision rather than overwrite previously approved engineering evidence.

## Current Implementation Status

### KESE-S1-M1 — Backend and Database Foundation

**Status:** Completed

Implemented:

* FastAPI application foundation.
* PostgreSQL configuration.
* SQLAlchemy 2.x.
* AsyncSession infrastructure.
* Pydantic v2.
* Alembic.
* UUID primary-key mixin.
* Audit timestamp mixin.
* API health and version endpoints.
* Application logging.

### KESE-S1-M2 — Engineering Units CRUD

**Status:** Completed

Implemented:

* Engineering Unit model.
* Schemas.
* Repository.
* Service.
* API endpoints.
* Router registration.
* Alembic migration.
* PostgreSQL CRUD validation.

Milestone commit:

```text
b78fa26 — KESE-S1-M2: Complete Engineering Units CRUD module
```

### KESE-S1-M3 — Engineering Standards CRUD

**Status:** Completed

Implemented:

* Engineering Standard model.
* Standards lifecycle fields.
* Pydantic schemas.
* Repository.
* Service.
* API endpoints.
* Duplicate-code protection.
* Alembic migration.
* Async API test foundation.
* Automated API tests.

Milestone commit:

```text
8ef97ea — KESE-S1-M3: Complete Engineering Standards CRUD module
```

## Product Module Boundaries

Product capabilities are planned as:

| ID     | Module                        |
| ------ | ----------------------------- |
| EOS-01 | Project Configuration         |
| EOS-02 | Engineering Standards         |
| EOS-03 | Engineering Units             |
| EOS-04 | Load and Demand               |
| EOS-05 | Transformer, DG, UPS and PV   |
| EOS-06 | Short-Circuit and Earth-Fault |
| EOS-07 | Protection Coordination       |
| EOS-08 | Cable Sizing                  |
| EOS-09 | Panels and IEC 61439          |
| EOS-10 | Earthing and Bonding          |
| EOS-11 | Lightning Protection          |
| EOS-12 | Surge Protection              |
| EOS-13 | Power Factor and Harmonics    |
| EOS-14 | Cable Tray and Routing        |
| EOS-15 | Engineering Deliverables      |
| EOS-16 | FAT, SAT and Commissioning    |
| EOS-17 | Metering, BMS, SCADA and IoT  |

Development missions use the `KESE` prefix.

## Consequences

### Positive

* Backend modules follow a consistent implementation pattern.
* Database access remains isolated inside repositories.
* Business workflows remain isolated inside services.
* API behavior can be tested independently.
* Engineering calculations can later be independently tested and reused.
* Standards and calculation evidence remain auditable.
* Module boundaries support future service extraction when justified.
* Manufacturer integrations cannot silently change core engineering calculations.

### Trade-offs

* Layer boundaries require additional files and tests.
* Database models cannot become calculation engines.
* Domain objects may differ from persistence models.
* Compliance workflows require controlled standards data.
* Future service extraction will require explicit implementation work.
* Calculation modules will require stricter Decimal and unit-handling rules than CRUD modules.

## Enforcement

This decision is enforced through:

* One-file-at-a-time implementation.
* Compile validation.
* Ruff lint checks.
* Pydantic schema validation.
* Repository and service separation.
* API tests.
* Persistence tests.
* Alembic migration checks.
* Coverage requirements.
* Standards-edition compliance gates.
* Future immutable calculation-run policies.
* Independent review of safety-critical calculations.

## Controlled Development Workflow

Every module should follow this sequence:

1. Inspect the repository and database state.
2. Design the domain model.
3. Implement one complete file at a time.
4. Validate each file before continuing.
5. Create and review the Alembic migration.
6. Apply the migration to PostgreSQL.
7. Validate CRUD or calculation behavior.
8. Add automated tests.
9. Run compilation, lint, tests, coverage, and migration checks.
10. Review staged files.
11. Commit and push after milestone completion.

## Review Triggers

Review this ADR when:

* A calculation module requires a dedicated pure domain package.
* A module requires independent scaling or deployment.
* An integration requires a separate security boundary.
* Operational evidence supports extracting a separate service.
* The domain dependency direction can no longer be maintained.
* A new persistence technology is proposed.
* Safety or compliance requirements require stronger architectural controls.
