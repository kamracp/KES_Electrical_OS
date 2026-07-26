# KES Electrical OS — Controlled Domain Glossary

* **Document status:** Controlled foundation
* **Version:** 1.1
* **Original date:** 25 July 2026
* **Last reviewed:** 26 July 2026
* **Project:** KES Electrical OS
* **Applies from:** KESE-S1-M1
* **Current implemented milestones:** KESE-S1-M1 through KESE-S1-M3

## Purpose

This glossary defines the controlled terminology used by KES Electrical OS across:

* Domain code.
* Database models.
* Pydantic schemas.
* Repositories.
* Services.
* APIs.
* Engineering calculations.
* Reports.
* Automated tests.
* Engineering reviews.
* Approval records.

Controlled terms must not be renamed, combined, or used with a materially different meaning without an approved architecture or engineering decision.

Database fields, API resources, calculation outputs, reports, and tests should use the terminology defined in this document.

## Naming Conventions

### KES

Kamra Engineering Solutions.

### KES Electrical OS

The electrical engineering software platform developed by Kamra Engineering Solutions.

### KESE

The controlled development-mission prefix for KES Electrical OS.

Examples:

* `KESE-S1-M1`
* `KESE-S1-M2`
* `KESE-S1-M3`

### EOS

The product-module identifier prefix used to classify functional electrical-engineering capabilities.

Examples:

* `EOS-02` — Engineering Standards.
* `EOS-03` — Engineering Units.
* `EOS-04` — Load and Demand.

### Milestone

A controlled development scope that produces a defined, validated, and committed software capability.

A milestone should include:

* Defined scope.
* Implemented files.
* Validation evidence.
* Database migration where required.
* Automated tests where required.
* Git commit.
* Remote repository synchronization.

## Common Persistence Terms

### Entity

A persistent business record with a stable identity.

Examples include:

* Engineering Standard.
* Engineering Unit.
* Project.
* Load.
* Calculation Run.

### UUID

A universally unique identifier used as the primary identifier for persistent KES Electrical OS entities.

UUIDs must not be replaced by user-facing codes.

### Code

A controlled, human-readable identifier assigned to a business record.

Examples:

* `IEC 60364-1:2025`
* `V`
* `kW`

A code may be unique within its registry, but it is not a replacement for the entity UUID.

### Created At

The audit timestamp recording when a persistent entity was created.

### Updated At

The audit timestamp recording the most recent persisted update to an entity.

### Active Flag

A Boolean application-level control indicating whether a record may normally be used in new workflows.

The field is generally represented as:

```text
is_active
```

An inactive record may remain in the database for history, audit, or reference.

The active flag is not the same as a lifecycle status.

### Lifecycle Status

A controlled state describing the business or regulatory condition of a record.

Examples include:

* `ACTIVE`
* `CURRENT`
* `DRAFT`
* `WITHDRAWN`
* `SUPERSEDED`

Lifecycle status and `is_active` must not be treated as interchangeable fields.

## Engineering Standards Registry

### Engineering Standard

A controlled master record representing an electrical engineering standard, code, recommended practice, regulatory document, or recognized technical publication.

The current Engineering Standard record includes:

* Code.
* Title.
* Issuing organization.
* Category.
* Edition.
* Publication year.
* Country.
* Lifecycle status.
* Effective date.
* Withdrawal date.
* Scope.
* Description.
* Reference URL.
* Remarks.
* Active flag.
* UUID and audit timestamps.

### Standard Code

The controlled human-readable identifier of an Engineering Standard.

Examples:

* `IEC 60364-1:2025`
* `IEEE 80-2013`
* `IS 3043:2018`
* `NFPA 70:2026`

The exact code format is determined by the issuing organization.

Within the current Engineering Standards Registry, the standard code is unique.

### Standard Title

The official or controlled descriptive title of an Engineering Standard.

The title does not replace the standard code.

### Issuing Organization

The recognized organization responsible for issuing, maintaining, or publishing an Engineering Standard.

Examples include:

* IEC.
* IEEE.
* BIS.
* NFPA.
* NEMA.
* ISO.
* ANSI.

The controlled database and API field is:

```text
issuing_organization
```

The terms `organization`, `issuing body`, and `publisher` must not be used as field-name substitutes without an approved model change.

### Standard Category

A controlled classification describing the principal engineering subject of a standard.

Examples include:

* Electrical Installations.
* Earthing and Bonding.
* Protection.
* Switchgear.
* Cable Systems.
* Lightning Protection.
* Power Quality.
* Rotating Equipment.
* Industrial Control.

A category assists filtering and organization but does not determine project applicability by itself.

### Standard Family

A recognized standards series or publication family.

Examples include:

* IEC 60364.
* IEC 60947.
* IS 3043.
* IEEE 80.

A standard family alone is not sufficient for a compliance conclusion.

