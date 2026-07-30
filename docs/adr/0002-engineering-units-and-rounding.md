# ADR-0002: Engineering Units, Decimal Arithmetic and Rounding Policy

* **Status:** Accepted with transitional implementation note
* **Date:** 25 July 2026
* **Last reviewed:** 26 July 2026
* **Project:** KES Electrical OS
* **Applies from:** KESE-S1-M2
* **Mandatory for calculation modules from:** KESE engineering calculation phase

## Context

Electrical engineering calculations combine values expressed in different units, scales, and engineering conventions.

Hidden unit assumptions, binary floating-point behaviour, inconsistent conversion factors, and premature rounding can produce results that are:

* Non-repeatable.
* Difficult to audit.
* Incorrect near compliance boundaries.
* Unsafe when used for equipment selection or protection decisions.
* Inconsistent between APIs, databases, reports, and calculation engines.

KES Electrical OS requires deterministic calculations whose inputs, conversions, intermediate values, outputs, tolerances, and displayed values remain traceable.

## Decision

KES Electrical OS will use:

* Explicit engineering units for every dimensional calculation input and output.
* Python `Decimal` for engineering-domain calculations.
* Decimal values constructed from strings, integers, or validated Decimal values.
* Canonical SI-based internal calculation units.
* Centralized and tested unit conversions.
* Unrounded values for engineering comparisons.
* Explicit output quantization using `ROUND_HALF_UP`.
* Module-specific tolerances and rounding policies.
* PostgreSQL `NUMERIC` for persisted engineering calculation values.
* Separate storage of raw calculated values and displayed values where required.

Binary `float` values are prohibited inside the engineering calculation domain core.

## Current Transitional Implementation

The Engineering Units CRUD module was completed under `KESE-S1-M2`.

The current Unit persistence model stores `conversion_factor` using a SQLAlchemy floating-point column.

This is accepted temporarily because:

* The completed module currently acts as a units master-data registry.
* No safety-critical engineering calculation engine currently depends on this field.
* The CRUD milestone validated architecture and persistence flow rather than final calculation precision.

This temporary implementation does not satisfy the final calculation-domain precision policy.

Before any engineering calculation module consumes persisted conversion factors:

1. `conversion_factor` must be migrated from floating-point storage to PostgreSQL `NUMERIC`.
2. The corresponding Pydantic schema must accept and return Decimal-compatible values.
3. Repository and service round-trip tests must confirm exact Decimal preservation.
4. Existing Unit records must be reviewed for conversion accuracy.
5. A controlled Alembic migration must preserve existing values without silent truncation.
6. Calculation code must not convert the value back to Python `float`.

No compliance-sensitive calculation may rely on the current floating-point conversion-factor implementation.

## Canonical Internal Units

| Quantity               | Canonical unit                 | Symbol |
| ---------------------- | ------------------------------ | ------ |
| Voltage                | volt                           | V      |
| Current                | ampere                         | A      |
| Active power           | watt                           | W      |
| Apparent power         | volt-ampere                    | VA     |
| Reactive power         | volt-ampere reactive           | var    |
| Energy                 | watt-hour                      | Wh     |
| Frequency              | hertz                          | Hz     |
| Resistance             | ohm                            | Ω      |
| Reactance              | ohm                            | Ω      |
| Impedance              | ohm                            | Ω      |
| Conductance            | siemens                        | S      |
| Capacitance            | farad                          | F      |
| Inductance             | henry                          | H      |
| Length                 | metre                          | m      |
| Conductor area         | square millimetre              | mm²    |
| Time                   | second                         | s      |
| Temperature            | degree Celsius                 | °C     |
| Temperature difference | kelvin                         | K      |
| Fault current          | ampere                         | A      |
| Short-circuit power    | volt-ampere                    | VA     |
| Power factor           | dimensionless ratio            | 1      |
| Utilization factor     | dimensionless ratio            | 1      |
| Demand factor          | dimensionless ratio            | 1      |
| Diversity factor       | dimensionless ratio            | 1      |
| Coincidence factor     | dimensionless ratio            | 1      |
| Efficiency             | dimensionless ratio            | 1      |
| Percentage             | dimensionless ratio internally | 1      |

Input and display units such as the following must be converted through controlled conversion functions:

* kV and mV.
* kA and mA.
* kW and MW.
* kVA and MVA.
* kvar and Mvar.
* kWh and MWh.
* mΩ.
* km and mm.
* mm².
* minutes and hours.

## Unit Registry Responsibilities

The Engineering Units Registry stores controlled metadata including:

* Unit code.
* Unit name.
* Symbol.
* Engineering quantity.
* Unit system.
* Corresponding SI or canonical unit.
* Conversion factor.
* Base-unit classification.
* Description.
* Remarks.
* Active status.

