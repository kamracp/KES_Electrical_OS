import { z } from "zod";

// The controlled vocabularies of the transformer sizing module (EOS-03a),
// copied verbatim from the backend so a value the API can send is never
// rejected here. Sources: backend/app/domain/electrical/sources/results.py
// (TransformerSizingStatus, TransformerSizingWarningCode) and .../sources/models.py
// (TransformerRedundancyMode). transformerSizingContract.test.ts pins each list.
//
// The operating scenario is the same enum the load module uses, so it is reused
// from loadDemandContract rather than written out a second time.

export const transformerSizingStatusSchema = z.enum([
  "VALID",
  "WARNING",
  "REVIEW_REQUIRED",
  "NO_SOLUTION",
]);

export const transformerSizingWarningCodeSchema = z.enum([
  "DERATING_APPLIED",
  "NO_STANDARD_RATING_AVAILABLE",
  "GROWTH_FACTOR_NOT_ESTABLISHED",
  "DESIGN_MARGIN_NOT_ESTABLISHED",
  "AMBIENT_DERATING_NOT_ESTABLISHED",
  "ALTITUDE_DERATING_NOT_ESTABLISHED",
  "HARMONIC_DERATING_NOT_ESTABLISHED",
]);

export const transformerRedundancyModeSchema = z.enum([
  "NONE",
  "N_PLUS_1",
  "TWO_N",
]);

/** The five warnings that make a result REVIEW_REQUIRED rather than WARNING. */
export const NOT_ESTABLISHED_WARNING_CODES = [
  "GROWTH_FACTOR_NOT_ESTABLISHED",
  "DESIGN_MARGIN_NOT_ESTABLISHED",
  "AMBIENT_DERATING_NOT_ESTABLISHED",
  "ALTITUDE_DERATING_NOT_ESTABLISHED",
  "HARMONIC_DERATING_NOT_ESTABLISHED",
] as const;

/** The message the backend returns when the demand power factor is missing. */
export const DEMAND_POWER_FACTOR_REQUIRED = "demand_power_factor is required";

export type TransformerSizingStatus = z.infer<typeof transformerSizingStatusSchema>;
export type TransformerSizingWarningCode = z.infer<typeof transformerSizingWarningCodeSchema>;
export type TransformerRedundancyMode = z.infer<typeof transformerRedundancyModeSchema>;
