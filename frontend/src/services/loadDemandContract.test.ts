import { describe, expect, it } from "vitest";

import { exactDecimalSchema } from "./faultContract";
import {
  AC_POWER_FACTOR_REQUIRED,
  loadCalculationStatusSchema,
  loadScenarioSchema,
  loadWarningCodeSchema,
  phaseSystemSchema,
  powerBasisSchema,
} from "./loadDemandContract";

const DECIMAL_MESSAGE = "Enter a plain number without units, for example 250 or 0.85.";

// Each list below is the backend enum, member for member and in the same order.
// Sources at commit 2a25a8b:
//   backend/app/domain/electrical/loads/models.py:11-16  PhaseSystem
//   backend/app/domain/electrical/loads/models.py:19-28  LoadScenario
//   backend/app/domain/electrical/loads/models.py:31-35  PowerBasis
//   backend/app/domain/electrical/loads/results.py:16-21 CalculationStatus
//   backend/app/domain/electrical/loads/results.py:24-31 LoadWarningCode
// A value the API can send but the contract does not list would be dropped by
// zod and never reach the page, so these lists are pinned rather than trusted.
describe("load and demand controlled vocabularies", () => {
  it("lists every phase system of the backend", () => {
    expect(phaseSystemSchema.options).toEqual([
      "SINGLE_PHASE",
      "THREE_PHASE",
      "DC",
    ]);
  });

  it("lists every load scenario of the backend", () => {
    expect(loadScenarioSchema.options).toEqual([
      "NORMAL",
      "EMERGENCY",
      "OUTAGE",
      "STARTING",
      "UPS",
      "PV",
      "FUTURE",
    ]);
  });

  it("lists every power basis of the backend", () => {
    expect(powerBasisSchema.options).toEqual([
      "ELECTRICAL_INPUT",
      "MECHANICAL_OUTPUT",
    ]);
  });

  it("lists every calculation status of the backend, including REVIEW_REQUIRED", () => {
    expect(loadCalculationStatusSchema.options).toEqual([
      "VALID",
      "WARNING",
      "REVIEW_REQUIRED",
    ]);
  });

  it("lists every load warning code of the backend", () => {
    expect(loadWarningCodeSchema.options).toEqual([
      "ZERO_DEMAND",
      "UTILIZATION_FACTOR_NOT_ESTABLISHED",
      "DEMAND_FACTOR_NOT_ESTABLISHED",
      "EFFICIENCY_NOT_ESTABLISHED",
      "COINCIDENCE_FACTOR_NOT_ESTABLISHED",
    ]);
  });

  it("carries the backend's sentence for a missing AC power factor", () => {
    expect(AC_POWER_FACTOR_REQUIRED).toBe("power_factor is required for AC loads");
  });

  it("rejects a value the backend does not know", () => {
    expect(loadWarningCodeSchema.safeParse("LOW_POWER_FACTOR").success).toBe(false);
    expect(loadCalculationStatusSchema.safeParse("PASS").success).toBe(false);
  });
});

describe("exact decimal values on a load study", () => {
  it.each(["15", "0.85", "0.0001", "415", "1e3"])("accepts %s", (value) => {
    expect(exactDecimalSchema.parse(value)).toBe(value);
  });

  it.each(["", "15 kW", "abc", "0.85%"])("rejects %s", (value) => {
    const parsed = exactDecimalSchema.safeParse(value);

    expect(parsed.success).toBe(false);
    if (!parsed.success) {
      expect(parsed.error.issues.map((issue) => issue.message)).toContain(
        value === "" ? "Decimal value is required." : DECIMAL_MESSAGE,
      );
    }
  });
});