### Standard Document

A controlled publication record belonging to a standard family.

It identifies the issuing organization, document number, title, publication type, and provenance.

In the current CRUD implementation, an Engineering Standard record may represent the controlled master entry for a standard document.

Future standards-governance modules may separate:

* Standard family.
* Standard document.
* Standard edition.
* Standard part.
* Amendment.
* Clause reference.

### Part

A separately identified subdivision of a standard family or publication.

Applicability must be resolved at part level whenever different parts govern different engineering subjects.

### Edition

The formally issued version of a standard document.

The exact edition must be known before the document can govern a compliance conclusion.

Edition may be represented by text such as:

* `6th Edition`
* `Edition 3.0`
* `2025 Edition`

Edition and publication year are related but are not always identical.

### Publication Year

The calendar year in which a standard edition or controlled publication was issued.

Publication year must not be assumed from the standard code unless the issuing organization’s format makes it explicit and the value is verified.

### Country

The country or territorial origin associated with a standard or regulatory publication.

For international standards, a controlled value such as `International` may be used.

Country does not determine project applicability by itself.

### Effective Date

The date from which a standard, edition, rule, or project requirement becomes effective.

### Withdrawal Date

The date on which a standard or edition ceased to be current or available for new application.

A withdrawal date must not be earlier than the effective date.

### Standard Scope

A controlled summary describing the systems, equipment, voltage ranges, activities, or engineering subjects addressed by the standard.

The scope is not a substitute for the authorized publication.

### Standard Description

Additional controlled information explaining the purpose or intended use of the Engineering Standard record.

### Reference URL

A controlled web reference to an official publisher, issuing organization, government source, or authorized evidence location.

A reference URL does not prove that the referenced edition is applicable to a project.

### Standard Remarks

Additional controlled notes associated with an Engineering Standard record.

Remarks must not contain hidden engineering rules that belong in a controlled rule or applicability record.

### Amendment

A formally issued change to a specific standard edition.

An amendment cannot exist independently of its parent standard edition.

### Correction Slip

An official correction, erratum, or corrigendum that modifies or clarifies an issued publication without silently replacing its edition.

### Clause Reference

A controlled reference to a clause, table, figure, annex, or other identifiable location within a standard document.

Protected clause text must not be redistributed unless legally authorized.

### Clause Rule

A structured engineering or compliance rule derived from an authorized source.

A Clause Rule should retain:

* Method.
* Parameters.
* Applicability.
* Source reference.
* Effective status.
* Rule version.
* Review state.

### Evidence Source

The official, licensed, government, publisher, utility, or controlled project source used to verify:

* Standard.
* Edition.
* Amendment.
* Clause reference.
* Applicability decision.
* Engineering rule.

### Provenance

The traceable origin of a record.

Provenance may include:

* Source type.
* Source identifier.
* Document location.
* Acquisition date.
* Effective date.
* Verification status.
* Reviewer.
* License or access basis.

### Jurisdiction

The country, state, authority, utility, client, contract, regulator, or legal environment that determines which requirements apply to a project.

### Applicability

The controlled decision describing whether a standard or rule governs a specific:

* Project.
* Location.
* Voltage level.
* Electrical system.
* Equipment type.
* Design activity.
* Operating scenario.

### Precedence

The approved order used to resolve overlapping or conflicting requirements.

Precedence is assigned at project level and must not be assumed globally.

### Project Standard Assignment

The controlled link between a project and an applicable:

* Standard.
* Edition.
* Amendment.
* Part.
* Purpose.
* Precedence.
* Applicability state.
* Approval state.

## Engineering Units Registry

### Engineering Unit

A controlled master record representing a unit used for an engineering quantity.

The current Engineering Unit record includes:

* Code.
* Name.
* Symbol.
* Engineering quantity.
* Unit system.
* Corresponding SI unit.
* Conversion factor.
* Base-unit flag.
* Description.
* Remarks.
* Active flag.
* UUID and audit timestamps.

### Unit Code

A controlled human-readable identifier for an Engineering Unit.

The Unit Code is unique within the Engineering Units Registry.

A Unit Code should remain stable after use in calculations or persisted engineering records.

### Unit Name

The descriptive name of an Engineering Unit.

Examples include:

* Volt.
* Ampere.
* Kilowatt.
* Millimetre.
* Ohm.

### Unit Symbol

The conventional short representation of an Engineering Unit.

Examples include:

* `V`
* `A`
* `kW`
* `mm`
* `Ω`

Symbols may be case-sensitive.

A display symbol must not be used as the only internal identifier where ambiguity is possible.

### Engineering Quantity

The physical or engineering property measured by a unit.

Examples include:

* Voltage.
* Current.
* Active Power.
* Apparent Power.
* Energy.
* Resistance.
* Length.
* Conductor Area.
* Time.
* Temperature.

