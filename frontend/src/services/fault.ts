import { z } from "zod";

import {
  exactDecimalSchema,
  faultBranchTypeSchema,
  faultResultStatusSchema,
  faultSequenceSchema,
  faultSourceTypeSchema,
  faultTypeSchema,
  faultWarningCodeSchema,
  faultWarningSeveritySchema,
  neutralEarthingModeSchema,
  shortCircuitCaseSchema,
  sourceRepresentationSchema,
} from "./faultContract";

const optionalRequestText = (maxLength: number) =>
  z.string().trim().max(maxLength).nullable().optional();

export const sequenceImpedanceRequestSchema = z
  .object({
    resistance_ohm: exactDecimalSchema,
    reactance_ohm: exactDecimalSchema,
  })
  .strict();

export const faultBusRequestSchema = z
  .object({
    code: z.string().trim().min(1).max(80),
    name: z.string().trim().min(1).max(200),
    nominal_voltage_v: exactDecimalSchema,
    voltage_factor_max: exactDecimalSchema,
    voltage_factor_min: exactDecimalSchema,
    neutral_earthing_mode: neutralEarthingModeSchema,
    neutral_resistance_ohm: exactDecimalSchema.optional(),
    neutral_reactance_ohm: exactDecimalSchema.optional(),
    sld_node_code: optionalRequestText(80),
    notes: optionalRequestText(1000),
  })
  .strict();

export const faultSourceRequestSchema = z
  .object({
    code: z.string().trim().min(1).max(80),
    name: z.string().trim().min(1).max(200),
    bus_code: z.string().trim().min(1).max(80),
    source_type: faultSourceTypeSchema,
    representation: sourceRepresentationSchema,
    positive_sequence_impedance: sequenceImpedanceRequestSchema.nullable().optional(),
    negative_sequence_impedance: sequenceImpedanceRequestSchema.nullable().optional(),
    zero_sequence_impedance: sequenceImpedanceRequestSchema.nullable().optional(),
    current_contribution_ka: exactDecimalSchema.nullable().optional(),
    in_service: z.boolean().optional(),
    contribution_factor: exactDecimalSchema.optional(),
    equipment_reference: optionalRequestText(120),
    notes: optionalRequestText(1000),
  })
  .strict();

export const faultBranchRequestSchema = z
  .object({
    code: z.string().trim().min(1).max(80),
    name: z.string().trim().min(1).max(200),
    from_bus_code: z.string().trim().min(1).max(80),
    to_bus_code: z.string().trim().min(1).max(80),
    branch_type: faultBranchTypeSchema,
    positive_sequence_impedance: sequenceImpedanceRequestSchema,
    negative_sequence_impedance: sequenceImpedanceRequestSchema.nullable().optional(),
    zero_sequence_impedance: sequenceImpedanceRequestSchema.nullable().optional(),
    parallel_circuits: z.number().int().positive().optional(),
    in_service: z.boolean().optional(),
    equipment_reference: optionalRequestText(120),
    notes: optionalRequestText(1000),
  })
  .strict();

export const faultLocationRequestSchema = z
  .object({
    bus_code: z.string().trim().min(1).max(80),
    fault_type: faultTypeSchema,
    fault_resistance_ohm: exactDecimalSchema.optional(),
    fault_reactance_ohm: exactDecimalSchema.optional(),
    clearing_time_s: exactDecimalSchema.nullable().optional(),
    description: optionalRequestText(500),
  })
  .strict();

export const shortCircuitStudyRequestSchema = z
  .object({
    code: z.string().trim().min(1).max(80),
    name: z.string().trim().min(1).max(200),
    calculation_case: shortCircuitCaseSchema,
    fault: faultLocationRequestSchema,
    buses: z.array(faultBusRequestSchema).min(1),
    sources: z.array(faultSourceRequestSchema).min(1),
    branches: z.array(faultBranchRequestSchema).optional(),
    frequency_hz: exactDecimalSchema.optional(),
    operating_state_code: optionalRequestText(80),
    standard_reference: z.string().trim().min(1).max(200).optional(),
    earth_current_reference: z.string().trim().min(1).max(200).optional(),
    notes: optionalRequestText(2000),
  })
  .strict();

