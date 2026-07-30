# KESE-S1-M3 — Engineering Standards CRUD Specification

* **Status:** Completed
* **Version:** 1.0
* **Completion date:** 26 July 2026
* **Project:** KES Electrical OS
* **Mission:** KESE-S1-M3
* **Product capability:** EOS-02 Engineering Standards
* **Milestone commit:** `8ef97ea`

## Objective

Implement a controlled master registry for electrical engineering standards using the established KES Electrical OS backend architecture:

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

The milestone provides CRUD operations for standard metadata and establishes the foundation for future standards governance, project applicability, clause references, amendments, and compliance workflows.

## Implemented Scope

KESE-S1-M3 includes:

* Engineering Standard SQLAlchemy model.
* UUID primary key.
* Created and updated audit timestamps.
* Pydantic create schema.
* Pydantic partial-update schema.
* Pydantic response schema.
* Async SQLAlchemy repository.
* Service layer.
* FastAPI CRUD endpoints.
* API router registration.
* Standard-code uniqueness validation.
* Standard lifecycle-date validation.
* Publication-year range validation.
* PostgreSQL migration.
* Async API test foundation.
* Automated CRUD and validation tests.
* Coverage-gate validation.

## Explicit Exclusions

This milestone does not implement:

* Separate Standards Organization entity.
* Standard Family entity.
* Standard Document entity.
* Standard Edition entity.
* Standard Part entity.
* Amendment or corrigendum entities.
* Clause, table, figure, or annex references.
* Evidence-source or provenance records.
* Project-standard assignment.
* Project applicability matrix.
* Standard precedence workflow.
* Compliance-readiness workflow.
* Standards seed-import process.
* Automatic interpretation of standards.
* Redistribution of protected standards text.
* Automatic statutory, regulatory, contractual, or engineering approval.

These capabilities remain future standards-governance work.

## Engineering Standard Entity

### Table

```text
standards
```

### Identity and Audit Fields

| Field        | Type                    | Requirement |
| ------------ | ----------------------- | ----------- |
| `id`         | UUID                    | Primary key |
| `created_at` | Timestamp with timezone | Required    |
| `updated_at` | Timestamp with timezone | Required    |

### Business Fields

| Field                  | Type                | Requirement         |
| ---------------------- | ------------------- | ------------------- |
| `code`                 | String, maximum 100 | Required and unique |
| `title`                | String, maximum 300 | Required            |
| `issuing_organization` | String, maximum 100 | Required            |
| `category`             | String, maximum 100 | Required            |
| `edition`              | String, maximum 100 | Optional            |
| `publication_year`     | Integer             | Optional            |
| `country`              | String, maximum 100 | Optional            |
| `status`               | String, maximum 30  | Required            |
| `effective_date`       | Date                | Optional            |
| `withdrawn_date`       | Date                | Optional            |
| `scope`                | Text                | Optional            |
| `description`          | Text                | Optional            |
| `reference_url`        | String, maximum 500 | Optional            |
| `remarks`              | Text                | Optional            |
| `is_active`            | Boolean             | Required            |

## Field Definitions

### Code

A controlled human-readable standard identifier.

Examples:

* `IEC 60364-1:2025`
* `IEEE 80-2013`
* `IS 3043:2018`
* `NFPA 70:2026`

The code is unique within the current Engineering Standards Registry.

### Title

The official or controlled descriptive title of the standard.

### Issuing Organization

The recognized organization responsible for issuing or publishing the standard.

Examples include:

* IEC
* IEEE
* BIS
* NFPA
* NEMA
* ISO
* ANSI

The database and API field name is:

```text
issuing_organization
```

### Category

A controlled engineering-subject classification.

Examples include:

* Electrical Installations
* Earthing and Bonding
* Protection
* Switchgear
* Cable Systems
* Lightning Protection
* Power Quality

### Edition

The formal edition label, where known.

Examples:

* `6th Edition`
* `Edition 3.0`
* `2025 Edition`

### Publication Year

The verified year in which the standard or edition was published.

Permitted range:

```text
1800 through 2100
```

### Country

The country or territorial origin associated with the publication.

International standards may use:

```text
International
```

### Status