Units may be converted only when they represent compatible engineering quantities.

### Unit System

The controlled measurement system associated with an Engineering Unit.

Examples include:

* SI.
* Metric.
* Imperial.
* Industry-specific controlled system.

The current default Unit System is `SI`.

### SI Unit

The controlled SI or canonical reference unit to which a unit is related.

Examples include:

* Volt for voltage.
* Ampere for current.
* Watt for active power.
* Metre for length.

The database field is currently named:

```text
si_unit
```

### Conversion Factor

The controlled numerical factor used to convert a unit to its defined SI or canonical reference unit when the conversion is purely multiplicative.

Conversion factors must be governed by ADR-0002.

A conversion factor must not be used for an affine conversion requiring an offset.

Temperature conversions such as Celsius to Fahrenheit require a controlled conversion method rather than only a multiplication factor.

### Base Unit

The unit selected as the canonical or principal unit for a defined engineering quantity within a controlled unit system.

The current Boolean field is:

```text
is_base_unit
```

Only an approved unit-governance rule should determine which unit is the base unit for a quantity.

### Unit Conversion

The controlled transformation of a value from one compatible Engineering Unit to another.

A valid conversion must retain:

* Original value.
* Original unit.
* Target unit.
* Conversion rule.
* Converted value.
* Precision context.

### Canonical Unit

The controlled internal unit used by an engineering calculation engine for a particular quantity.

The canonical unit may correspond to the registered SI unit.

### Dimensional Compatibility

The rule that permits conversion or comparison only between units representing compatible engineering quantities.

Examples:

* Volts may be converted to kilovolts.
* Amperes may be converted to milliamperes.
* Kilowatts must not be converted to amperes without a separate engineering formula and required electrical inputs.

## Compliance States

### UNRESOLVED

Applicability, edition, amendment, evidence, jurisdiction, or another governing input is incomplete.

This state blocks a compliance-ready conclusion.

### REFERENCE_ONLY

The record provides useful engineering guidance but is not a governing project requirement.

### DESIGN_CHECK_PASSED

The encoded engineering check passed for the supplied inputs and scenario.

This state is not statutory, contractual, client, or regulatory approval.

### REVIEW_REQUIRED

Conflicting requirements, missing evidence, warnings, exceptions, or engineering judgement require an identified reviewer.

### COMPLIANCE_CONFIRMED

The governing evidence, design response, independent review, and authorized approval are complete.

### SUPERSEDED

A newer controlled revision replaced the record.

The superseded record remains available in audit history.

### WITHDRAWN

The issuing organization has withdrawn the standard or edition.

A withdrawn standard may remain available for historical projects but must not automatically govern new projects.

### CURRENT

The record is considered current within its controlled registry context.

`CURRENT` does not independently prove project applicability.

### ACTIVE

The record is in an active lifecycle state.

`ACTIVE` must not be confused with the Boolean `is_active` application flag.

## Project and Engineering Model

### Project

The controlled engineering work scope for a client, plant, building, site, system, or facility.

### Design Basis

The approved collection of:

* Project constraints.
* Voltage.
* Frequency.
* Earthing arrangement.
* Environmental conditions.
* Utility data.
* Applicable standards.
* Operating scenarios.
* Assumptions.
* Design criteria.

### Operating Scenario

A named operating condition against which calculations are executed.

Examples include:

* Normal utility operation.
* Emergency generator operation.
* Source outage.
* Motor starting.
* UPS operation.
* Maximum fault.
* Minimum fault.
* Future expansion.

### Network Revision

An immutable version of the electrical network configuration containing:

* Sources.
* Buses.
* Feeders.
* Loads.
* Connections.
* Protection devices.
* Scenario-specific states.

### Assumption

An explicitly recorded engineering input used when verified project data is unavailable.

An assumption must include:

* Rationale.
* Owner.
* Effective scope.
* Review status.
* Replacement condition.
* Expiry condition where applicable.

### Warning

A non-silent calculation, compliance, or data-quality condition requiring attention.

A blocking warning prevents approval or compliance confirmation.

### Approval

An authorized decision accepting a controlled engineering record or calculation.

A calculation cannot approve itself.

### Reviewer

An identified person authorized to evaluate engineering evidence, assumptions, warnings, calculations, or compliance conclusions.

## Load and Demand

### Load

An electrical consumer represented by relevant attributes such as:

* Active power.
* Apparent power.
* Reactive power.
* Phase.
* Voltage.
* Power factor.
* Duty.
* Criticality.
* Operating scenario.

### Connected Load

The total installed rated load before utilization, demand, coincidence, diversity, operating duty, or future allowance is applied.

### Utilization Factor

The expected operating load divided by rated or connected load for the defined scope and scenario.

It is normally expressed as a ratio between zero and one.

