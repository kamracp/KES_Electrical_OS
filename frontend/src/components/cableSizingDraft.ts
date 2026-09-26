// Draft model of the Cable sizing study form: what the user is typing, kept apart from the
// component so the payload rules sit next to the draft they read. Every value is held as the
// string the user typed; the three switches are booleans.

export type CableSizingDraft = {
  studyCode: string;
  studyName: string;
  notes: string;
  designCurrentA: string;
  nominalVoltageV: string;
  routeLengthM: string;
  system: string;
  jurisdictionProfile: string;
  powerFactor: string;
  allowableVoltageDropPercent: string;
  faultCurrentKa: string;
  faultDurationS: string;
  harmonicNeutralFactor: string;
  conductorMaterial: string;
  insulationMaterial: string;
  construction: string;
  arrangement: string;
  numberOfLoadedConductors: string;
  parallelRuns: string;
  neutralRequired: boolean;
  reducedNeutralPermitted: boolean;
  protectiveConductorType: string;
  armoured: boolean;
  method: string;
  ambientTemperatureC: string;
  ambientDeratingFactor: string;
  groupingDeratingFactor: string;
  thermalInsulationFactor: string;
  depthDeratingFactor: string;
  soilThermalResistivityFactor: string;
  groupedCircuits: string;
  burialDepthM: string;
  soilThermalResistivityKMPerW: string;
  conductorSpacingMm: string;
  phaseSizesMm2: string;
  neutralSizesMm2: string;
  protectiveSizesMm2: string;
};

export function createInitialCableSizingDraft(): CableSizingDraft {
  return {
    studyCode: "",
    studyName: "",
    notes: "",
    designCurrentA: "",
    nominalVoltageV: "",
    routeLengthM: "",
    system: "",
    jurisdictionProfile: "IN",
    powerFactor: "",
    allowableVoltageDropPercent: "",
    faultCurrentKa: "",
    faultDurationS: "",
    harmonicNeutralFactor: "",
    conductorMaterial: "",
    insulationMaterial: "",
    construction: "",
    arrangement: "",
    numberOfLoadedConductors: "",
    parallelRuns: "",
    neutralRequired: true,
    reducedNeutralPermitted: false,
    protectiveConductorType: "",
    armoured: false,
    method: "",
    ambientTemperatureC: "",
    ambientDeratingFactor: "",
    groupingDeratingFactor: "",
    thermalInsulationFactor: "",
    depthDeratingFactor: "",
    soilThermalResistivityFactor: "",
    groupedCircuits: "",
    burialDepthM: "",
    soilThermalResistivityKMPerW: "",
    conductorSpacingMm: "",
    phaseSizesMm2: "",
    neutralSizesMm2: "",
    protectiveSizesMm2: "",
  };
}

/** Empty text means "not supplied": the backend default applies. */
function optional(value: string): string | undefined {
  return value.trim() === "" ? undefined : value.trim();
}

function optionalInt(value: string): number | undefined {
  const text = value.trim();
  return text === "" ? undefined : Number(text);
}

/** Drop undefined entries so "not supplied" fields are absent, not null-ish. */
function compact<T extends Record<string, unknown>>(value: T): T {
  return Object.fromEntries(
    Object.entries(value).filter(([, item]) => item !== undefined),
  ) as T;
}

/** Comma-separated sizes -> trimmed exact-decimal strings; empty -> undefined. */
function sizeList(value: string): string[] | undefined {
  const items = value
    .split(",")
    .map((item) => item.trim())
    .filter((item) => item !== "");
  return items.length === 0 ? undefined : items;
}

/** The request body as the form sends it; validated afterwards with cableSizingRequestSchema. */
export function buildCableSizingPayload(draft: CableSizingDraft) {
  return compact({
    code: draft.studyCode,
    name: draft.studyName,
    jurisdiction_profile: draft.jurisdictionProfile,
    circuit: compact({
      design_current_a: draft.designCurrentA,
      nominal_voltage_v: draft.nominalVoltageV,
      route_length_m: draft.routeLengthM,
      system: draft.system,
      power_factor: optional(draft.powerFactor),
      allowable_voltage_drop_percent: optional(draft.allowableVoltageDropPercent),
      fault_current_ka: optional(draft.faultCurrentKa),
      fault_duration_s: optional(draft.faultDurationS),
      harmonic_neutral_factor: optional(draft.harmonicNeutralFactor),
    }),
    cable: compact({
      conductor_material: draft.conductorMaterial,
      insulation_material: draft.insulationMaterial,
      construction: draft.construction,
      arrangement: draft.arrangement,
      number_of_loaded_conductors: Number(draft.numberOfLoadedConductors),
      parallel_runs: optionalInt(draft.parallelRuns),
      neutral_required: draft.neutralRequired,
      reduced_neutral_permitted: draft.reducedNeutralPermitted,
      protective_conductor_type: optional(draft.protectiveConductorType),
      armoured: draft.armoured,
    }),
    installation: compact({
      method: draft.method,
      ambient_temperature_c: draft.ambientTemperatureC,
      ambient_derating_factor: optional(draft.ambientDeratingFactor),
      grouping_derating_factor: optional(draft.groupingDeratingFactor),
      thermal_insulation_factor: optional(draft.thermalInsulationFactor),
      depth_derating_factor: optional(draft.depthDeratingFactor),
      soil_thermal_resistivity_factor: optional(draft.soilThermalResistivityFactor),
      grouped_circuits: optionalInt(draft.groupedCircuits),
      burial_depth_m: optional(draft.burialDepthM),
      soil_thermal_resistivity_k_m_per_w: optional(draft.soilThermalResistivityKMPerW),
      conductor_spacing_mm: optional(draft.conductorSpacingMm),
    }),
    size_schedule: compact({
      phase_sizes_mm2: sizeList(draft.phaseSizesMm2) ?? [],
      neutral_sizes_mm2: sizeList(draft.neutralSizesMm2),
      protective_sizes_mm2: sizeList(draft.protectiveSizesMm2),
    }),
    notes: optional(draft.notes),
  });
}
