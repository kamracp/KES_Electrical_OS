import { describe, expect, it } from "vitest";

import { shortCircuitStudyRequestSchema } from "./fault";
import {
  exactDecimalSchema,
  faultBranchTypeSchema,
  faultSourceTypeSchema,
  faultTypeSchema,
  neutralEarthingModeSchema,
  shortCircuitCaseSchema,
  sourceRepresentationSchema,
} from "./faultContract";

const DECIMAL_MESSAGE = "Enter a plain number without units, for example 250 or 0.85.";

// Schema-shape fixture only: a two-bus network as Fault UI v2 will send it.
// The figures prove nothing about engineering results.
function bus(code: string) {
  return {
    code,
    name: `Bus ${code}`,
    nominal_voltage_v: "415",
    voltage_factor_max: "1.10",
    voltage_factor_min: "0.95",
    neutral_earthing_mode: "SOLIDLY_EARTHED",
  };
}

const network = {
  code: "SC-NET-01",
  name: "Two-bus network",
  calculation_case: "MAXIMUM",
  fault: { bus_code: "DB-01", fault_type: "THREE_PHASE" },
  buses: [bus("MSB-01"), bus("DB-01")],
  sources: [
    {
      code: "TX-01",
      name: "Transformer TX-01",
      bus_code: "MSB-01",
      source_type: "UTILITY_GRID",
      representation: "VOLTAGE_BEHIND_IMPEDANCE",
      positive_sequence_impedance: { resistance_ohm: "0.00087", reactance_ohm: "0.00709" },
    },
    {
      code: "M-01",
      name: "Motor group",
      bus_code: "DB-01",
      source_type: "ASYNCHRONOUS_MOTOR",
      representation: "CURRENT_INJECTION",
      current_contribution_ka: "1.2",
    },
  ],
  branches: [
    {
      code: "CBL-01",
      name: "Feeder to DB-01",
      from_bus_code: "MSB-01",
      to_bus_code: "DB-01",
      branch_type: "CABLE",
      positive_sequence_impedance: { resistance_ohm: "0.0124", reactance_ohm: "0.0080" },
      parallel_circuits: 2,
    },
  ],
};

describe("fault contract enums", () => {
  // Verbatim mirror of backend/app/domain/electrical/fault/fault_models.py.
  it.each<[string, readonly string[], string[]]>([
    [
      "FaultType",
      faultTypeSchema.options,
      ["THREE_PHASE", "TWO_PHASE", "TWO_PHASE_TO_EARTH", "SINGLE_PHASE_TO_EARTH"],
    ],
    ["ShortCircuitCase", shortCircuitCaseSchema.options, ["MAXIMUM", "MINIMUM"]],
    [
      "FaultSourceType",
      faultSourceTypeSchema.options,
      [
        "UTILITY_GRID",
        "SYNCHRONOUS_GENERATOR",
        "ASYNCHRONOUS_MOTOR",
        "INVERTER_BASED_RESOURCE",
        "EQUIVALENT_SOURCE",
      ],
    ],
    [
      "SourceRepresentation",
      sourceRepresentationSchema.options,
      ["VOLTAGE_BEHIND_IMPEDANCE", "CURRENT_INJECTION"],
    ],
    [
      "FaultBranchType",
      faultBranchTypeSchema.options,
      ["CABLE", "OVERHEAD_LINE", "TRANSFORMER", "BUSBAR", "BUSDUCT", "REACTOR", "EQUIVALENT"],
    ],
    [
      "NeutralEarthingMode",
      neutralEarthingModeSchema.options,
      ["SOLIDLY_EARTHED", "RESISTANCE_EARTHED", "REACTANCE_EARTHED", "RESONANT_EARTHED", "ISOLATED"],
    ],
  ])("mirrors the backend %s members", (_name, options, expected) => {
    expect([...options]).toEqual(expected);
  });
});

describe("exactDecimalSchema", () => {
  it.each(["250", "0.85", ".5", "5.", "-1.2e-3"])("accepts %s", (text) => {
    expect(exactDecimalSchema.parse(text)).toBe(text);
  });

  it("trims surrounding spaces and keeps the digits exactly", () => {
    expect(exactDecimalSchema.parse(" 35.219668322 ")).toBe("35.219668322");
  });

  it.each(["250 A", "1,5", "abc"])("rejects %s in field language", (text) => {
    const parsed = exactDecimalSchema.safeParse(text);
    expect(parsed.success).toBe(false);
    expect(parsed.error?.issues[0]?.message).toBe(DECIMAL_MESSAGE);
  });

  it("reports a blank value as required first", () => {
    const parsed = exactDecimalSchema.safeParse("   ");
    expect(parsed.success).toBe(false);
    expect(parsed.error?.issues[0]?.message).toBe("Decimal value is required.");
  });

  it("rejects a binary float", () => {
    expect(exactDecimalSchema.safeParse(250).success).toBe(false);
  });
});

describe("shortCircuitStudyRequestSchema", () => {
  it("accepts a two-bus network with two sources and a branch", () => {
    const parsed = shortCircuitStudyRequestSchema.safeParse(network);
    expect(parsed.error?.issues ?? []).toEqual([]);
    expect(parsed.success).toBe(true);
  });

  it("requires at least one source", () => {
    const parsed = shortCircuitStudyRequestSchema.safeParse({ ...network, sources: [] });
    expect(parsed.success).toBe(false);
    expect(parsed.error?.issues[0]?.path).toEqual(["sources"]);
    expect(parsed.error?.issues[0]?.code).toBe("too_small");
  });

  it("rejects a key the backend does not know", () => {
    const parsed = shortCircuitStudyRequestSchema.safeParse({ ...network, decay_data: {} });
    expect(parsed.success).toBe(false);
    expect(parsed.error?.issues[0]?.code).toBe("unrecognized_keys");
  });
});
