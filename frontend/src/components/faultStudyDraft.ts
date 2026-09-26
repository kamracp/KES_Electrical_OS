import { z } from "zod";

import { jurisdictionProfileSchema } from "../services/cableContract";
import {
  faultBranchTypeSchema,
  faultSourceTypeSchema,
  faultTypeSchema,
  neutralEarthingModeSchema,
  shortCircuitCaseSchema,
  sourceRepresentationSchema,
} from "../services/faultContract";
import type { ValidationLabels } from "../utils/validationMessages";

// Draft model of the Fault study form (Fault UI v2): what the user is typing,
// kept apart from the components so the payload rules are tested without a
// browser. Every row has a stable id; a source or a branch points at a bus by
// that id, so editing a bus code never breaks the link. The ids never reach
// the backend: buildShortCircuitPayload turns them into bus codes.

export type ImpedanceDraft = {
  resistanceOhm: string;
  reactanceOhm: string;
};

export type BusDraft = {
  id: string;
  code: string;
  name: string;
  nominalVoltageV: string;
  voltageFactorMax: string;
  voltageFactorMin: string;
  neutralEarthingMode: string;
  neutralResistanceOhm: string;
  neutralReactanceOhm: string;
};

export type SourceDraft = {
  id: string;
  code: string;
  name: string;
  busId: string;
  sourceType: string;
  representation: string;
  positive: ImpedanceDraft;
  negative: ImpedanceDraft;
  zero: ImpedanceDraft;
  currentContributionKa: string;
  inService: boolean;
};

export type BranchDraft = {
  id: string;
  code: string;
  name: string;
  fromBusId: string;
  toBusId: string;
  branchType: string;
  positive: ImpedanceDraft;
  negative: ImpedanceDraft;
  zero: ImpedanceDraft;
  parallelCircuits: string;
  inService: boolean;
};

export type FaultStudyDraft = {
  studyCode: string;
  studyName: string;
  calculationCase: string;
  faultType: string;
  faultBusId: string;
  frequencyHz: string;
  jurisdictionProfile: string;
  buses: BusDraft[];
  sources: SourceDraft[];
  branches: BranchDraft[];
};

// A choice the user has not made yet is held as "" - a new row starts that way.
function chosenOrBlank<T extends z.ZodType<string>>(choice: T) {
  return z.union([z.literal(""), choice]);
}

const impedanceDraftSchema = z
  .object({ resistanceOhm: z.string(), reactanceOhm: z.string() })
  .strict();

const busDraftSchema = z
  .object({
    id: z.string(),
    code: z.string(),
    name: z.string(),
    nominalVoltageV: z.string(),
    voltageFactorMax: z.string(),
    voltageFactorMin: z.string(),
    neutralEarthingMode: chosenOrBlank(neutralEarthingModeSchema),
    neutralResistanceOhm: z.string(),
    neutralReactanceOhm: z.string(),
  })
  .strict();

const sourceDraftSchema = z
  .object({
    id: z.string(),
    code: z.string(),
    name: z.string(),
    busId: z.string(),
    sourceType: chosenOrBlank(faultSourceTypeSchema),
    representation: chosenOrBlank(sourceRepresentationSchema),
    positive: impedanceDraftSchema,
    negative: impedanceDraftSchema,
    zero: impedanceDraftSchema,
    currentContributionKa: z.string(),
    inService: z.boolean(),
  })
  .strict();

const branchDraftSchema = z
  .object({
    id: z.string(),
    code: z.string(),
    name: z.string(),
    fromBusId: z.string(),
    toBusId: z.string(),
    branchType: chosenOrBlank(faultBranchTypeSchema),
    positive: impedanceDraftSchema,
    negative: impedanceDraftSchema,
    zero: impedanceDraftSchema,
    parallelCircuits: z.string(),
    inService: z.boolean(),
  })
  .strict();

// The shape a draft kept in the browser tab must still have to be restored: exactly the
// fields above, typed text as strings and the choices as values the contract knows or "".
// The rows point at buses by id, so the links are checked too: every id is used once, and
// every bus reference is either not chosen yet ("") or a bus of this draft. A draft with a
// broken link is dropped as a whole rather than restored with a row pointing nowhere.
export const faultStudyDraftSchema = z
  .object({
    studyCode: z.string(),
    studyName: z.string(),
    calculationCase: chosenOrBlank(shortCircuitCaseSchema),
    faultType: chosenOrBlank(faultTypeSchema),
    faultBusId: z.string(),
    frequencyHz: z.string(),
    jurisdictionProfile: jurisdictionProfileSchema,
    buses: z.array(busDraftSchema).min(1),
    sources: z.array(sourceDraftSchema).min(1),
    branches: z.array(branchDraftSchema),
  })
  .strict()
  .superRefine((draft, context) => {
    const ids = [...draft.buses, ...draft.sources, ...draft.branches].map((row) => row.id);
    if (new Set(ids).size !== ids.length) {
      context.addIssue({ code: "custom", message: "A row id is used more than once." });
    }

    const busIds = new Set(draft.buses.map((bus) => bus.id));
    const references = [
      draft.faultBusId,
      ...draft.sources.map((source) => source.busId),
      ...draft.branches.flatMap((branch) => [branch.fromBusId, branch.toBusId]),
    ];
    if (references.some((busId) => busId !== "" && !busIds.has(busId))) {
      context.addIssue({ code: "custom", message: "A row points at a bus the draft does not have." });
    }
  });

