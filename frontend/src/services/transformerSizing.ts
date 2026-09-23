import { z } from "zod";

import { calculationRunSummarySchema } from "./calculationRun";
import { jurisdictionProfileSchema } from "./cableContract";
import { exactDecimalSchema } from "./faultContract";
import { ApiError } from "./http";
import { loadScenarioSchema } from "./loadDemandContract";
import {
  DEMAND_POWER_FACTOR_REQUIRED,
  transformerRedundancyModeSchema,
  transformerSizingStatusSchema,
  transformerSizingWarningCodeSchema,
} from "./transformerSizingContract";

const optionalRequestText = (maxLength: number) =>
  z.string().trim().max(maxLength).nullable().optional();

// A factor left out means NOT ESTABLISHED, never 1: the engine sizes with 1,
// names the factor in a warning and reports REVIEW_REQUIRED (Master Prompt
// A16 (a)). The form must omit a blank field instead of sending "1".
const optionalFactor = exactDecimalSchema.optional();

export const transformerSizingRequestSchema = z
  .object({
    code: z.string().trim().min(1).max(50),
    name: z.string().trim().min(1).max(200),
    demand_power_kw: exactDecimalSchema,
    // An engineering input, not a margin: it has no default and is required.
    demand_power_factor: exactDecimalSchema.optional(),
    available_unit_ratings_kva: z.array(exactDecimalSchema).min(1),
    future_growth_factor: optionalFactor,
    design_margin_factor: optionalFactor,
    ambient_derating_factor: optionalFactor,
    altitude_derating_factor: optionalFactor,
    harmonic_derating_factor: optionalFactor,
    duty_units: z.number().int().positive().optional(),
    standby_units: z.number().int().nonnegative().optional(),
    redundancy_mode: transformerRedundancyModeSchema.optional(),
    scenario: loadScenarioSchema.optional(),
    jurisdiction_profile: jurisdictionProfileSchema.optional(),
    notes: optionalRequestText(1000),
  })
  .strict()
  .superRefine((values, ctx) => {
    if (values.demand_power_factor === undefined) {
      // Reported as a missing value rather than a custom rule, so the form's
      // describeValidationIssue turns it into "... is required." instead of
      // pasting the raw sentence after the label.
      ctx.addIssue({
        code: "invalid_type",
        expected: "string",
        received: "undefined",
        message: DEMAND_POWER_FACTOR_REQUIRED,
        path: ["demand_power_factor"],
      });
    }
  });

export const transformerSizingWarningSchema = z
  .object({
    code: transformerSizingWarningCodeSchema,
    message: z.string(),
  })
  .strict();

export const transformerSizingResponseSchema = z
  .object({
    code: z.string(),
    name: z.string(),
    scenario: loadScenarioSchema,
    redundancy_mode: transformerRedundancyModeSchema,
    demand_power_kw: z.string(),
    demand_power_factor: z.string(),
    base_demand_kva: z.string(),
    // The factor the sizing used; "1" when it was not established.
    future_growth_factor: z.string(),
    future_demand_kva: z.string(),
    design_margin_factor: z.string(),
    design_required_kva: z.string(),
    combined_derating_factor: z.string(),
    required_nameplate_capacity_kva: z.string(),
    duty_units: z.number().int(),
    standby_units: z.number().int(),
    total_units: z.number().int(),
    required_unit_rating_kva: z.string(),
    // Null together with the four below when no rating was adequate (NO_SOLUTION).
    selected_unit_rating_kva: z.string().nullable(),
    installed_nameplate_capacity_kva: z.string().nullable(),
    derated_duty_capacity_kva: z.string().nullable(),
    spare_derated_capacity_kva: z.string().nullable(),
    loading_percent: z.string().nullable(),
    status: transformerSizingStatusSchema,
    warnings: z.array(transformerSizingWarningSchema),
    jurisdiction_profile: jurisdictionProfileSchema,
  })
  .strict();

export const transformerRunCreateRequestSchema = z
  .object({
    study: transformerSizingRequestSchema,
    project_revision_id: z.string().uuid().optional(),
    notes: optionalRequestText(2000),
  })
  .strict();

export const transformerRunResponseSchema = z
  .object({
    run: calculationRunSummarySchema,
    result: transformerSizingResponseSchema,
  })
  .strict();

const errorDetailSchema = z.union([
  z.string(),
  z.array(
    z
      .object({
        loc: z.array(z.union([z.string(), z.number()])),
        msg: z.string(),
        type: z.string(),
      })
      .passthrough(),
  ),
]);

const errorResponseSchema = z.object({
  detail: errorDetailSchema,
});

export type TransformerSizingRequest = z.infer<typeof transformerSizingRequestSchema>;
export type TransformerSizingWarning = z.infer<typeof transformerSizingWarningSchema>;
export type TransformerSizingResponse = z.infer<typeof transformerSizingResponseSchema>;
export type TransformerRunCreateRequest = z.infer<typeof transformerRunCreateRequestSchema>;
export type TransformerRunResponse = z.infer<typeof transformerRunResponseSchema>;

function formatApiError(data: unknown, status: number): string {
  const parsed = errorResponseSchema.safeParse(data);

  if (!parsed.success) {
    return `Transformer sizing failed (HTTP ${status}).`;
  }

  if (typeof parsed.data.detail === "string") {
    return parsed.data.detail;
  }

  return parsed.data.detail
    .map((item) => `${item.loc.join(".")}: ${item.msg}`)
    .join("; ");
}

/**
 * Calculate a transformer sizing study and persist it as a run revision.
 *
 * The request carries the whole run body, because a study's notes belong to the
 * run, not to the sizing the engine calculates. The returned summary carries the
 * run ID, engine version, profile, reference status and content hash shown in
 * the traceability panel.
 *
 * With a project revision id the run is stored under that revision of the selected
 * project; without one it belongs to no project. An unchanged study returns the
 * stored revision with HTTP 200 instead of a new one (A11); both are valid here.
 */
export async function createTransformerRun(
  payload: TransformerRunCreateRequest,
  signal?: AbortSignal,
  projectRevisionId?: string,
): Promise<TransformerRunResponse> {
  const validatedPayload = transformerRunCreateRequestSchema.parse(payload);
  const timeoutSignal = AbortSignal.timeout(30_000);
  const requestSignal = signal
    ? AbortSignal.any([signal, timeoutSignal])
    : timeoutSignal;

  const response = await fetch("/api/v1/electrical/transformer-sizing/runs", {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(
      projectRevisionId === undefined
        ? validatedPayload
        : { ...validatedPayload, project_revision_id: projectRevisionId },
    ),
    cache: "no-store",
    signal: requestSignal,
  });

  const data: unknown = await response.json().catch(() => null);

  if (!response.ok) {
    throw new ApiError(formatApiError(data, response.status), response.status);
  }

  const parsed = transformerRunResponseSchema.safeParse(data);

  if (!parsed.success) {
    throw new Error("Unexpected response from the KES Electrical OS transformer runs API.");
  }

  return parsed.data;
}
