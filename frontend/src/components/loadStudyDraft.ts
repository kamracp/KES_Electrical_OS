import type { ValidationLabels } from "../utils/validationMessages";

// Draft model of the Load and demand study form (EOS-02): what the user is
// typing, kept apart from the components so the payload rules are tested
// without a browser. Every row has a stable id so adding or removing a load
// never disturbs the others; the ids never reach the backend.
//
// The persisted study is the load group - a schedule of loads with its
// coincidence factor - so the draft builds a LoadRunCreateRequest.
//
// Every value is held as the string the user typed, including the quantity.
// A blank optional field is left OUT of the payload: under Master Prompt
// A15 (a) a blank factor means NOT ESTABLISHED, and the engine must see it
// as absent, never as "" and never as "1".

export type LoadRowDraft = {
  id: string;
  code: string;
  name: string;
  quantity: string;
  ratedPowerKw: string;
  phaseSystem: string;
  voltageV: string;
  powerFactor: string;
  efficiency: string;
  utilizationFactor: string;
  demandFactor: string;
  scenario: string;
  powerBasis: string;
  notes: string;
};

export type LoadStudyDraft = {
  code: string;
  name: string;
  jurisdictionProfile: string;
  coincidenceFactor: string;
  notes: string;
  loads: LoadRowDraft[];
};

let nextRowNumber = 1;

export function createRowId(prefix: "load"): string {
  const id = `${prefix}-${nextRowNumber}`;
  nextRowNumber += 1;
  return id;
}

// Enum defaults are filled in only where the backend itself has one. The phase
// system has none, so it stays blank and the engineer has to choose it - a
// silent THREE_PHASE would decide the current calculation for them.
export function createLoadRowDraft(): LoadRowDraft {
  return {
    id: createRowId("load"),
    code: "",
    name: "",
    quantity: "",
    ratedPowerKw: "",
    phaseSystem: "",
    voltageV: "",
    powerFactor: "",
    efficiency: "",
    utilizationFactor: "",
    demandFactor: "",
    scenario: "NORMAL",
    powerBasis: "ELECTRICAL_INPUT",
    notes: "",
  };
}

export function createInitialLoadStudyDraft(): LoadStudyDraft {
  return {
    code: "",
    name: "",
    jurisdictionProfile: "IN",
    coincidenceFactor: "",
    notes: "",
    loads: [createLoadRowDraft()],
  };
}

// An optional text or decimal field: sent trimmed, or left out when blank.
function optional(key: string, typed: string): Record<string, string> {
  const value = typed.trim();
  return value === "" ? {} : { [key]: value };
}

// The quantity is a whole number on the contract. A clean whole number is sent
// as one; anything else is passed through as typed, so the schema reports it
// instead of this function guessing what the engineer meant.
function quantityValue(typed: string): unknown {
  const value = typed.trim();
  return /^\d+$/.test(value) ? Number(value) : typed;
}

function loadPayload(row: LoadRowDraft): Record<string, unknown> {
  return {
    code: row.code.trim(),
    name: row.name.trim(),
    quantity: quantityValue(row.quantity),
    rated_power_kw: row.ratedPowerKw.trim(),
    phase_system: row.phaseSystem,
    voltage_v: row.voltageV.trim(),
    ...optional("power_factor", row.powerFactor),
    ...optional("efficiency", row.efficiency),
    ...optional("utilization_factor", row.utilizationFactor),
    ...optional("demand_factor", row.demandFactor),
    ...optional("scenario", row.scenario),
    ...optional("power_basis", row.powerBasis),
    ...optional("notes", row.notes),
  };
}

// The request body as the form will send it. It is validated afterwards with
// loadRunCreateRequestSchema, so this function does not judge the values.
export function buildLoadRunPayload(
  draft: LoadStudyDraft,
  projectRevisionId?: string,
): Record<string, unknown> {
  return {
    study: {
      code: draft.code.trim(),
      name: draft.name.trim(),
      loads: draft.loads.map(loadPayload),
      ...optional("coincidence_factor", draft.coincidenceFactor),
      ...optional("jurisdiction_profile", draft.jurisdictionProfile),
    },
    ...(projectRevisionId === undefined ? {} : { project_revision_id: projectRevisionId }),
    ...optional("notes", draft.notes),
  };
}

// On-screen labels of the Load study form, keyed by the request path. The run
// request nests the schedule under "study", so every study path carries that
// prefix; describeLocation numbers the list items, giving "Load 2 - ...".
export const LOAD_STUDY_LABELS: ValidationLabels = {
  fields: {
    "study.code": "Study code",
    "study.name": "Study name",
    "study.coincidence_factor": "Coincidence factor",
    "study.jurisdiction_profile": "Jurisdiction profile",
    "study.loads": "Loads",
    // Named apart from a load row's own notes, which stay "Notes".
    notes: "Study notes",
    "study.loads.*.code": "Load code",
    "study.loads.*.name": "Load name",
    "study.loads.*.quantity": "Quantity",
    "study.loads.*.rated_power_kw": "Rated power (kW)",
    "study.loads.*.phase_system": "Phase system",
    "study.loads.*.voltage_v": "Voltage (V)",
    "study.loads.*.power_factor": "Power factor",
    "study.loads.*.efficiency": "Efficiency",
    "study.loads.*.utilization_factor": "Utilization factor",
    "study.loads.*.demand_factor": "Demand factor",
    "study.loads.*.scenario": "Scenario",
    "study.loads.*.power_basis": "Power basis",
    "study.loads.*.notes": "Notes",
  },
  groups: { loads: "Load" },
};