let nextRowNumber = 1;

export function createRowId(prefix: "bus" | "source" | "branch"): string {
  const id = `${prefix}-${nextRowNumber}`;
  nextRowNumber += 1;
  return id;
}

// Buses, sources and branches share one counter that starts again at 1 on every page load,
// while a restored draft brings the ids it was saved with. Moving the counter past every id
// in use keeps a row added afterwards from taking the id of one already on screen.
export function seedRowIdCounter(ids: readonly string[]): void {
  for (const id of ids) {
    const match = /^(?:bus|source|branch)-(\d+)$/.exec(id);
    if (match !== null) {
      nextRowNumber = Math.max(nextRowNumber, Number(match[1]) + 1);
    }
  }
}

function emptyImpedance(): ImpedanceDraft {
  return { resistanceOhm: "", reactanceOhm: "" };
}

export function createBusDraft(): BusDraft {
  return {
    id: createRowId("bus"),
    code: "",
    name: "",
    nominalVoltageV: "",
    voltageFactorMax: "",
    voltageFactorMin: "",
    neutralEarthingMode: "",
    neutralResistanceOhm: "",
    neutralReactanceOhm: "",
  };
}

export function createSourceDraft(busId = ""): SourceDraft {
  return {
    id: createRowId("source"),
    code: "",
    name: "",
    busId,
    sourceType: "",
    representation: "",
    positive: emptyImpedance(),
    negative: emptyImpedance(),
    zero: emptyImpedance(),
    currentContributionKa: "",
    inService: true,
  };
}

export function createBranchDraft(): BranchDraft {
  return {
    id: createRowId("branch"),
    code: "",
    name: "",
    fromBusId: "",
    toBusId: "",
    branchType: "",
    positive: emptyImpedance(),
    negative: emptyImpedance(),
    zero: emptyImpedance(),
    parallelCircuits: "",
    inService: true,
  };
}

// One bus with one source on it and the fault at that bus: the single-bus
// study of Fault UI v1, so its payload stays exactly what it was.
export function createInitialFaultStudyDraft(): FaultStudyDraft {
  const bus = createBusDraft();
  return {
    studyCode: "",
    studyName: "",
    calculationCase: "",
    faultType: "",
    faultBusId: bus.id,
    frequencyHz: "",
    jurisdictionProfile: "IN",
    buses: [bus],
    sources: [createSourceDraft(bus.id)],
    branches: [],
  };
}

function impedance(draft: ImpedanceDraft) {
  return { resistance_ohm: draft.resistanceOhm, reactance_ohm: draft.reactanceOhm };
}

function isBlank(draft: ImpedanceDraft): boolean {
  return draft.resistanceOhm.trim() === "" && draft.reactanceOhm.trim() === "";
}

// Optional pair: left out when both fields are blank; a half-filled pair is
// passed through so the schema names the missing field.
function optionalImpedances(row: { negative: ImpedanceDraft; zero: ImpedanceDraft }) {
  return {
    ...(isBlank(row.negative) ? {} : { negative_sequence_impedance: impedance(row.negative) }),
    ...(isBlank(row.zero) ? {} : { zero_sequence_impedance: impedance(row.zero) }),
  };
}

