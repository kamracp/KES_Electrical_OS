import { describe, expect, it } from "vitest";

import { shortCircuitStudyRequestSchema } from "../services/fault";
import { describeValidationIssue } from "../utils/validationMessages";
import {
  FAULT_STUDY_LABELS,
  buildShortCircuitPayload,
  createBranchDraft,
  createBusDraft,
  createInitialFaultStudyDraft,
  createRowId,
  createSourceDraft,
  faultStudyDraftSchema,
  seedRowIdCounter,
  type FaultStudyDraft,
} from "./faultStudyDraft";

// The single-bus study of the Fault UI v1 form test, as a draft.
function filledDraft(): FaultStudyDraft {
  const draft = createInitialFaultStudyDraft();
  Object.assign(draft.buses[0]!, {
    code: "BUS-1",
    name: "Main LV Bus",
    nominalVoltageV: "415",
    voltageFactorMax: "1.10",
    voltageFactorMin: "0.95",
    neutralEarthingMode: "SOLIDLY_EARTHED",
  });
  Object.assign(draft.sources[0]!, {
    code: "GRID-1",
    name: "Utility Grid",
    sourceType: "UTILITY_GRID",
    representation: "VOLTAGE_BEHIND_IMPEDANCE",
    positive: { resistanceOhm: "0.0100", reactanceOhm: "0.0200" },
  });
  return {
    ...draft,
    studyCode: "FAULT-001",
    studyName: "Main LV Bus Fault Study",
    calculationCase: "MAXIMUM",
    faultType: "THREE_PHASE",
    frequencyHz: "50.0",
  };
}

function firstMessage(draft: FaultStudyDraft): string {
  const parsed = shortCircuitStudyRequestSchema.safeParse(buildShortCircuitPayload(draft));
  const issue = parsed.error?.issues[0];
  return issue ? describeValidationIssue(issue, FAULT_STUDY_LABELS) : "no issue";
}

describe("fault study draft", () => {
  it("starts as one bus with one source on it and the fault at that bus", () => {
    const draft = createInitialFaultStudyDraft();

    expect(draft.buses).toHaveLength(1);
    expect(draft.sources).toHaveLength(1);
    expect(draft.branches).toEqual([]);
    expect(draft.sources[0]?.busId).toBe(draft.buses[0]?.id);
    expect(draft.faultBusId).toBe(draft.buses[0]?.id);
    expect(draft.jurisdictionProfile).toBe("IN");
  });

  it("gives every row a different id", () => {
    const ids = [createRowId("bus"), createRowId("bus"), createBusDraft().id, createBranchDraft().id];
    expect(new Set(ids).size).toBe(ids.length);
  });
});

// Bus 1 with the source, bus 2 behind a branch, the fault at bus 2.
function twoBusDraft(): FaultStudyDraft {
  const draft = filledDraft();
  const board = createBusDraft();
  const feeder = { ...createBranchDraft(), fromBusId: draft.buses[0]!.id, toBusId: board.id };
  return { ...draft, buses: [...draft.buses, board], branches: [feeder], faultBusId: board.id };
}

function isValidDraft(draft: unknown): boolean {
  return faultStudyDraftSchema.safeParse(draft).success;
}

