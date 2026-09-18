import type { ValidationLabels } from "../utils/validationMessages";

// On-screen labels of the Cable sizing form, keyed by the request path, so a
// validation message names a field the way the form does. CableSizingForm.test
// checks that every field label below is present on the form.
export const CABLE_SIZING_LABELS: ValidationLabels = {
  fields: {
    code: "Study code",
    name: "Study name",
    notes: "Notes",
    jurisdiction_profile: "Jurisdiction profile",
    "circuit.design_current_a": "Design current (A)",
    "circuit.nominal_voltage_v": "Nominal voltage (V)",
    "circuit.route_length_m": "Route length (m)",
    "circuit.system": "System",
    "circuit.power_factor": "Power factor",
    "circuit.allowable_voltage_drop_percent": "Allowable voltage drop (%)",
    "circuit.fault_current_ka": "Fault current (kA)",
    "circuit.fault_duration_s": "Fault duration (s)",
    "circuit.harmonic_neutral_factor": "Harmonic neutral factor",
    "cable.conductor_material": "Conductor material",
    "cable.insulation_material": "Insulation",
    "cable.construction": "Construction",
    "cable.arrangement": "Arrangement",
    "cable.number_of_loaded_conductors": "Loaded conductors",
    "cable.parallel_runs": "Parallel runs",
    "cable.neutral_required": "Neutral required",
    "cable.reduced_neutral_permitted": "Reduced neutral permitted",
    "cable.protective_conductor_type": "Protective conductor",
    "cable.armoured": "Armoured",
    "installation.method": "Installation method",
    "installation.ambient_temperature_c": "Ambient temperature (°C)",
    "installation.ambient_derating_factor": "Ambient derating factor",
    "installation.grouping_derating_factor": "Grouping derating factor",
    "installation.thermal_insulation_factor": "Thermal insulation factor",
    "installation.depth_derating_factor": "Depth derating factor",
    "installation.soil_thermal_resistivity_factor": "Soil thermal resistivity factor",
    "installation.grouped_circuits": "Grouped circuits",
    "installation.burial_depth_m": "Burial depth (m)",
    "installation.soil_thermal_resistivity_k_m_per_w": "Soil thermal resistivity (K·m/W)",
    "installation.conductor_spacing_mm": "Conductor spacing (mm)",
    "size_schedule.phase_sizes_mm2": "Phase sizes",
    "size_schedule.neutral_sizes_mm2": "Neutral sizes",
    "size_schedule.protective_sizes_mm2": "Protective sizes",
  },
  // One entry of a size list: "Phase size 2".
  groups: {
    phase_sizes_mm2: "Phase size",
    neutral_sizes_mm2: "Neutral size",
    protective_sizes_mm2: "Protective size",
  },
};
