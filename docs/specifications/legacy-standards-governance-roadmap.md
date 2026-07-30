# KEOS-S1-M1 — Standards Registry & Compliance Matrix Specification

- **Status:** Approved for implementation
- **Version:** 1.0
- **Date:** 25 July 2026
- **Mission:** KEOS-S1-M1
- **Product capability:** EOS-01 Project Configuration

## Objective

Create a controlled standards registry that identifies standards organizations, families, documents, parts, editions, amendments, clause references, evidence sources, project applicability, precedence, verification, and compliance readiness.

No unverified or unknown edition may support a compliance-ready conclusion.

## Scope

The mission includes:

- Standards organizations and publishers.
- Standard families and controlled document identifiers.
- Parts and document subdivisions.
- Exact editions and publication dates.
- Amendments, corrigenda, and correction slips.
- Clause, table, figure, and annex references.
- Evidence-source metadata and provenance.
- Project-standard assignments.
- Project-level applicability and precedence.
- Verification and compliance-readiness states.
- Search, filtering, CRUD, seed import, and applicability matrix.
- Domain, schema, service, persistence, API, and seed-import tests.

## Explicit Exclusions

This mission does not include:

- Redistribution of protected standards text.
- Automatic interpretation of an entire standard.
- Automatic statutory or regulatory approval.
- Electrical load, cable, fault, protection, or earthing calculations.
- Manufacturer product-selection logic.
- Silent replacement of an unknown edition with the latest edition.

## Entity Model

### StandardsOrganization

Represents the issuing or publishing organization.

Required fields:

- `id`: UUID primary key.
- `code`: stable uppercase identifier.
- `name`: official organization name.
- `country_code`: optional ISO country code.
- `website_url`: optional official website.
- `is_active`: controlled availability flag.
- Audit fields.

Examples include IEC, BIS, IEEE, CPWD, CEA, and an authorized project authority.

### StandardFamily

Represents a recognized standards series or document family.

Required fields:

- `id`: UUID primary key.
- `organization_id`: issuing organization reference.
- `code`: controlled family identifier.
- `title`: controlled title.
- `subject`: controlled engineering subject.
- `scope_summary`: non-copyrighted summary.
- `record_status`: lifecycle state.
- Audit fields.

A family identifier alone cannot establish an applicable edition.

### StandardDocument

Represents a specific document or separately issued part within a family.

Required fields:

- `id`: UUID primary key.
- `family_id`: parent family reference.
- `document_number`: official controlled identifier.
- `part_number`: optional part identifier.
- `section_identifier`: optional subdivision.
- `title`: controlled document title.
- `document_type`: standard, code, specification, guide, regulation, or project requirement.
- `record_status`: lifecycle state.
- Audit fields.

### StandardEdition

Represents an issued version of a standard document.

Required fields:

- `id`: UUID primary key.
- `document_id`: parent document reference.
- `edition_label`: official edition or publication-year label.
- `edition_number`: optional edition number.
- `publication_date`: optional verified publication date.
- `effective_date`: optional effective date.
- `withdrawal_date`: optional withdrawal date.
- `edition_confirmed`: explicit Boolean verification gate.
- `verification_status`: controlled verification state.
- `supersedes_edition_id`: optional prior-edition reference.
- `evidence_source_id`: verification evidence reference.
- `record_status`: lifecycle state.
- Audit fields.

An edition with `edition_confirmed = false` cannot become compliance-ready.

### StandardAmendment

Represents an amendment, corrigendum, erratum, addendum, or correction slip.

Required fields:

- `id`: UUID primary key.
- `edition_id`: parent edition reference.
- `amendment_type`: controlled amendment classification.
- `identifier`: official amendment identifier.
- `title`: controlled title or summary.
- `publication_date`: optional verified date.
- `effective_date`: optional effective date.
- `verification_status`: controlled verification state.
- `evidence_source_id`: evidence reference.
- `record_status`: lifecycle state.
- Audit fields.

An amendment cannot exist without a parent edition.

### ClauseReference

Represents a controlled locator within an edition.

Required fields:

- `id`: UUID primary key.
- `edition_id`: governing edition reference.
- `locator_type`: clause, table, figure, annex, note, or schedule.
- `locator`: controlled source locator.
- `subject`: engineering subject.
- `derived_rule_summary`: non-copyrighted structured summary.
- `rule_identifier`: optional stable encoded-rule identifier.
- `verification_status`: verification state.
- `evidence_source_id`: evidence reference.
- `record_status`: lifecycle state.
- Audit fields.

Protected standards text must not be stored unless separately licensed and access-controlled.

### EvidenceSource

Represents the provenance used to verify registry data.

Required fields:

- `id`: UUID primary key.
- `source_type`: official publisher, government source, licensed copy, project document, vendor guide, or secondary reference.
- `title`: controlled evidence title.
- `publisher`: source publisher.
- `source_locator`: URL, document identifier, or controlled storage reference.
- `document_date`: optional source date.
- `acquired_at`: acquisition timestamp.
- `checksum`: optional file checksum.
- `license_status`: controlled licensing classification.
- `verification_status`: verification state.
- `verified_by`: optional reviewer identifier.
- `verified_at`: optional verification timestamp.
- Audit fields.

### ProjectStandardAssignment

Links a project to a selected standard edition and defines its intended use.

Required fields:

- `id`: UUID primary key.
- `project_id`: shared KES project reference.
- `edition_id`: selected edition reference.
- `purpose`: design, installation, equipment, testing, safety, contractual, or reference.
- `jurisdiction`: controlled project jurisdiction.
- `precedence_rank`: positive integer; `1` is the highest precedence.
- `applicability_status`: controlled applicability state.
- `readiness_status`: controlled compliance-readiness state.
- `rationale`: mandatory engineering rationale.
- `effective_from`: project-effective date.
- `effective_to`: optional expiry date.
- `approved_by`: optional authorized reviewer.
- `approved_at`: optional approval timestamp.
- Audit fields.

### ApplicabilityDecision

Records a reviewable applicability decision for a project assignment.

Required fields:

- `id`: UUID primary key.
- `assignment_id`: project-standard assignment reference.
- `scope_type`: project, system, voltage level, area, equipment, or activity.
- `scope_identifier`: stable identifier for the applicable scope.
- `decision`: applicable, not applicable, reference only, or unresolved.
- `rationale`: mandatory decision rationale.
- `evidence_source_id`: optional evidence reference.
- `decided_by`: identified decision owner.
- `decided_at`: decision timestamp.
- `review_status`: pending, reviewed, approved, or rejected.
- Audit fields.

## Controlled Enumerations

### RecordStatus

- `DRAFT`
- `ACTIVE`
- `SUPERSEDED`
- `WITHDRAWN`
- `ARCHIVED`

### VerificationStatus

- `UNVERIFIED`
- `METADATA_VERIFIED`
- `SOURCE_VERIFIED`
- `REJECTED`

### ApplicabilityStatus

- `UNRESOLVED`
- `APPLICABLE`
- `NOT_APPLICABLE`
- `REFERENCE_ONLY`

### ReadinessStatus

- `UNRESOLVED`
- `REFERENCE_ONLY`
- `REVIEW_REQUIRED`
- `COMPLIANCE_READY`

### DocumentType

- `STANDARD`
- `CODE`
- `SPECIFICATION`
- `REGULATION`
- `GUIDE`
- `PROJECT_REQUIREMENT`

### AmendmentType

- `AMENDMENT`
- `CORRIGENDUM`
- `ERRATUM`
- `ADDENDUM`
- `CORRECTION_SLIP`

## Compliance-Readiness Gate

A project-standard assignment may enter `COMPLIANCE_READY` only when:

- The exact standard document is identified.
- The exact edition is identified and confirmed.
- The edition verification status is `SOURCE_VERIFIED`.
- Required amendments and correction slips are resolved.
- Project jurisdiction and purpose are recorded.
- Applicability is `APPLICABLE`.
- Precedence is defined.
- Engineering rationale is present.
- No blocking conflict or unresolved decision remains.
- Authorized review and approval are complete.

Failure of any condition must result in `UNRESOLVED` or `REVIEW_REQUIRED`.

## Data Integrity Constraints

- Organization codes must be unique.
- Family codes must be unique within an organization.
- Document number and part must be unique within a family.
- Edition labels must be unique within a document.
- Amendment identifiers must be unique within an edition.
- Clause locators must be unique within an edition and locator type.
- Project and edition assignments must be unique for the same purpose and effective period.
- Precedence rank must be a positive integer.
- Effective-to dates cannot precede effective-from dates.
- Verified states require verifier identity and verification timestamp.
- Approved states require approver identity and approval timestamp.
- Hard deletion of approved or referenced engineering records is prohibited.

## Initial Seed Import

The existing 16-record baseline will be imported using an idempotent seed process.

The seed importer must:

- Use stable controlled identifiers.
- Preserve supplied titles, families, and status.
- Never infer missing editions.
- Mark unknown editions as unverified and unresolved.
- Retain legacy CPWD records as searchable references.
- Block unverified legacy records from new-project compliance decisions.
- Record source provenance.
- Produce the same database state when run repeatedly.
- Report created, updated, unchanged, rejected, and unresolved counts.

## API Resource Groups

Initial resources:

- `/api/v1/electrical/standards/organizations`
- `/api/v1/electrical/standards/families`
- `/api/v1/electrical/standards/documents`
- `/api/v1/electrical/standards/editions`
- `/api/v1/electrical/standards/amendments`
- `/api/v1/electrical/standards/clauses`
- `/api/v1/electrical/standards/evidence-sources`
- `/api/v1/electrical/projects/{project_id}/standard-assignments`
- `/api/v1/electrical/projects/{project_id}/applicability-matrix`

## Test Requirements

The mission requires:

- Enumeration and state-transition unit tests.
- Required-field and invalid-state schema tests.
- Repository CRUD and uniqueness tests.
- Compliance-readiness gate tests.
- Project precedence and applicability service tests.
- Idempotent seed-import tests.
- API success, validation, conflict, not-found, and filtering tests.
- Migration upgrade and downgrade validation.
- Audit-field and soft-deletion tests.
- Regression tests protecting the controlled seed baseline.

## Definition of Done

KEOS-S1-M1 is complete only when:

- Domain entities and state policies are implemented.
- Pydantic schemas are strict and tested.
- SQLAlchemy models and relationships are implemented.
- Alembic migration reaches database head.
- Repositories and services are implemented.
- Versioned APIs and applicability matrix are operational.
- The 16-record seed is imported idempotently.
- Unknown editions demonstrably block compliance readiness.
- Relevant automated tests pass.
- Architecture, README, changelog, and project status are updated.