The lifecycle state of the standard record.

Current API accepts a controlled string with a maximum length of 30 characters.

Typical values include:

* `ACTIVE`
* `CURRENT`
* `DRAFT`
* `WITHDRAWN`
* `SUPERSEDED`

A strict status enumeration is not yet implemented.

### Effective Date

The date from which the standard or edition becomes effective.

### Withdrawal Date

The date on which the standard or edition is withdrawn.

When both lifecycle dates are supplied:

```text
withdrawn_date must be greater than or equal to effective_date
```

### Scope

A non-copyrighted summary describing the systems, voltage levels, equipment, activities, or engineering subjects addressed by the standard.

### Description

Additional controlled information explaining the purpose or intended use of the registry record.

### Reference URL

A link to an official issuing organization, publisher, regulator, or authorized reference source.

A reference URL does not independently verify project applicability.

### Remarks

Additional controlled notes.

Remarks must not be used to hide unstructured compliance rules.

### Active Flag

The Boolean field:

```text
is_active
```

controls whether the record is normally available for new application workflows.

The active flag is separate from lifecycle `status`.

## Database Constraints

### Primary Key

The `id` field is the primary key.

### Unique Standard Code

The standard code must be unique.

Duplicate code creation or update is rejected by the API.

### Publication-Year Constraint

The database permits:

```text
publication_year IS NULL
OR publication_year BETWEEN 1800 AND 2100
```

Constraint name:

```text
ck_standards_publication_year_range
```

### Lifecycle-Date Constraint

The database permits:

```text
withdrawn_date IS NULL
OR effective_date IS NULL
OR withdrawn_date >= effective_date
```

Constraint name:

```text
ck_standards_valid_lifecycle_dates
```

## Database Indexes

The following indexed fields support lookup and ordered retrieval:

* `code`
* `issuing_organization`
* `category`
* `status`

The unique code index also enforces standard-code uniqueness.

## Pydantic Schemas

### StandardCreate

Used to create a new standard.

Characteristics:

* Required core fields.
* Field-length validation.
* Publication-year range validation.
* Whitespace stripping.
* Unexpected fields prohibited.
* Lifecycle-date cross-field validation.

### StandardUpdate

Used for HTTP `PATCH`.

Characteristics:

* All fields optional.
* Only supplied fields are updated.
* Unexpected fields prohibited.
* Field-length validation.
* Publication-year validation.
* Lifecycle-date validation when both dates are supplied.

### StandardResponse

Used for API responses.

Includes:

* All standard business fields.
* UUID.
* Created timestamp.
* Updated timestamp.

The schema supports SQLAlchemy model serialization through Pydantic attribute loading.

## Repository Responsibilities

The async repository provides:

* `create`
* `get_by_id`
* `get_by_code`
* `list`
* `update`
* `delete`

The repository receives an SQLAlchemy `AsyncSession`.

The list operation orders standards by:

1. Issuing organization.
2. Standard code.

The repository contains persistence logic but no HTTP response logic.

## Service Responsibilities

The service provides:

* Standard creation.
* Standard listing.
* UUID retrieval.
* Code lookup.
* Partial-update application.
* Deletion coordination.

The service converts validated Pydantic data into SQLAlchemy model data.

The service does not define HTTP status codes.

## API Resources

Base resource:

```text
/api/v1/standards
```

### Create Standard

```http
POST /api/v1/standards/
```

Successful result:

```text
201 Created
```

Duplicate code result:

```text
409 Conflict
```

### List Standards

```http
GET /api/v1/standards/
```

Successful result:

```text
200 OK
```

### Get Standard by UUID

```http
GET /api/v1/standards/{standard_id}
```

Results:

* `200 OK` when found.
* `404 Not Found` when absent.

### Update Standard

```http
PATCH /api/v1/standards/{standard_id}
```

Results:

* `200 OK` when updated.
* `404 Not Found` when the UUID does not exist.
* `409 Conflict` when changing the code to an existing code.
* `422 Unprocessable Entity` for invalid request data.

### Delete Standard

```http
DELETE /api/v1/standards/{standard_id}
```

Results:

* `204 No Content` when deleted.
* `404 Not Found` when the UUID does not exist.