The Units Registry provides conversion metadata but must not become a substitute for dimensional validation in the calculation domain.

A conversion is valid only when the source and target units represent compatible engineering quantities.

## Decimal Construction

Allowed engineering-domain construction includes:

```python
Decimal("415")
Decimal("0.85")
Decimal("0.001")
Decimal(3)
```

An existing validated `Decimal` value is also permitted.

Prohibited engineering-domain construction includes:

```python
Decimal(0.1)
```

The following are also prohibited:

* Arithmetic using Python `float`.
* Mixing Decimal and float operands.
* Implicit conversion from an unvalidated JSON floating-point value.
* Conversion through float before Decimal construction.
* Use of NaN or infinity.
* Hidden scientific-notation transformations that change stored precision.

External APIs should represent engineering Decimal values as strings when exact reproducibility is required.

Example:

```json
{
  "value": "415.000",
  "unit": "V"
}
```

## Decimal Context

The default engineering calculation context will use:

* Precision of at least 28 significant digits.
* `ROUND_HALF_UP` for declared final quantization.
* Explicit handling of division by zero.
* Explicit handling of invalid operations.
* Rejection of non-finite values.
* No intermediate quantization unless required by the approved calculation method.

Calculation modules may define a higher precision where necessary.

A module must not silently reduce the shared precision.

Constants such as the square root of three must be produced using controlled Decimal arithmetic or stored as approved versioned Decimal constants.

## Factors and Percentages

Power factor, utilization factor, demand factor, coincidence factor, efficiency, and similar values are stored internally as ratios.

Examples:

* 85 percent is stored as `Decimal("0.85")`.
* 5 percent is stored as `Decimal("0.05")`.
* A power factor of 0.90 is stored as `Decimal("0.90")`.
* 100 percent efficiency is stored as `Decimal("1.00")`.

Percentage conversion is an input-boundary or presentation operation.

A percentage must not be applied once as `5` and elsewhere as `0.05`.

Each schema must make the accepted representation unambiguous.

## Conversion Rules

Every conversion function must:

1. Identify the source unit.
2. Identify the target unit.
3. Validate dimensional compatibility.
4. Use a controlled Decimal conversion factor.
5. Preserve the originally entered value and unit.
6. Return the canonical value without display rounding.
7. Reject unknown units.
8. Reject ambiguous symbols.
9. Reject dimensionally incompatible units.
10. Include conversion and boundary tests.

Unit symbols are case-sensitive where case changes the engineering meaning.

Examples include:

* `mA` and `MA`.
* `mV` and `MV`.
* `kW` and `KW`.
* `Hz` and `hz`.

Canonical unit codes should be used internally where display symbols could be ambiguous.

## Conversion-Factor Governance

Every conversion factor must have:

* A unique controlled identifier.
* Source unit.
* Target unit.
* Engineering quantity.
* Decimal factor.
* Factor direction.
* Effective version.
* Source or engineering basis.
* Review status.
* Automated tests.

Reciprocal conversions must not be assumed to be exact unless verified under the approved Decimal context.

Affine conversions, such as temperature conversions involving an offset, must not be represented using only a multiplication factor.

They require a controlled conversion function containing both scale and offset logic.

## Rounding Rules

Engineering calculations follow this sequence:

1. Validate the input value.
2. Validate the input unit.
3. Convert the input to the canonical unit.
4. Perform calculations using controlled Decimal precision.
5. Preserve intermediate values without unnecessary quantization.
6. Evaluate limits, margins, pass states, warnings, and failures using unrounded values.
7. Apply the declared output quantization.
8. Preserve both the raw result and displayed result where required.
9. Record the rounding policy with the calculation run.

A value must never be rounded before it is used in a downstream safety, compliance, capacity, or selection check.

## Equipment Selection Is Not Rounding

Selection of standard equipment sizes is a discrete engineering decision.

Examples include:

* Selecting a standard cable size.
* Selecting a circuit-breaker rating.
* Selecting a transformer capacity.
* Selecting a busbar size.
* Selecting a CT ratio.
* Selecting a capacitor-bank step.
* Selecting a generator rating.

Such decisions must be implemented through approved selection rules and standard-size tables.

They must not be described as mathematical rounding.

The selected value, calculated requirement, engineering margin, governing rule, and available standard options must remain traceable.

## Default Display Precision

The following defaults apply only where a calculation module has not approved a more specific presentation policy:

| Quantity              | Default display                                 |
| --------------------- | ----------------------------------------------- |
| Voltage               | 2 decimal places                                |
| Current               | 2 decimal places                                |
| Active power          | 2 decimal places in selected display unit       |
| Apparent power        | 2 decimal places in selected display unit       |
| Reactive power        | 2 decimal places in selected display unit       |
| Power factor          | 3 decimal places                                |
| Dimensionless factors | 3 decimal places                                |
| Percentage            | 1 decimal place                                 |
| Resistance            | 6 decimal places in Ω                           |
| Reactance             | 6 decimal places in Ω                           |
| Impedance             | 6 decimal places in Ω                           |
| Fault current         | 3 decimal places in kA                          |
| Energy                | 2 decimal places in selected display unit       |
| Length                | 2 decimal places                                |
| Conductor area        | Appropriate standard size or declared precision |
| Time                  | 3 decimal places in selected display unit       |
| Frequency             | 2 decimal places                                |

Displayed values must not replace the unrounded engineering result.

## Tolerances

Every comparison tolerance must be:

* Named.
* Expressed using Decimal.
* Associated with a calculation rule or method.
* Version controlled.
* Included in calculation evidence.
* Covered by lower-boundary tests.
* Covered by upper-boundary tests.
* Covered by exact-edge tests.

A global hidden tolerance is prohibited.

Tolerance values must not be introduced only to make a failing test pass.

## Database Storage

Engineering decimal values will use PostgreSQL `NUMERIC`, not floating-point database types.

Persisted engineering values should retain, where applicable:

* Raw Decimal value.
* Canonical unit.
* Originally entered value.
* Originally entered unit.
* Value source.
* Entered, derived, defaulted, measured, or assumed classification.
* Effective date.
* Revision.
* Precision policy.
* Rounding-policy identifier.
* Formula or method identifier.

Database precision and scale must be selected from the documented range of each field.

Silent truncation is prohibited.

Where different engineering quantities require materially different ranges, they should use separately defined precision and scale rather than one universal database definition.

## API Requirements

Engineering API contracts must:

* Require or explicitly declare units.
* Reject unsupported units.
* Reject incompatible units.
* Reject NaN.
* Reject positive or negative infinity.
* Reject empty numeric strings.
* Reject malformed Decimal strings.
* Reject ambiguous percentage representations.
* Return canonical values where required.
* Return declared display values where required.
* Return warnings when defaults or assumptions are applied.
* Preserve stable Decimal serialization.
* Avoid unintended conversion to binary float.

API validation alone does not replace domain validation.

## Calculation Evidence

Every issued numerical result must be reproducible from:

* Original value.
* Original unit.
* Canonical converted value.
* Conversion-rule version.
* Formula or method identifier.
* Decimal context.
* Intermediate values required for audit.
* Raw output.
* Comparison tolerance.
* Quantized display output.
* Rounding-policy identifier.
* Engine version.
* Rule-set version.

## Testing Requirements

Each engineering quantity and calculation must include:

* Valid conversion tests.
* Incompatible-unit rejection tests.
* Unknown-unit rejection tests.
* Minimum-boundary tests.
* Maximum-boundary tests.
* Decimal-construction tests.
* Float-rejection tests.
* Rounding-midpoint tests.
* Tolerance-edge tests.
* Serialization tests.
* Persistence round-trip tests.
* Golden-reference calculation tests.
* Regression tests for corrected conversion defects.

Conversion factors must be independently verified rather than tested only against the same implementation logic that produced them.

## Implementation Gate for Calculation Modules

Before starting the first safety- or compliance-sensitive calculation module, the following must be complete:

* Decimal engineering value object.
* Controlled unit identifier or unit enumeration.
* Dimensional-compatibility validation.
* Decimal conversion service.
* Float-rejection tests.
* Unit-conversion tests.
* Database `NUMERIC` persistence pattern.
* Stable Decimal API serialization.
* Rounding-policy implementation.
* Tolerance-policy implementation.
* Migration of Unit `conversion_factor` from floating point to `NUMERIC`.

Failure to complete these items blocks calculation-ready status.

## Consequences

### Positive

* Calculations remain deterministic.
* Calculations remain auditable.
* Unit errors are detected at system boundaries.
* Compliance comparisons use full-precision results.
* Reports cannot silently change engineering decisions through formatting.
* Persisted values can round-trip without binary floating-point drift.
* Calculation defects can be reproduced from retained evidence.

### Trade-offs

* Decimal arithmetic requires more code than primitive float arithmetic.
* Explicit units require additional schemas and value objects.
* API clients must send controlled values and units.
* Database precision must be designed for each engineering range.
* Each calculation module must define and test its precision.
* Existing temporary floating-point fields require migration.

## Enforcement

This ADR is enforced through:

* Domain value objects.
* Schema validation.
* Database type reviews.
* Alembic migration reviews.
* Calculation tests.
* API tests.
* Persistence round-trip tests.
* Golden-reference tests.
* Ruff and MyPy checks.
* Coverage gates.
* Engineering review of unit and rounding policies.
