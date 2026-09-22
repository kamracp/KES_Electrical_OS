import { z } from "zod";

import { calculationRunSummarySchema } from "./calculationRun";
import { ApiError } from "./http";
import {
  cableCheckStatusSchema,
  cableConstructionSchema,
  cableSizingStatusSchema,
  cableWarningCodeSchema,
  circuitSystemSchema,
  conductorArrangementSchema,
  conductorMaterialSchema,
  exactDecimalSchema,
  installationMethodSchema,
  insulationMaterialSchema,
  jurisdictionProfileSchema,
  protectiveConductorTypeSchema,
  cableReferenceSourceSchema,
  referenceVerificationStatusSchema,
} from "./cableContract";

const optionalRequestText = (maxLength: number) =>
  z.string().trim().max(maxLength).nullable().optional();

const positiveInt = z.number().int().positive();

/** Mirrors CableSizeScheduleSchema: unique, strictly ascending exact decimals. */
const ascendingDecimalList = z
  .array(exactDecimalSchema)
  .min(1)
  .superRefine((values, ctx) => {
    const numeric = values.map((value) => Number(value));
    for (let index = 1; index < numeric.length; index += 1) {
      if (!(numeric[index] > numeric[index - 1])) {
        ctx.addIssue({
          code: "custom",
          message: "Sizes must be unique and in ascending order.",
          path: [index],
        });
        return;
      }
    }
  });

export const cableCircuitRequestSchema = z
  .object({
    design_current_a: exactDecimalSchema,
    nominal_voltage_v: exactDecimalSchema,
    route_length_m: exactDecimalSchema,
    system: circuitSystemSchema,
    power_factor: exactDecimalSchema.optional(),
    allowable_voltage_drop_percent: exactDecimalSchema.optional(),
    fault_current_ka: exactDecimalSchema.nullable().optional(),
    fault_duration_s: exactDecimalSchema.nullable().optional(),
    harmonic_neutral_factor: exactDecimalSchema.optional(),
  })
  .strict();

export const cableConstructionRequestSchema = z
  .object({
    conductor_material: conductorMaterialSchema,
    insulation_material: insulationMaterialSchema,
    construction: cableConstructionSchema,
    arrangement: conductorArrangementSchema,
    number_of_loaded_conductors: z.number().int().min(1).max(4),
    parallel_runs: positiveInt.optional(),
    neutral_required: z.boolean().optional(),
    reduced_neutral_permitted: z.boolean().optional(),
    protective_conductor_type: protectiveConductorTypeSchema.optional(),
    armoured: z.boolean().optional(),
  })
  .strict();

export const cableInstallationRequestSchema = z
  .object({
    method: installationMethodSchema,
    ambient_temperature_c: exactDecimalSchema,
    ambient_derating_factor: exactDecimalSchema.optional(),
    grouping_derating_factor: exactDecimalSchema.optional(),
    thermal_insulation_factor: exactDecimalSchema.optional(),
    depth_derating_factor: exactDecimalSchema.optional(),
    soil_thermal_resistivity_factor: exactDecimalSchema.optional(),
    grouped_circuits: positiveInt.optional(),
    burial_depth_m: exactDecimalSchema.nullable().optional(),
    soil_thermal_resistivity_k_m_per_w: exactDecimalSchema.nullable().optional(),
    conductor_spacing_mm: exactDecimalSchema.nullable().optional(),
  })
  .strict();

export const cableSizeScheduleRequestSchema = z
  .object({
    phase_sizes_mm2: ascendingDecimalList,
    neutral_sizes_mm2: ascendingDecimalList.nullable().optional(),
    protective_sizes_mm2: ascendingDecimalList.nullable().optional(),
  })
  .strict();

export const cableSizingRequestSchema = z
  .object({
    code: z.string().trim().min(1).max(80),
    name: z.string().trim().min(1).max(200),
    circuit: cableCircuitRequestSchema,
    cable: cableConstructionRequestSchema,
    installation: cableInstallationRequestSchema,
    size_schedule: cableSizeScheduleRequestSchema,
    standard_reference: z.string().trim().min(1).max(80).optional(),
    ampacity_reference: z.string().trim().min(1).max(80).optional(),
    jurisdiction_profile: jurisdictionProfileSchema.optional(),
    notes: optionalRequestText(1000),
  })
  .strict();

const cableConductorResultResponseSchema = z
  .object({
    phase_area_mm2: exactDecimalSchema,
    neutral_area_mm2: exactDecimalSchema.nullable(),
    protective_area_mm2: exactDecimalSchema.nullable(),
    parallel_runs: z.number().int(),
    phase_conductors_per_run: z.number().int(),
    neutral_status: cableCheckStatusSchema,
    protective_status: cableCheckStatusSchema,
  })
  .strict();

const cableAmpacityResultResponseSchema = z
  .object({
    tabulated_ampacity_a_per_run: exactDecimalSchema,
    combined_derating_factor: exactDecimalSchema,
    derating_established: z.boolean(),
    unestablished_derating_factors: z.array(z.string()),
    derated_ampacity_a_per_run: exactDecimalSchema,
    parallel_runs: z.number().int(),
    total_installed_ampacity_a: exactDecimalSchema,
    design_current_a: exactDecimalSchema,
    required_tabulated_ampacity_a_per_run: exactDecimalSchema,
    utilization_ratio: exactDecimalSchema,
    status: cableCheckStatusSchema,
  })
  .strict();