// The request body as the form will send it. It is validated afterwards with
// shortCircuitStudyRequestSchema, so this function does not judge the values.
export function buildShortCircuitPayload(draft: FaultStudyDraft): Record<string, unknown> {
  const busCode = (busId: string) => draft.buses.find((bus) => bus.id === busId)?.code ?? "";

  const buses = draft.buses.map((bus) => ({
    code: bus.code,
    name: bus.name,
    nominal_voltage_v: bus.nominalVoltageV,
    voltage_factor_max: bus.voltageFactorMax,
    voltage_factor_min: bus.voltageFactorMin,
    neutral_earthing_mode: bus.neutralEarthingMode,
    // A neutral impedance belongs to its earthing mode; a value typed under
    // another mode is not sent.
    ...(bus.neutralEarthingMode === "RESISTANCE_EARTHED" && bus.neutralResistanceOhm.trim() !== ""
      ? { neutral_resistance_ohm: bus.neutralResistanceOhm }
      : {}),
    ...(bus.neutralEarthingMode === "REACTANCE_EARTHED" && bus.neutralReactanceOhm.trim() !== ""
      ? { neutral_reactance_ohm: bus.neutralReactanceOhm }
      : {}),
  }));

  const sources = draft.sources.map((source) => ({
    code: source.code,
    name: source.name,
    bus_code: busCode(source.busId),
    source_type: source.sourceType,
    representation: source.representation,
    ...(source.representation === "VOLTAGE_BEHIND_IMPEDANCE"
      ? { positive_sequence_impedance: impedance(source.positive), ...optionalImpedances(source) }
      : {}),
    ...(source.representation === "CURRENT_INJECTION"
      ? { current_contribution_ka: source.currentContributionKa }
      : {}),
    ...(source.inService ? {} : { in_service: false }),
  }));

  const branches = draft.branches.map((branch) => ({
    code: branch.code,
    name: branch.name,
    from_bus_code: busCode(branch.fromBusId),
    to_bus_code: busCode(branch.toBusId),
    branch_type: branch.branchType,
    positive_sequence_impedance: impedance(branch.positive),
    ...optionalImpedances(branch),
    ...(branch.parallelCircuits.trim() === ""
      ? {}
      : { parallel_circuits: Number(branch.parallelCircuits) }),
    ...(branch.inService ? {} : { in_service: false }),
  }));

  return {
    code: draft.studyCode,
    name: draft.studyName,
    calculation_case: draft.calculationCase,
    fault: { bus_code: busCode(draft.faultBusId), fault_type: draft.faultType },
    buses,
    sources,
    ...(branches.length > 0 ? { branches } : {}),
    ...(draft.frequencyHz.trim() === "" ? {} : { frequency_hz: draft.frequencyHz }),
    jurisdiction_profile: draft.jurisdictionProfile,
  };
}

const SEQUENCE_LABELS = {
  "positive_sequence_impedance.resistance_ohm": "Positive-sequence resistance (Ω)",
  "positive_sequence_impedance.reactance_ohm": "Positive-sequence reactance (Ω)",
  "negative_sequence_impedance.resistance_ohm": "Negative-sequence resistance (Ω)",
  "negative_sequence_impedance.reactance_ohm": "Negative-sequence reactance (Ω)",
  "zero_sequence_impedance.resistance_ohm": "Zero-sequence resistance (Ω)",
  "zero_sequence_impedance.reactance_ohm": "Zero-sequence reactance (Ω)",
};

function withPrefix(prefix: string, labels: Record<string, string>): Record<string, string> {
  return Object.fromEntries(Object.entries(labels).map(([key, label]) => [`${prefix}.${key}`, label]));
}

// On-screen labels of the Fault study form, keyed by the request path.
export const FAULT_STUDY_LABELS: ValidationLabels = {
  fields: {
    code: "Study code",
    name: "Study name",
    calculation_case: "Calculation case",
    "fault.fault_type": "Fault type",
    "fault.bus_code": "Fault at bus",
    frequency_hz: "Frequency (Hz)",
    jurisdiction_profile: "Jurisdiction profile",
    buses: "Buses",
    sources: "Sources",
    "buses.*.code": "Bus code",
    "buses.*.name": "Bus name",
    "buses.*.nominal_voltage_v": "Nominal voltage (V)",
    "buses.*.voltage_factor_max": "Maximum voltage factor",
    "buses.*.voltage_factor_min": "Minimum voltage factor",
    "buses.*.neutral_earthing_mode": "Neutral earthing mode",
    "buses.*.neutral_resistance_ohm": "Neutral resistance (Ω)",
    "buses.*.neutral_reactance_ohm": "Neutral reactance (Ω)",
    "sources.*.code": "Source code",
    "sources.*.name": "Source name",
    "sources.*.bus_code": "Connected bus",
    "sources.*.source_type": "Source type",
    "sources.*.representation": "Source representation",
    "sources.*.current_contribution_ka": "Current contribution (kA)",
    ...withPrefix("sources.*", SEQUENCE_LABELS),
    "branches.*.code": "Branch code",
    "branches.*.name": "Branch name",
    "branches.*.from_bus_code": "From bus",
    "branches.*.to_bus_code": "To bus",
    "branches.*.branch_type": "Branch type",
    "branches.*.parallel_circuits": "Parallel circuits",
    ...withPrefix("branches.*", SEQUENCE_LABELS),
  },
  groups: { buses: "Bus", sources: "Source", branches: "Branch" },
};
