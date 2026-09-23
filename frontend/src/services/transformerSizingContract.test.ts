import { describe, expect, it } from "vitest";

import { loadScenarioSchema } from "./loadDemandContract";
import {
  DEMAND_POWER_FACTOR_REQUIRED,
  NOT_ESTABLISHED_WARNING_CODES,
  transformerRedundancyModeSchema,
  transformerSizingStatusSchema,
  transformerSizingWarningCodeSchema,
} from "./transformerSizingContract";

// Each list below is the backend enum, member for member and in the same order.
// Sources at commit 7853d51:
//   backend/app/domain/electrical/sources/results.py:16-23 TransformerSizingStatus
//   backend/app/domain/electrical/sources/results.py:25-35 TransformerSizingWarningCode
//   backend/app/domain/electrical/sources/results.py:37-45 NOT_ESTABLISHED_WARNING_CODES
//   backend/app/domain/electrical/sources/models.py:14-19  TransformerRedundancyMode
// A value the API can send but the contract does not list would be dropped by
// zod and never reach the page, so these lists are pinned rather than trusted.
describe("transformer sizing controlled vocabularies", () => {
  it("lists every sizing status of the backend, including REVIEW_REQUIRED", () => {
    expect(transformerSizingStatusSchema.options).toEqual([
      "VALID",
      "WARNING",
      "REVIEW_REQUIRED",
      "NO_SOLUTION",
    ]);
  });

  it("lists every warning code of the backend", () => {
    expect(transformerSizingWarningCodeSchema.options).toEqual([
      "DERATING_APPLIED",
      "NO_STANDARD_RATING_AVAILABLE",
      "GROWTH_FACTOR_NOT_ESTABLISHED",
      "DESIGN_MARGIN_NOT_ESTABLISHED",
      "AMBIENT_DERATING_NOT_ESTABLISHED",
      "ALTITUDE_DERATING_NOT_ESTABLISHED",
      "HARMONIC_DERATING_NOT_ESTABLISHED",
    ]);
  });

  it("lists every redundancy mode of the backend", () => {
    expect(transformerRedundancyModeSchema.options).toEqual([
      "NONE",
      "N_PLUS_1",
      "TWO_N",
    ]);
  });

  it("names the five factors that make a result REVIEW_REQUIRED", () => {
    expect([...NOT_ESTABLISHED_WARNING_CODES]).toEqual([
      "GROWTH_FACTOR_NOT_ESTABLISHED",
      "DESIGN_MARGIN_NOT_ESTABLISHED",
      "AMBIENT_DERATING_NOT_ESTABLISHED",
      "ALTITUDE_DERATING_NOT_ESTABLISHED",
      "HARMONIC_DERATING_NOT_ESTABLISHED",
    ]);
    // Every one of them is a code the contract accepts.
    for (const code of NOT_ESTABLISHED_WARNING_CODES) {
      expect(transformerSizingWarningCodeSchema.safeParse(code).success).toBe(true);
    }
  });

  it("rejects the loading codes the backend withdrew (GAP-016)", () => {
    expect(transformerSizingWarningCodeSchema.safeParse("HIGH_LOADING").success).toBe(false);
    expect(transformerSizingWarningCodeSchema.safeParse("LOW_LOADING").success).toBe(false);
  });

  it("reuses the load module's scenario enum unchanged", () => {
    // The backend types both with the same LoadScenario, so a second copy here
    // could drift away from it.
    expect(loadScenarioSchema.options).toContain("NORMAL");
    expect(loadScenarioSchema.options).toHaveLength(7);
  });

  it("carries the backend's field name for a missing demand power factor", () => {
    expect(DEMAND_POWER_FACTOR_REQUIRED).toContain("demand_power_factor");
  });
});