const cableVoltageDropResultResponseSchema = z
  .object({
    resistance_ohm_per_km: exactDecimalSchema,
    reactance_ohm_per_km: exactDecimalSchema,
    voltage_drop_v: exactDecimalSchema,
    voltage_drop_percent: exactDecimalSchema,
    allowable_voltage_drop_percent: exactDecimalSchema,
    status: cableCheckStatusSchema,
  })
  .strict();

const cableShortCircuitResultResponseSchema = z
  .object({
    fault_current_ka: exactDecimalSchema.nullable(),
    fault_duration_s: exactDecimalSchema.nullable(),
    material_constant_k: exactDecimalSchema.nullable(),
    required_area_mm2: exactDecimalSchema.nullable(),
    selected_area_mm2: exactDecimalSchema,
    withstand_current_ka: exactDecimalSchema.nullable(),
    status: cableCheckStatusSchema,
  })
  .strict();

const cableEngineeringWarningResponseSchema = z
  .object({
    code: cableWarningCodeSchema,
    message: z.string().min(1),
    field_name: z.string().min(1).nullable(),
  })
  .strict();

export const cableSizingResponseSchema = z
  .object({
    study_code: z.string().min(1),
    status: cableSizingStatusSchema,
    conductor: cableConductorResultResponseSchema.nullable(),
    ampacity: cableAmpacityResultResponseSchema.nullable(),
    voltage_drop: cableVoltageDropResultResponseSchema.nullable(),
    short_circuit: cableShortCircuitResultResponseSchema.nullable(),
    warnings: z.array(cableEngineeringWarningResponseSchema),
    standard_reference: z.string().min(1).nullable(),
    ampacity_reference: z.string().min(1).nullable(),
    reference_source: cableReferenceSourceSchema,
    jurisdiction_profile: jurisdictionProfileSchema,
    reference_verification_status: referenceVerificationStatusSchema,
    notes: z.string().nullable(),
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

export type CableCircuitRequest = z.infer<typeof cableCircuitRequestSchema>;
export type CableConstructionRequest = z.infer<typeof cableConstructionRequestSchema>;
export type CableInstallationRequest = z.infer<typeof cableInstallationRequestSchema>;
export type CableSizeScheduleRequest = z.infer<typeof cableSizeScheduleRequestSchema>;
export type CableSizingRequest = z.infer<typeof cableSizingRequestSchema>;
export type CableSizingResponse = z.infer<typeof cableSizingResponseSchema>;
export type CableEngineeringWarning = z.infer<typeof cableEngineeringWarningResponseSchema>;

function formatApiError(data: unknown, status: number): string {
  const parsed = errorResponseSchema.safeParse(data);

  if (!parsed.success) {
    return `Cable sizing failed (HTTP ${status}).`;
  }

  if (typeof parsed.data.detail === "string") {
    return parsed.data.detail;
  }

  return parsed.data.detail
    .map((item) => `${item.loc.join(".")}: ${item.msg}`)
    .join("; ");
}

export async function calculateCableSizing(
  payload: CableSizingRequest,
  signal?: AbortSignal,
): Promise<CableSizingResponse> {
  const validatedPayload = cableSizingRequestSchema.parse(payload);
  const timeoutSignal = AbortSignal.timeout(30_000);
  const requestSignal = signal
    ? AbortSignal.any([signal, timeoutSignal])
    : timeoutSignal;

  const response = await fetch("/api/v1/electrical/cable/calculate", {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(validatedPayload),
    cache: "no-store",
    signal: requestSignal,
  });

  const data: unknown = await response.json().catch(() => null);

  if (!response.ok) {
    throw new ApiError(formatApiError(data, response.status), response.status);
  }

  const parsed = cableSizingResponseSchema.safeParse(data);

  if (!parsed.success) {
    throw new Error("Unexpected response from the KES Electrical OS cable API.");
  }

  return parsed.data;
}

// Persisted runs (Master Prompt v2.1 item 15 / section 19 traceability).

export const cableRunResponseSchema = z
  .object({
    run: calculationRunSummarySchema,
    result: cableSizingResponseSchema,
  })
  .strict();

export { calculationRunSummarySchema, type CalculationRunSummary } from "./calculationRun";
export type CableRunResponse = z.infer<typeof cableRunResponseSchema>;

/**
 * Calculate a cable study and persist it as a run revision.
 *
 * The persisted run is the only thing a study page may export (section 20):
 * the returned summary carries the run ID, engine version, profile, reference
 * status and content hash shown in the traceability panel.
 *
 * With a project revision id the run is stored under that revision of the selected
 * project; without one it belongs to no project, exactly as before EOS-01 (b).
 */
export async function createCableRun(
  payload: CableSizingRequest,
  signal?: AbortSignal,
  projectRevisionId?: string,
): Promise<CableRunResponse> {
  const validatedPayload = cableSizingRequestSchema.parse(payload);
  const timeoutSignal = AbortSignal.timeout(30_000);
  const requestSignal = signal ? AbortSignal.any([signal, timeoutSignal]) : timeoutSignal;

  const response = await fetch("/api/v1/electrical/cable/runs", {
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

  const parsed = cableRunResponseSchema.safeParse(data);

  if (!parsed.success) {
    throw new Error("Unexpected response from the KES Electrical OS cable runs API.");
  }

  return parsed.data;
}
