import { z } from "zod";

import { calculationRunSummarySchema } from "./calculationRun";
import { jurisdictionProfileSchema } from "./cableContract";
import { exactDecimalSchema } from "./faultContract";
import { ApiError } from "./http";
import {
  AC_POWER_FACTOR_REQUIRED,
  loadCalculationStatusSchema,
  loadScenarioSchema,
  loadWarningCodeSchema,
  phaseSystemSchema,
  powerBasisSchema,
} from "./loadDemandContract";

const optionalRequestText = (maxLength: number) =>
  z.string().trim().max(maxLength).nullable().optional();

// A factor left out means NOT ESTABLISHED, never 1: the engine calculates with 1,
// names the factor in a warning and reports REVIEW_REQUIRED (Master Prompt A15 (a)).
// The form must therefore omit a blank field instead of sending "1".
const optionalFactor = exactDecimalSchema.optional();

export const loadRequestSchema = z
  .object({
    code: z.string().trim().min(1).max(50),
    name: z.string().trim().min(1).max(200),
    quantity: z.number().int().positive(),
    rated_power_kw: exactDecimalSchema,
    phase_system: phaseSystemSchema,
    voltage_v: exactDecimalSchema,
    power_factor: optionalFactor,
    efficiency: optionalFactor,
    utilization_factor: optionalFactor,
    demand_factor: optionalFactor,
    scenario: loadScenarioSchema.optional(),
    power_basis: powerBasisSchema.optional(),
    notes: optionalRequestText(1000),
  })
  .strict()
  .superRefine((values, ctx) => {
    // Mirrors LoadCalculationRequest.validate_phase_configuration: an AC load must
    // state its power factor, because a silent unity factor understates the current.
    if (values.phase_system === "DC") {
      if (values.power_factor !== undefined && Number(values.power_factor) !== 1) {
        ctx.addIssue({
          code: "custom",
          message: "DC loads must use a power_factor of 1",
          path: ["power_factor"],
        });
      }
      return;
    }

    if (values.power_factor === undefined) {
      // Reported as a missing value rather than a custom rule, so the form's
      // describeValidationIssue turns it into "Load 1 - Power factor is
      // required." instead of pasting the raw sentence after the label.
      // AC_POWER_FACTOR_REQUIRED stays the backend's own 422 wording.
      ctx.addIssue({
        code: "invalid_type",
        expected: "string",
        received: "undefined",
        message: AC_POWER_FACTOR_REQUIRED,
        path: ["power_factor"],
      });
    }
  });

export const loadGroupRequestSchema = z
  .object({
    code: z.string().trim().min(1).max(50),
    name: z.string().trim().min(1).max(200),
    loads: z.array(loadRequestSchema).min(1),
    coincidence_factor: optionalFactor,
    jurisdiction_profile: jurisdictionProfileSchema.optional(),
  })
  .strict();

export const loadWarningSchema = z
  .object({
    code: loadWarningCodeSchema,
    message: z.string(),
  })
  .strict();

export const loadResultSchema = z
  .object({
    load_code: z.string(),
    load_name: z.string(),
    scenario: loadScenarioSchema,
    phase_system: phaseSystemSchema,
    connected_power_kw: z.string(),
    utilized_power_kw: z.string(),
    demand_power_kw: z.string(),
    apparent_power_kva: z.string(),
    reactive_power_kvar: z.string(),
    design_current_a: z.string(),
    status: loadCalculationStatusSchema,
    warnings: z.array(loadWarningSchema),
  })
  .strict();

export const loadGroupResponseSchema = z
  .object({
    group_code: z.string(),
    group_name: z.string(),
    // The factor the aggregation used; "1" when it was not established.
    coincidence_factor: z.string(),
    connected_power_kw: z.string(),
    pre_coincidence_demand_kw: z.string(),
    demand_power_kw: z.string(),
    apparent_power_kva: z.string(),
    reactive_power_kvar: z.string(),
    load_results: z.array(loadResultSchema),
    status: loadCalculationStatusSchema,
    warnings: z.array(loadWarningSchema),
    // Declared engineering assumptions of the aggregation (A15 (e)).
    assumptions: z.array(z.string()),
    jurisdiction_profile: jurisdictionProfileSchema,
  })
  .strict();

export const loadRunCreateRequestSchema = z
  .object({
    study: loadGroupRequestSchema,
    project_revision_id: z.string().uuid().optional(),
    notes: optionalRequestText(2000),
  })
  .strict();

export const loadRunResponseSchema = z
  .object({
    run: calculationRunSummarySchema,
    result: loadGroupResponseSchema,
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

export type LoadRequest = z.infer<typeof loadRequestSchema>;
export type LoadGroupRequest = z.infer<typeof loadGroupRequestSchema>;
export type LoadWarning = z.infer<typeof loadWarningSchema>;
export type LoadResult = z.infer<typeof loadResultSchema>;
export type LoadGroupResponse = z.infer<typeof loadGroupResponseSchema>;
export type LoadRunCreateRequest = z.infer<typeof loadRunCreateRequestSchema>;
export type LoadRunResponse = z.infer<typeof loadRunResponseSchema>;

function formatApiError(data: unknown, status: number): string {
  const parsed = errorResponseSchema.safeParse(data);

  if (!parsed.success) {
    return `Load calculation failed (HTTP ${status}).`;
  }

  if (typeof parsed.data.detail === "string") {
    return parsed.data.detail;
  }

  return parsed.data.detail
    .map((item) => `${item.loc.join(".")}: ${item.msg}`)
    .join("; ");
}

/**
 * Calculate a load schedule and persist it as a run revision.
 *
 * The persisted study is the load group: several loads with their coincidence
 * factor. The returned summary carries the run ID, engine version, profile,
 * reference status and content hash shown in the traceability panel.
 *
 * With a project revision id the run is stored under that revision of the selected
 * project; without one it belongs to no project. An unchanged study returns the
 * stored revision with HTTP 200 instead of a new one (A11); both are valid here.
 */
export async function createLoadRun(
  payload: LoadGroupRequest,
  signal?: AbortSignal,
  projectRevisionId?: string,
): Promise<LoadRunResponse> {
  const validatedPayload = loadGroupRequestSchema.parse(payload);
  const timeoutSignal = AbortSignal.timeout(30_000);
  const requestSignal = signal
    ? AbortSignal.any([signal, timeoutSignal])
    : timeoutSignal;

  const response = await fetch("/api/v1/electrical/load-demand/runs", {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(
      projectRevisionId === undefined
        ? { study: validatedPayload }
        : { study: validatedPayload, project_revision_id: projectRevisionId },
    ),
    cache: "no-store",
    signal: requestSignal,
  });

  const data: unknown = await response.json().catch(() => null);

  if (!response.ok) {
    throw new ApiError(formatApiError(data, response.status), response.status);
  }

  const parsed = loadRunResponseSchema.safeParse(data);

  if (!parsed.success) {
    throw new Error("Unexpected response from the KES Electrical OS load runs API.");
  }

  return parsed.data;
}
