// @vitest-environment node

import { describe, expect, it } from "vitest";

import {
  cableCheckStatusSchema,
  cableConstructionSchema,
  cableSizingStatusSchema,
  cableReferenceSourceSchema,
  cableWarningCodeSchema,
  circuitSystemSchema,
  conductorArrangementSchema,
  conductorMaterialSchema,
  exactDecimalSchema,
  installationMethodSchema,
  insulationMaterialSchema,
  protectiveConductorTypeSchema,
} from "./cableContract";

describe("cableContract", () => {
  it("preserves exact decimal strings and rejects binary floats", () => {
    expect(exactDecimalSchema.parse("1.500000000")).toBe("1.500000000");
    expect(exactDecimalSchema.safeParse(1.5).success).toBe(false);
  });

  it("matches the backend cable input enum vocabulary", () => {
    expect(conductorMaterialSchema.options).toEqual([
      "COPPER",
      "ALUMINIUM",
    ]);
    expect(insulationMaterialSchema.options).toEqual([
      "PVC",
      "XLPE",
      "EPR",
      "MINERAL",
    ]);
    expect(cableConstructionSchema.options).toEqual([
      "SINGLE_CORE",
      "MULTICORE",
    ]);
    expect(circuitSystemSchema.options).toEqual([
      "DC_TWO_WIRE",
      "SINGLE_PHASE_AC",
      "THREE_PHASE_THREE_WIRE",
      "THREE_PHASE_FOUR_WIRE",
    ]);
    expect(installationMethodSchema.options).toEqual([
      "A1_INSULATED_WALL_CONDUIT",
      "A2_INSULATED_WALL_MULTICORE",
      "B1_WALL_CONDUIT_SINGLE_CORE",
      "B2_WALL_CONDUIT_MULTICORE",
      "C_CLIPPED_DIRECT",
      "D1_GROUND_DUCT",
      "D2_DIRECT_BURIED",
      "E_FREE_AIR_MULTICORE",
      "F_FREE_AIR_TOUCHING_SINGLE_CORE",
      "G_FREE_AIR_SPACED_SINGLE_CORE",
      "CABLE_TRAY",
      "CABLE_LADDER",
      "ENGINEERED_IEC_60287",
    ]);
    expect(conductorArrangementSchema.options).toEqual([
      "MULTICORE",
      "FLAT_TOUCHING",
      "FLAT_SPACED",
      "TREFOIL_TOUCHING",
      "TREFOIL_SPACED",
    ]);
    expect(protectiveConductorTypeSchema.options).toEqual([
      "INTEGRAL_CORE",
      "SEPARATE_INSULATED",
      "SEPARATE_BARE",
      "METALLIC_SCREEN",
      "METALLIC_ARMOUR",
      "NONE",
    ]);
  });

  it("uses canonical design-check statuses without compliance aliases", () => {
    expect(cableCheckStatusSchema.options).toEqual([
      "PASS",
      "FAIL",
      "NOT_APPLICABLE",
    ]);
    expect(cableSizingStatusSchema.options).toEqual([
      "DESIGN_CHECK_PASSED",
      "DESIGN_CHECK_FAILED",
      "NO_STANDARD_SIZE_AVAILABLE",
    ]);
    expect(cableSizingStatusSchema.safeParse("COMPLIANT").success).toBe(false);
    expect(cableSizingStatusSchema.safeParse("NON_COMPLIANT").success).toBe(
      false,
    );
  });

  it("matches the backend cable engineering warning codes", () => {
    expect(cableWarningCodeSchema.options).toEqual([
      "AMPACITY_INADEQUATE",
      "VOLTAGE_DROP_EXCEEDED",
      "SHORT_CIRCUIT_WITHSTAND_INADEQUATE",
      "NEUTRAL_SIZE_INADEQUATE",
      "PROTECTIVE_CONDUCTOR_INADEQUATE",
      "HIGH_TOTAL_DERATING",
      "PARALLEL_CABLE_CURRENT_SHARING",
      "SOIL_DATA_REQUIRED",
      "AMBIENT_DERATING_NOT_ESTABLISHED",
      "GROUPING_DERATING_NOT_ESTABLISHED",
      "GOVERNING_REFERENCE_NOT_ESTABLISHED",
      "GOVERNING_REFERENCE_OVERRIDDEN",
      "NO_STANDARD_SIZE_AVAILABLE",
    ]);
  });

  it("matches the backend cable reference sources", () => {
    expect(cableReferenceSourceSchema.options).toEqual([
      "PROFILE",
      "REQUEST_OVERRIDE",
      "NOT_ESTABLISHED",
    ]);
  });
});