## API Error Responses

### Duplicate Code

```json
{
  "detail": "Standard code already exists"
}
```

HTTP status:

```text
409 Conflict
```

### Standard Not Found

```json
{
  "detail": "Standard not found"
}
```

HTTP status:

```text
404 Not Found
```

### Schema Validation Failure

Invalid request fields, publication years, field lengths, or lifecycle dates return:

```text
422 Unprocessable Entity
```

## Migration

Migration revision:

```text
c4f1a2b3d4e5
```

Previous revision:

```text
90c8a737dfe4
```

The migration:

* Renamed `organization` to `issuing_organization`.
* Increased code length from 50 to 100.
* Increased edition length from 50 to 100.
* Increased issuing-organization length from 50 to 100.
* Added `scope`.
* Added `reference_url`.
* Added issuing-organization index.
* Added status index.
* Added publication-year constraint.
* Added lifecycle-date constraint.

Current Alembic head:

```text
c4f1a2b3d4e5
```

## Manual CRUD Validation

The following operations were validated against PostgreSQL:

| Operation               | Result         |
| ----------------------- | -------------- |
| Create Standard         | 201 Created    |
| List Standards          | 200 OK         |
| Get Standard by UUID    | 200 OK         |
| Update Standard         | 200 OK         |
| Duplicate Standard code | 409 Conflict   |
| Delete Standard         | 204 No Content |
| Get deleted Standard    | 404 Not Found  |

The expected `409 Conflict` was confirmed without an application traceback.

## Automated Tests

Test file:

```text
backend/tests/api/test_standards.py
```

Shared async fixtures:

```text
backend/tests/conftest.py
```

The test foundation uses:

* pytest
* pytest-asyncio
* HTTPX
* FastAPI ASGI transport
* SQLAlchemy async sessions
* In-memory SQLite through aiosqlite
* Isolated database creation and removal for each test

Implemented tests cover:

* Valid Standard creation.
* Listing Standards.
* UUID retrieval.
* Duplicate-code creation conflict.
* Partial update.
* Duplicate-code update conflict.
* Deletion.
* Retrieval after deletion.
* Unknown UUID operations.
* Invalid lifecycle dates.
* Invalid publication year.

## Automated Validation Result

```text
9 passed
```

Coverage result:

```text
82.04%
```

Required minimum coverage:

```text
80.00%
```

## Quality Gates

The milestone was validated using:

* Python compilation.
* Ruff lint validation.
* pytest.
* pytest coverage.
* Alembic current revision check.
* Alembic head check.
* Alembic schema-difference check.
* Manual PostgreSQL CRUD validation.
* Git diff whitespace validation.

## Security and Copyright Rules

The Engineering Standards Registry stores metadata and controlled summaries.

It must not store or redistribute protected standards text unless:

* A valid license permits storage.
* Access control is implemented.
* Distribution rights are confirmed.

Reference URLs should point to official or authorized sources where possible.

## Future Development

Future standards-governance missions may implement:

* Standards Organization entity.
* Standard Family entity.
* Standard Document entity.
* Standard Edition entity.
* Standard Part entity.
* Amendment and corrigendum entities.
* Clause references.
* Evidence-source records.
* Provenance records.
* Project-standard assignments.
* Applicability decisions.
* Precedence controls.
* Compliance-readiness gates.
* Controlled seed import.
* Soft deletion and audit-history protection.
* Search and filtering.
* Standards lifecycle enumerations.

Future functionality must build on the current Engineering Standard UUID rather than silently replace existing registry records.

## Definition of Done

KESE-S1-M3 is complete because:

* Engineering Standard model is implemented.
* Pydantic schemas are implemented.
* Async repository is implemented.
* Service layer is implemented.
* CRUD API is implemented.
* Router registration is complete.
* Duplicate-code protection is operational.
* Database constraints are implemented.
* Alembic migration reaches database head.
* PostgreSQL CRUD behavior is validated.
* Automated API tests pass.
* Coverage exceeds the required threshold.
* Code is committed.
* Commit is pushed to `origin/master`.

Milestone commit:

```text
8ef97ea — KESE-S1-M3: Complete Engineering Standards CRUD module
```