describe("faultStudyDraftSchema", () => {
  it("accepts the initial draft, a two-bus draft and one kept through JSON", () => {
    expect(isValidDraft(createInitialFaultStudyDraft())).toBe(true);
    expect(isValidDraft(twoBusDraft())).toBe(true);
    expect(isValidDraft(JSON.parse(JSON.stringify(twoBusDraft())))).toBe(true);
  });

  it("accepts a bus that is not chosen yet, as a new branch or source has it", () => {
    const draft = twoBusDraft();
    draft.branches.push(createBranchDraft());
    draft.sources.push(createSourceDraft());

    expect(isValidDraft({ ...draft, faultBusId: "" })).toBe(true);
  });

  it("refuses a draft with a field this form does not have or a choice the contract does not know", () => {
    expect(isValidDraft({ ...twoBusDraft(), loads: [] })).toBe(false);
    expect(isValidDraft({ ...twoBusDraft(), faultType: "FOUR_PHASE" })).toBe(false);
  });

  it("refuses a draft without a bus or without a source", () => {
    expect(isValidDraft({ ...twoBusDraft(), buses: [] })).toBe(false);
    expect(isValidDraft({ ...twoBusDraft(), sources: [] })).toBe(false);
  });

  it("refuses a row that points at a bus the draft does not have", () => {
    const stale = "bus-999999";
    const draft = twoBusDraft();
    const source = { ...draft.sources[0]!, busId: stale };
    const branch = { ...draft.branches[0]!, toBusId: stale };

    expect(isValidDraft({ ...draft, faultBusId: stale })).toBe(false);
    expect(isValidDraft({ ...draft, sources: [source] })).toBe(false);
    expect(isValidDraft({ ...draft, branches: [branch] })).toBe(false);
  });

  it("refuses a draft that uses one id for two rows", () => {
    const draft = twoBusDraft();
    const twin = { ...draft.branches[0]!, id: draft.sources[0]!.id };

    expect(isValidDraft({ ...draft, branches: [twin] })).toBe(false);
  });
});

describe("seedRowIdCounter", () => {
  it("moves the one shared counter past every bus, source and branch id in use", () => {
    seedRowIdCounter(["bus-900", "source-902", "branch-901"]);

    expect(createRowId("branch")).toBe("branch-903");
  });

  it("never moves the counter back and ignores ids of another form", () => {
    seedRowIdCounter(["bus-950"]);
    seedRowIdCounter(["source-2", "load-5000", "something"]);

    expect(createRowId("bus")).toBe("bus-951");
  });
});