const faultEngineeringWarningResponseSchema = z
  .object({
    code: faultWarningCodeSchema,
    severity: faultWarningSeveritySchema,
    message: z.string().min(1),
    reference_code: z.string().min(1).nullable(),
  })
  .strict();

const equivalentSequenceImpedanceResponseSchema = z
  .object({
    sequence: faultSequenceSchema,
    available: z.boolean(),
    resistance_ohm: exactDecimalSchema.nullable(),
    reactance_ohm: exactDecimalSchema.nullable(),
    path_reference_codes: z.array(z.string().min(1)),
    blocking_reference_codes: z.array(z.string().min(1)),
  })
  .strict();

const faultSourceContributionResponseSchema = z
  .object({
    source_code: z.string().min(1),
    source_type: faultSourceTypeSchema,
    representation: sourceRepresentationSchema,
    included: z.boolean(),
    initial_symmetrical_current_ka: exactDecimalSchema,
    peak_current_ka: exactDecimalSchema.nullable(),
    exclusion_reason: z.string().min(1).nullable(),
  })
  .strict();

export const shortCircuitStudyResponseSchema = z
  .object({
    study_code: z.string().min(1),
    study_name: z.string().min(1),
    calculation_case: shortCircuitCaseSchema,
    fault_bus_code: z.string().min(1),
    fault_type: faultTypeSchema,
    nominal_voltage_v: exactDecimalSchema,
    frequency_hz: exactDecimalSchema,
    status: faultResultStatusSchema,
    initial_symmetrical_short_circuit_current_ka: exactDecimalSchema.nullable(),
    peak_short_circuit_current_ka: exactDecimalSchema.nullable(),
    symmetrical_breaking_current_ka: exactDecimalSchema.nullable(),
    steady_state_short_circuit_current_ka: exactDecimalSchema.nullable(),
    thermal_equivalent_short_circuit_current_ka: exactDecimalSchema.nullable(),
    earth_fault_current_ka: exactDecimalSchema.nullable(),
    kappa_factor: exactDecimalSchema.nullable(),
    x_r_ratio: exactDecimalSchema.nullable(),
    clearing_time_s: exactDecimalSchema.nullable(),
    sequence_results: z.array(equivalentSequenceImpedanceResponseSchema),
    source_contributions: z.array(faultSourceContributionResponseSchema),
    warnings: z.array(faultEngineeringWarningResponseSchema),
    standard_reference: z.string().min(1),
    earth_current_reference: z.string().min(1),
    operating_state_code: z.string().nullable(),
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

export type SequenceImpedanceRequest = z.infer<typeof sequenceImpedanceRequestSchema>;
export type FaultBusRequest = z.infer<typeof faultBusRequestSchema>;
export type FaultSourceRequest = z.infer<typeof faultSourceRequestSchema>;
export type FaultBranchRequest = z.infer<typeof faultBranchRequestSchema>;
export type FaultLocationRequest = z.infer<typeof faultLocationRequestSchema>;
export type ShortCircuitStudyRequest = z.infer<typeof shortCircuitStudyRequestSchema>;
export type ShortCircuitStudyResponse = z.infer<typeof shortCircuitStudyResponseSchema>;

function formatApiError(data: unknown, status: number): string {
  const parsed = errorResponseSchema.safeParse(data);

  if (!parsed.success) {
    return `Fault calculation failed (HTTP ${status}).`;
  }

  if (typeof parsed.data.detail === "string") {
    return parsed.data.detail;
  }

  return parsed.data.detail
    .map((item) => `${item.loc.join(".")}: ${item.msg}`)
    .join("; ");
}

export async function calculateFaultStudy(
  payload: ShortCircuitStudyRequest,
  signal?: AbortSignal,
): Promise<ShortCircuitStudyResponse> {
  const validatedPayload = shortCircuitStudyRequestSchema.parse(payload);
  const timeoutSignal = AbortSignal.timeout(30_000);
  const requestSignal = signal
    ? AbortSignal.any([signal, timeoutSignal])
    : timeoutSignal;

  const response = await fetch("/api/v1/electrical/fault/calculate", {
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
    throw new Error(formatApiError(data, response.status));
  }

  const parsed = shortCircuitStudyResponseSchema.safeParse(data);

  if (!parsed.success) {
    throw new Error("Unexpected response from the KES Electrical OS fault API.");
  }

  return parsed.data;
}
