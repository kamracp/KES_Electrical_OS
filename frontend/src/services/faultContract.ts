import { z } from "zod";

export const exactDecimalSchema = z
  .string()
  .trim()
  .min(1, "Decimal value is required.")
  .regex(
    /^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/,
    "Value must be an exact decimal string.",
  );

export const faultTypeSchema = z.enum([
  "THREE_PHASE",
  "TWO_PHASE",
  "TWO_PHASE_TO_EARTH",
  "SINGLE_PHASE_TO_EARTH",
]);

export const shortCircuitCaseSchema = z.enum([
  "MAXIMUM",
  "MINIMUM",
]);

export const faultSourceTypeSchema = z.enum([
  "UTILITY_GRID",
  "SYNCHRONOUS_GENERATOR",
  "ASYNCHRONOUS_MOTOR",
  "INVERTER_BASED_RESOURCE",
  "EQUIVALENT_SOURCE",
]);

export const sourceRepresentationSchema = z.enum([
  "VOLTAGE_BEHIND_IMPEDANCE",
  "CURRENT_INJECTION",
]);

export const faultBranchTypeSchema = z.enum([
  "CABLE",
  "OVERHEAD_LINE",
  "TRANSFORMER",
  "BUSBAR",
  "BUSDUCT",
  "REACTOR",
  "EQUIVALENT",
]);

export const neutralEarthingModeSchema = z.enum([
  "SOLIDLY_EARTHED",
  "RESISTANCE_EARTHED",
  "REACTANCE_EARTHED",
  "RESONANT_EARTHED",
  "ISOLATED",
]);

export const faultResultStatusSchema = z.enum([
  "CALCULATED",
  "WARNING",
  "INDETERMINATE",
]);

export const faultSequenceSchema = z.enum([
  "POSITIVE",
  "NEGATIVE",
  "ZERO",
]);

export const faultWarningSeveritySchema = z.enum([
  "WARNING",
  "ERROR",
]);

export const faultWarningCodeSchema = z.enum([
  "NO_FAULT_CURRENT_PATH",
  "ZERO_SEQUENCE_PATH_BLOCKED",
  "INCOMPLETE_SEQUENCE_DATA",
  "CURRENT_INJECTION_APPROXIMATION",
  "PEAK_CURRENT_NOT_EVALUATED",
  "BREAKING_CURRENT_NOT_EVALUATED",
  "STEADY_STATE_CURRENT_NOT_EVALUATED",
  "THERMAL_CURRENT_NOT_EVALUATED",
  "ENGINEERING_REVIEW_REQUIRED",
  "CALCULATION_FAILED",
]);

export type ExactDecimal = z.infer<typeof exactDecimalSchema>;
export type FaultType = z.infer<typeof faultTypeSchema>;
export type ShortCircuitCase = z.infer<typeof shortCircuitCaseSchema>;
export type FaultSourceType = z.infer<typeof faultSourceTypeSchema>;
export type SourceRepresentation = z.infer<typeof sourceRepresentationSchema>;
export type FaultBranchType = z.infer<typeof faultBranchTypeSchema>;
export type NeutralEarthingMode = z.infer<typeof neutralEarthingModeSchema>;
export type FaultResultStatus = z.infer<typeof faultResultStatusSchema>;
export type FaultSequence = z.infer<typeof faultSequenceSchema>;
export type FaultWarningSeverity = z.infer<typeof faultWarningSeveritySchema>;
export type FaultWarningCode = z.infer<typeof faultWarningCodeSchema>;
