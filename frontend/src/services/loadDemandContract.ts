import { z } from "zod";

// The controlled vocabularies of the load and demand module (EOS-02), copied
// verbatim from the backend so a value the API can send is never rejected here.
// Sources: backend/app/domain/electrical/loads/models.py (PhaseSystem,
// LoadScenario, PowerBasis) and .../loads/results.py (CalculationStatus,
// LoadWarningCode). loadDemandContract.test.ts pins each list against them.

export const phaseSystemSchema = z.enum([
  "SINGLE_PHASE",
  "THREE_PHASE",
  "DC",
]);

export const loadScenarioSchema = z.enum([
  "NORMAL",
  "EMERGENCY",
  "OUTAGE",
  "STARTING",
  "UPS",
  "PV",
  "FUTURE",
]);

export const powerBasisSchema = z.enum([
  "ELECTRICAL_INPUT",
  "MECHANICAL_OUTPUT",
]);

// REVIEW_REQUIRED outranks WARNING: it means a factor was not established and
// the figures were produced with an assumed 1 (Master Prompt A15 (a)).
export const loadCalculationStatusSchema = z.enum([
  "VALID",
  "WARNING",
  "REVIEW_REQUIRED",
]);

export const loadWarningCodeSchema = z.enum([
  "ZERO_DEMAND",
  "UTILIZATION_FACTOR_NOT_ESTABLISHED",
  "DEMAND_FACTOR_NOT_ESTABLISHED",
  "EFFICIENCY_NOT_ESTABLISHED",
  "COINCIDENCE_FACTOR_NOT_ESTABLISHED",
]);

/** The four warnings that make a result REVIEW_REQUIRED rather than WARNING. */
export const NOT_ESTABLISHED_WARNING_CODES = [
  "UTILIZATION_FACTOR_NOT_ESTABLISHED",
  "DEMAND_FACTOR_NOT_ESTABLISHED",
  "EFFICIENCY_NOT_ESTABLISHED",
  "COINCIDENCE_FACTOR_NOT_ESTABLISHED",
] as const;

/** The message the backend returns when an AC load carries no power factor. */
export const AC_POWER_FACTOR_REQUIRED = "power_factor is required for AC loads";

export type PhaseSystem = z.infer<typeof phaseSystemSchema>;
export type LoadScenario = z.infer<typeof loadScenarioSchema>;
export type PowerBasis = z.infer<typeof powerBasisSchema>;
export type LoadCalculationStatus = z.infer<typeof loadCalculationStatusSchema>;
export type LoadWarningCode = z.infer<typeof loadWarningCodeSchema>;
