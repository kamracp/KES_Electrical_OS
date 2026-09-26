import { z } from "zod";

import { jurisdictionProfileSchema } from "../services/cableContract";
import { loadScenarioSchema } from "../services/loadDemandContract";
import { transformerRedundancyModeSchema } from "../services/transformerSizingContract";
import type { ValidationLabels } from "../utils/validationMessages";

// Draft model of the Transformer sizing study form (EOS-03a): what the user is
// typing, kept apart from the components so the payload rules are tested
// without a browser.
//
// Every value is held as the string the user typed, including the unit counts.
// A blank optional field is left OUT of the payload: under Master Prompt
// A16 (a) a blank factor means NOT ESTABLISHED, and the engine must see it as
// absent, never as "" and never as "1". The demand power factor is an
// engineering input, not a margin, so it stays required.
//
// The available unit ratings are separate entries with stable ids, so adding or
// removing one never disturbs the others; the ids never reach the backend.
// Every entry is sent in the order it is on screen, blank ones included - the
// backend requires a unique ascending schedule of positive decimals and must be
// the one to say so, entry by entry.

export type UnitRatingDraft = {
  id: string;
  value: string;
};

export type TransformerStudyDraft = {
  code: string;
  name: string;
  demandPowerKw: string;
  demandPowerFactor: string;
  futureGrowthFactor: string;
  designMarginFactor: string;
  ambientDeratingFactor: string;
  altitudeDeratingFactor: string;
  harmonicDeratingFactor: string;
  dutyUnits: string;
  // Derived from the redundancy mode and the duty units; shown, never typed.
  standbyUnits: string;
  redundancyMode: string;
  scenario: string;
  jurisdictionProfile: string;
  notes: string;
  unitRatings: UnitRatingDraft[];
};

// The shape a draft kept in the browser tab must still have to be restored: exactly the
// fields above, typed text as strings and the choices as values the contract knows. A draft
// saved by an older form fails here and is dropped instead of half-filling this one.
export const transformerStudyDraftSchema = z
  .object({
    code: z.string(),
    name: z.string(),
    demandPowerKw: z.string(),
    demandPowerFactor: z.string(),
    futureGrowthFactor: z.string(),
    designMarginFactor: z.string(),
    ambientDeratingFactor: z.string(),
    altitudeDeratingFactor: z.string(),
    harmonicDeratingFactor: z.string(),
    dutyUnits: z.string(),
    standbyUnits: z.string(),
    redundancyMode: transformerRedundancyModeSchema,
    scenario: loadScenarioSchema,
    jurisdictionProfile: jurisdictionProfileSchema,
    notes: z.string(),
    unitRatings: z.array(z.object({ id: z.string(), value: z.string() }).strict()).min(1),
  })
  .strict();

let nextRatingNumber = 1;

export function createRatingId(): string {
  const id = `rating-${nextRatingNumber}`;
  nextRatingNumber += 1;
  return id;
}

// Rating ids come from a counter that starts again at 1 on every page load, while a
// restored draft brings the ids it was saved with. Moving the counter past every id in use
// keeps an entry added afterwards from taking the id of one already on screen.
export function seedRatingIdCounter(ids: readonly string[]): void {
  for (const id of ids) {
    const match = /^rating-(\d+)$/.exec(id);
    if (match !== null) {
      nextRatingNumber = Math.max(nextRatingNumber, Number(match[1]) + 1);
    }
  }
}

export function createUnitRatingDraft(): UnitRatingDraft {
  return { id: createRatingId(), value: "" };
}

// Enum defaults are filled in only where the backend itself has one.
export function createInitialTransformerStudyDraft(): TransformerStudyDraft {
  return {
    code: "",
    name: "",
    demandPowerKw: "",
    demandPowerFactor: "",
    futureGrowthFactor: "",
    designMarginFactor: "",
    ambientDeratingFactor: "",
    altitudeDeratingFactor: "",
    harmonicDeratingFactor: "",
    dutyUnits: "1",
    standbyUnits: "0",
    redundancyMode: "NONE",
    scenario: "NORMAL",
    jurisdictionProfile: "IN",
    notes: "",
    unitRatings: [createUnitRatingDraft()],
  };
}