### Coincidence Factor

The coincident maximum demand of a group divided by the sum of individual maximum demands.

It is normally less than or equal to one.

### Diversity Factor

The sum of individual maximum demands divided by the coincident maximum demand of the group.

It is normally greater than or equal to one.

Coincidence factor and diversity factor are reciprocal concepts only for the same defined population and time basis.

They must not both be applied to the same aggregation step.

### Demand Factor

The maximum demand divided by connected load for the same defined system and time basis.

### Future Allowance

An approved additional capacity included for identified future expansion.

Future Allowance must not be hidden inside utilization, coincidence, diversity, or demand factors.

### Design Demand

The calculated project demand for a defined scenario after applying approved:

* Factors.
* Duty rules.
* Scenario rules.
* Future allowance.

## Sources and Network

### Source

A device or system capable of energizing the electrical network.

Examples include:

* Utility supply.
* Transformer.
* Generator.
* UPS.
* Battery system.
* PV system.
* Inverter.

### Bus

A network node at a defined voltage level connecting sources, feeders, panels, or loads.

### Feeder

A controlled electrical connection supplying a downstream:

* Bus.
* Panel.
* Equipment item.
* Load group.

### Protection Device

A device used to detect or interrupt abnormal electrical conditions.

Examples include:

* ACB.
* MCCB.
* MCB.
* Fuse.
* RCD.
* RCBO.
* Protection relay.

### Cable Run

A cable or parallel-cable installation with defined:

* Conductor.
* Insulation.
* Installation method.
* Route.
* Length.
* Grouping.
* Ambient condition.
* Derating data.

## Calculation Governance

### Calculation Run

An immutable execution record containing:

* Inputs.
* Units.
* Input sources.
* Scenario.
* Network revision.
* Engine version.
* Rule-set snapshot.
* Formulas.
* Assumptions.
* Warnings.
* Outputs.
* Review status.
* Approval status.

### Engine Version

The controlled software version of the calculation implementation used for a Calculation Run.

### Rule-Set Snapshot

The immutable collection of:

* Standards-derived rules.
* Standard editions.
* Amendments.
* Project applicability decisions.
* Calculation configuration.

### Formula Identifier

A stable controlled identifier representing the formula or calculation method used to produce a result.

### Golden Reference Case

An independently reviewed worked example containing:

* Controlled inputs.
* Expected outputs.
* Tolerances.
* Calculation method.
* Evidence source.

### Deterministic Calculation

A calculation that produces the same controlled result for the same:

* Inputs.
* Units.
* Rules.
* Engine version.
* Decimal context.
* Rounding policy.

### Engineering Margin

The quantified difference or ratio between:

* Calculated duty and allowable capacity.
* Calculated duty and selected rating.
* Calculated value and governing limit.

### Raw Result

The unrounded engineering result produced by the controlled calculation method.

### Display Result

The quantized or formatted result presented to a user or report.

A Display Result must not replace the Raw Result used for engineering decisions.

### Tolerance

A named and version-controlled numerical allowance used for comparison, acceptance, or boundary evaluation.

A hidden global tolerance is prohibited.

## API and CRUD Terms

### Create

The operation that creates and persists a new entity.

Typical successful HTTP status:

```text
201 Created
```

### List

The operation that returns a collection of entities.

Typical successful HTTP status:

```text
200 OK
```

### Get by UUID

The operation that retrieves one entity using its UUID.

Typical results:

* `200 OK` when found.
* `404 Not Found` when absent.

### Partial Update

The operation that modifies only fields supplied by the client.

The current API uses HTTP `PATCH`.

### Delete

The operation that removes an entity from the active persistent registry.

Typical successful HTTP status:

```text
204 No Content
```

Future audit-controlled records may use retirement, withdrawal, or soft deletion instead of physical deletion.

### Conflict

A request that cannot be completed because it violates a uniqueness or state rule.

Duplicate Engineering Standard codes currently return:

```text
409 Conflict
```

### Validation Error

A request rejected because supplied data does not satisfy the API schema or cross-field validation rules.

Typical HTTP status:

```text
422 Unprocessable Entity
```

## Current Milestones

### KESE-S1-M1

Backend and Database Foundation.

Status: Completed.

### KESE-S1-M2

Engineering Units CRUD.

Status: Completed.

Milestone commit:

```text
b78fa26
```

### KESE-S1-M3

Engineering Standards CRUD.

Status: Completed.

Milestone commit:

```text
8ef97ea
```

## Governance Rule

Database fields, API resources, domain classes, calculation outputs, reports, tests, and approval records must use these controlled terms.

Any proposed terminology change requires impact review across:

* Persisted data.
* Database migrations.
* APIs.
* Pydantic schemas.
* Calculation engines.
* Reports.
* Automated tests.
* Existing approved records.
* External integrations.
