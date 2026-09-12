import { z } from "zod";

export {
  exactDecimalSchema,
  type ExactDecimal,
} from "./faultContract";

export const conductorMaterialSchema = z.enum([
  "COPPER",
  "ALUMINIUM",
]);

export const insulationMaterialSchema = z.enum([
  "PVC",
  "XLPE",
  "EPR",
  "MINERAL",
]);

export const cableConstructionSchema = z.enum([
  "SINGLE_CORE",
  "MULTICORE",
]);

export const circuitSystemSchema = z.enum([
  "DC_TWO_WIRE",
  "SINGLE_PHASE_AC",
  "THREE_PHASE_THREE_WIRE",
  "THREE_PHASE_FOUR_WIRE",
]);

export const installationMethodSchema = z.enum([
  "A1_INSULATED_WALL_CONDUIT",
  "A2_INSULATED_WALL_MULTICORE",
  "B1_WALL_CONDUIT_SINGLE_CORE",
  "B2_WALL_CONDUIT_MULTICORE",
  "C_CLIPPED_DIRECT",
  "D1_GROUND_DUCT",
  "D2_DIRECT_BURIED",
  "E_FREE_AIR_MULTICORE",
  "F_FREE_AIR_TOUCHING_SINGLE_CORE",
  "G_FREE_AIR_SPACED_SINGLE_CORE",
  "CABLE_TRAY",
  "CABLE_LADDER",
  "ENGINEERED_IEC_60287",
]);

export const conductorArrangementSchema = z.enum([
  "MULTICORE",
  "FLAT_TOUCHING",
  "FLAT_SPACED",
  "TREFOIL_TOUCHING",
  "TREFOIL_SPACED",
]);

export const protectiveConductorTypeSchema = z.enum([
  "INTEGRAL_CORE",
  "SEPARATE_INSULATED",
  "SEPARATE_BARE",
  "METALLIC_SCREEN",
  "METALLIC_ARMOUR",
  "NONE",
]);

export const cableCheckStatusSchema = z.enum([
  "PASS",
  "FAIL",
  "NOT_APPLICABLE",
]);

export const cableSizingStatusSchema = z.enum([
  "DESIGN_CHECK_PASSED",
  "DESIGN_CHECK_FAILED",
  "NO_STANDARD_SIZE_AVAILABLE",
]);

export const cableWarningCodeSchema = z.enum([
  "AMPACITY_INADEQUATE",
  "VOLTAGE_DROP_EXCEEDED",
  "SHORT_CIRCUIT_WITHSTAND_INADEQUATE",
  "NEUTRAL_SIZE_INADEQUATE",
  "PROTECTIVE_CONDUCTOR_INADEQUATE",
  "HIGH_TOTAL_DERATING",
  "PARALLEL_CABLE_CURRENT_SHARING",
  "SOIL_DATA_REQUIRED",
  "NO_STANDARD_SIZE_AVAILABLE",
]);

export type ConductorMaterial = z.infer<typeof conductorMaterialSchema>;
export type InsulationMaterial = z.infer<typeof insulationMaterialSchema>;
export type CableConstruction = z.infer<typeof cableConstructionSchema>;
export type CircuitSystem = z.infer<typeof circuitSystemSchema>;
export type InstallationMethod = z.infer<typeof installationMethodSchema>;
export type ConductorArrangement = z.infer<
  typeof conductorArrangementSchema
>;
export type ProtectiveConductorType = z.infer<
  typeof protectiveConductorTypeSchema
>;
export type CableCheckStatus = z.infer<typeof cableCheckStatusSchema>;
export type CableSizingStatus = z.infer<typeof cableSizingStatusSchema>;
export type CableWarningCode = z.infer<typeof cableWarningCodeSchema>;