// The standby count the backend requires for each redundancy mode
// (schemas/transformer_sizing.py): NONE needs 0, N_PLUS_1 exactly 1, TWO_N the
// same number as the duty units. The form shows this rather than asking for it,
// so the rule can never be broken by typing.
//
// Under TWO_N the duty text is passed through exactly as typed - blank or not a
// whole number included - so a bad value is reported once, against Duty units,
// instead of twice.
export function deriveStandbyUnits(redundancyMode: string, dutyUnits: string): string {
  if (redundancyMode === "N_PLUS_1") {
    return "1";
  }

  if (redundancyMode === "TWO_N") {
    return dutyUnits;
  }

  return "0";
}


// An optional text or decimal field: sent trimmed, or left out when blank.
function optional(key: string, typed: string): Record<string, string> {
  const value = typed.trim();
  return value === "" ? {} : { [key]: value };
}

// A unit count is a whole number on the contract. A clean whole number is sent
// as one; anything else is passed through as typed, so the schema reports it
// instead of this function guessing what the engineer meant.
function countValue(typed: string): unknown {
  const value = typed.trim();
  return /^\d+$/.test(value) ? Number(value) : typed;
}

// The request body as the form will send it. It is validated afterwards with
// transformerRunCreateRequestSchema, so this function does not judge the values
// and never reorders the rating schedule.
export function buildTransformerRunPayload(
  draft: TransformerStudyDraft,
  projectRevisionId?: string,
): Record<string, unknown> {
  return {
    study: {
      code: draft.code.trim(),
      name: draft.name.trim(),
      demand_power_kw: draft.demandPowerKw.trim(),
      ...optional("demand_power_factor", draft.demandPowerFactor),
      // Every entry is sent, blank ones as "", so the index in a message such as
      // "Unit rating 2 is required." always matches the entry's position on
      // screen. The schema refuses the blank; this builder does not hide it.
      available_unit_ratings_kva: draft.unitRatings.map((rating) => rating.value.trim()),
      ...optional("future_growth_factor", draft.futureGrowthFactor),
      ...optional("design_margin_factor", draft.designMarginFactor),
      ...optional("ambient_derating_factor", draft.ambientDeratingFactor),
      ...optional("altitude_derating_factor", draft.altitudeDeratingFactor),
      ...optional("harmonic_derating_factor", draft.harmonicDeratingFactor),
      duty_units: countValue(draft.dutyUnits),
      standby_units: countValue(deriveStandbyUnits(draft.redundancyMode, draft.dutyUnits)),
      ...optional("redundancy_mode", draft.redundancyMode),
      ...optional("scenario", draft.scenario),
      ...optional("jurisdiction_profile", draft.jurisdictionProfile),
    },
    ...(projectRevisionId === undefined ? {} : { project_revision_id: projectRevisionId }),
    ...optional("notes", draft.notes),
  };
}

// On-screen labels of the Transformer study form, keyed by the request path.
// The run request nests the study under "study", so every study path carries
// that prefix; describeLocation numbers the schedule entries, giving
// "Unit rating 2 - ...".
export const TRANSFORMER_STUDY_LABELS: ValidationLabels = {
  fields: {
    "study.code": "Study code",
    "study.name": "Study name",
    "study.demand_power_kw": "Demand power (kW)",
    "study.demand_power_factor": "Power factor",
    "study.available_unit_ratings_kva": "Unit ratings",
    "study.future_growth_factor": "Future growth factor",
    "study.design_margin_factor": "Design margin factor",
    "study.ambient_derating_factor": "Ambient derating factor",
    "study.altitude_derating_factor": "Altitude derating factor",
    "study.harmonic_derating_factor": "Harmonic derating factor",
    "study.duty_units": "Duty units",
    "study.standby_units": "Standby units",
    "study.redundancy_mode": "Redundancy mode",
    "study.scenario": "Scenario",
    "study.jurisdiction_profile": "Jurisdiction profile",
    notes: "Study notes",
  },
  // One entry of the rating schedule: "Unit rating 2".
  groups: { available_unit_ratings_kva: "Unit rating" },
};