describe("buildShortCircuitPayload", () => {
  it("keeps the single-bus payload exactly as Fault UI v1 sent it", () => {
    const payload = buildShortCircuitPayload(filledDraft());

    expect(payload).toEqual({
      code: "FAULT-001",
      name: "Main LV Bus Fault Study",
      calculation_case: "MAXIMUM",
      fault: { bus_code: "BUS-1", fault_type: "THREE_PHASE" },
      buses: [
        {
          code: "BUS-1",
          name: "Main LV Bus",
          nominal_voltage_v: "415",
          voltage_factor_max: "1.10",
          voltage_factor_min: "0.95",
          neutral_earthing_mode: "SOLIDLY_EARTHED",
        },
      ],
      sources: [
        {
          code: "GRID-1",
          name: "Utility Grid",
          bus_code: "BUS-1",
          source_type: "UTILITY_GRID",
          representation: "VOLTAGE_BEHIND_IMPEDANCE",
          positive_sequence_impedance: { resistance_ohm: "0.0100", reactance_ohm: "0.0200" },
        },
      ],
      frequency_hz: "50.0",
      jurisdiction_profile: "IN",
    });
    expect(shortCircuitStudyRequestSchema.safeParse(payload).success).toBe(true);
  });

  it("sends only the current for a current-injection source", () => {
    const draft = filledDraft();
    Object.assign(draft.sources[0]!, {
      representation: "CURRENT_INJECTION",
      currentContributionKa: "2.750",
    });

    const parsed = shortCircuitStudyRequestSchema.parse(buildShortCircuitPayload(draft));
    expect(parsed.sources[0]).toMatchObject({ current_contribution_ka: "2.750" });
    expect(parsed.sources[0]).not.toHaveProperty("positive_sequence_impedance");
  });

  it("omits a blank optional impedance pair and passes a half-filled one through", () => {
    const draft = filledDraft();
    Object.assign(draft.sources[0]!, { negative: { resistanceOhm: "0.0110", reactanceOhm: "" } });

    const source = (buildShortCircuitPayload(draft).sources as Record<string, unknown>[])[0];
    expect(source).toHaveProperty("negative_sequence_impedance", {
      resistance_ohm: "0.0110",
      reactance_ohm: "",
    });
    expect(source).not.toHaveProperty("zero_sequence_impedance");
    expect(firstMessage(draft)).toBe("Source 1 — Negative-sequence reactance (Ω) is required.");
  });

  it("sends a neutral impedance only under its own earthing mode", () => {
    const draft = filledDraft();
    Object.assign(draft.buses[0]!, { neutralResistanceOhm: "12.5" });

    const solidly = (buildShortCircuitPayload(draft).buses as Record<string, unknown>[])[0];
    expect(solidly).not.toHaveProperty("neutral_resistance_ohm");

    Object.assign(draft.buses[0]!, { neutralEarthingMode: "RESISTANCE_EARTHED" });
    const resistance = (buildShortCircuitPayload(draft).buses as Record<string, unknown>[])[0];
    expect(resistance).toHaveProperty("neutral_resistance_ohm", "12.5");
  });

  it("omits a blank frequency and an empty branch list", () => {
    const payload = buildShortCircuitPayload({ ...filledDraft(), frequencyHz: " " });

    expect(payload).not.toHaveProperty("frequency_hz");
    expect(payload).not.toHaveProperty("branches");
  });

  it("builds a two-bus network: bus ids become codes, the branch links the buses", () => {
    const draft = filledDraft();
    const mainBus = draft.buses[0]!;
    const boardBus = {
      ...createBusDraft(),
      code: "DB-01",
      name: "Distribution board",
      nominalVoltageV: "415",
      voltageFactorMax: "1.10",
      voltageFactorMin: "0.95",
      neutralEarthingMode: "SOLIDLY_EARTHED",
    };
    const motor = {
      ...createSourceDraft(boardBus.id),
      code: "M-01",
      name: "Motor group",
      sourceType: "ASYNCHRONOUS_MOTOR",
      representation: "CURRENT_INJECTION",
      currentContributionKa: "1.2",
      inService: false,
    };
    const feeder = {
      ...createBranchDraft(),
      code: "CBL-01",
      name: "Feeder to DB-01",
      fromBusId: mainBus.id,
      toBusId: boardBus.id,
      branchType: "CABLE",
      positive: { resistanceOhm: "0.0124", reactanceOhm: "0.0080" },
      parallelCircuits: "2",
    };

    const parsed = shortCircuitStudyRequestSchema.parse(
      buildShortCircuitPayload({
        ...draft,
        faultBusId: boardBus.id,
        buses: [mainBus, boardBus],
        sources: [draft.sources[0]!, motor],
        branches: [feeder],
      }),
    );

    expect(parsed.fault.bus_code).toBe("DB-01");
    expect(parsed.buses.map((bus) => bus.code)).toEqual(["BUS-1", "DB-01"]);
    expect(parsed.sources[1]).toEqual({
      code: "M-01",
      name: "Motor group",
      bus_code: "DB-01",
      source_type: "ASYNCHRONOUS_MOTOR",
      representation: "CURRENT_INJECTION",
      current_contribution_ka: "1.2",
      in_service: false,
    });
    expect(parsed.branches).toEqual([
      {
        code: "CBL-01",
        name: "Feeder to DB-01",
        from_bus_code: "BUS-1",
        to_bus_code: "DB-01",
        branch_type: "CABLE",
        positive_sequence_impedance: { resistance_ohm: "0.0124", reactance_ohm: "0.0080" },
        parallel_circuits: 2,
      },
    ]);
  });

  it("follows a bus by id when its code is edited later", () => {
    const draft = filledDraft();
    Object.assign(draft.buses[0]!, { code: "MSB-01" });

    const parsed = shortCircuitStudyRequestSchema.parse(buildShortCircuitPayload(draft));
    expect(parsed.sources[0]?.bus_code).toBe("MSB-01");
    expect(parsed.fault.bus_code).toBe("MSB-01");
  });
});

describe("fault study validation messages", () => {
  it("rewrites the raw source-name message the founder saw", () => {
    const draft = filledDraft();
    Object.assign(draft.sources[0]!, { name: "" });

    expect(firstMessage(draft)).toBe("Source 1 — Source name is required.");
  });

  it("asks for the connected bus when a source points at a removed bus", () => {
    const draft = filledDraft();
    Object.assign(draft.sources[0]!, { busId: "bus-removed" });

    expect(firstMessage(draft)).toBe("Source 1 — Connected bus is required.");
  });
});
