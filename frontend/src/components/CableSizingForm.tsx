import { useState, type FormEvent } from "react";

import {
  cableSizingRequestSchema,
  type CableSizingRequest,
} from "../services/cable";

type CableSizingFormProps = {
  disabled?: boolean;
  onSubmit: (payload: CableSizingRequest) => void | Promise<void>;
};

type CableSizingDraft = {
  studyCode: string;
  studyName: string;
  notes: string;
  designCurrentA: string;
  nominalVoltageV: string;
  routeLengthM: string;
  system: string;
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

const initialDraft: CableSizingDraft = {
  studyCode: "",
  studyName: "",
  notes: "",
  designCurrentA: "",
  nominalVoltageV: "",
  routeLengthM: "",
  system: "",
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

export function CableSizingForm({ disabled = false, onSubmit }: CableSizingFormProps) {
  const [draft, setDraft] = useState<CableSizingDraft>(initialDraft);
  const [validationError, setValidationError] = useState<string | null>(null);

  function updateField<K extends keyof CableSizingDraft>(
    field: K,
    value: CableSizingDraft[K],
  ) {
    setDraft((current) => ({ ...current, [field]: value }));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setValidationError(null);

    const payload = compact({
      code: draft.studyCode,
      name: draft.studyName,
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

    const parsed = cableSizingRequestSchema.safeParse(payload);

    if (!parsed.success) {
      const issue = parsed.error.issues[0];
      const location = issue?.path.length ? `${issue.path.join(".")}: ` : "";
      setValidationError(
        issue ? `${location}${issue.message}` : "Review the cable sizing inputs.",
      );
      return;
    }

    await onSubmit(parsed.data);
  }

  const text = (
    label: string,
    field: keyof CableSizingDraft,
    decimal = false,
  ) => (
    <label>
      {label}
      <input
        inputMode={decimal ? "decimal" : undefined}
        name={field}
        value={String(draft[field])}
        onChange={(event) => updateField(field, event.target.value as never)}
      />
    </label>
  );

  const check = (label: string, field: keyof CableSizingDraft) => (
    <label>
      <input
        type="checkbox"
        name={field}
        checked={Boolean(draft[field])}
        onChange={(event) => updateField(field, event.target.checked as never)}
      />
      {label}
    </label>
  );

  return (
    <form aria-label="Cable sizing inputs" onSubmit={handleSubmit}>
      <fieldset disabled={disabled}>
        <legend>Study definition</legend>
        {text("Study code", "studyCode")}
        {text("Study name", "studyName")}
        {text("Notes", "notes")}
        <p>
          References: IEC 60364-5-52 (selection) and IEC 60287 (ampacity) as
          registered in the reference register; editions are unverified until
          confirmed there.
        </p>
      </fieldset>

      <fieldset disabled={disabled}>
        <legend>Circuit</legend>
        {text("Design current (A)", "designCurrentA", true)}
        {text("Nominal voltage (V)", "nominalVoltageV", true)}
        {text("Route length (m)", "routeLengthM", true)}
        <label>
          System
          <select
            name="system"
            value={draft.system}
            onChange={(event) => updateField("system", event.target.value)}
          >
            <option value="">Select system</option>
            <option value="DC_TWO_WIRE">DC two-wire</option>
            <option value="SINGLE_PHASE_AC">Single-phase AC</option>
            <option value="THREE_PHASE_THREE_WIRE">Three-phase three-wire</option>
            <option value="THREE_PHASE_FOUR_WIRE">Three-phase four-wire</option>
          </select>
        </label>
        {text("Power factor", "powerFactor", true)}
        {text("Allowable voltage drop (%)", "allowableVoltageDropPercent", true)}
        {text("Fault current (kA)", "faultCurrentKa", true)}
        {text("Fault duration (s)", "faultDurationS", true)}
        {text("Harmonic neutral factor", "harmonicNeutralFactor", true)}
      </fieldset>

      <fieldset disabled={disabled}>
        <legend>Cable</legend>
        <label>
          Conductor material
          <select
            name="conductorMaterial"
            value={draft.conductorMaterial}
            onChange={(event) => updateField("conductorMaterial", event.target.value)}
          >
            <option value="">Select material</option>
            <option value="COPPER">Copper</option>
            <option value="ALUMINIUM">Aluminium</option>
          </select>
        </label>
        <label>
          Insulation
          <select
            name="insulationMaterial"
            value={draft.insulationMaterial}
            onChange={(event) => updateField("insulationMaterial", event.target.value)}
          >
            <option value="">Select insulation</option>
            <option value="PVC">PVC</option>
            <option value="XLPE">XLPE</option>
            <option value="EPR">EPR</option>
            <option value="MINERAL">Mineral</option>
          </select>
        </label>
        <label>
          Construction
          <select
            name="construction"
            value={draft.construction}
            onChange={(event) => updateField("construction", event.target.value)}
          >
            <option value="">Select construction</option>
            <option value="SINGLE_CORE">Single-core</option>
            <option value="MULTICORE">Multicore</option>
          </select>
        </label>
        <label>
          Arrangement
          <select
            name="arrangement"
            value={draft.arrangement}
            onChange={(event) => updateField("arrangement", event.target.value)}
          >
            <option value="">Select arrangement</option>
            <option value="MULTICORE">Multicore</option>
            <option value="FLAT_TOUCHING">Flat touching</option>
            <option value="FLAT_SPACED">Flat spaced</option>
            <option value="TREFOIL_TOUCHING">Trefoil touching</option>
            <option value="TREFOIL_SPACED">Trefoil spaced</option>
          </select>
        </label>
        {text("Loaded conductors", "numberOfLoadedConductors")}
        {text("Parallel runs", "parallelRuns")}
        <label>
          Protective conductor
          <select
            name="protectiveConductorType"
            value={draft.protectiveConductorType}
            onChange={(event) => updateField("protectiveConductorType", event.target.value)}
          >
            <option value="">Backend default</option>
            <option value="INTEGRAL_CORE">Integral core</option>
            <option value="SEPARATE_INSULATED">Separate insulated</option>
            <option value="SEPARATE_BARE">Separate bare</option>
            <option value="METALLIC_SCREEN">Metallic screen</option>
            <option value="METALLIC_ARMOUR">Metallic armour</option>
            <option value="NONE">None</option>
          </select>
        </label>
        {check("Neutral required", "neutralRequired")}
        {check("Reduced neutral permitted", "reducedNeutralPermitted")}
        {check("Armoured", "armoured")}
      </fieldset>

      <fieldset disabled={disabled}>
        <legend>Installation</legend>
        <label>
          Installation method
          <select
            name="method"
            value={draft.method}
            onChange={(event) => updateField("method", event.target.value)}
          >
            <option value="">Select method</option>
            <option value="A1_INSULATED_WALL_CONDUIT">A1 insulated wall, conduit</option>
            <option value="A2_INSULATED_WALL_MULTICORE">A2 insulated wall, multicore</option>
            <option value="B1_WALL_CONDUIT_SINGLE_CORE">B1 wall conduit, single-core</option>
            <option value="B2_WALL_CONDUIT_MULTICORE">B2 wall conduit, multicore</option>
            <option value="C_CLIPPED_DIRECT">C clipped direct</option>
            <option value="D1_GROUND_DUCT">D1 ground duct</option>
            <option value="D2_DIRECT_BURIED">D2 direct buried</option>
            <option value="E_FREE_AIR_MULTICORE">E free air, multicore</option>
            <option value="F_FREE_AIR_TOUCHING_SINGLE_CORE">F free air, touching single-core</option>
            <option value="G_FREE_AIR_SPACED_SINGLE_CORE">G free air, spaced single-core</option>
            <option value="CABLE_TRAY">Cable tray</option>
            <option value="CABLE_LADDER">Cable ladder</option>
            <option value="ENGINEERED_IEC_60287">Engineered (IEC 60287)</option>
          </select>
        </label>
        {text("Ambient temperature (°C)", "ambientTemperatureC", true)}
        {text("Ambient derating factor", "ambientDeratingFactor", true)}
        {text("Grouping derating factor", "groupingDeratingFactor", true)}
        {text("Thermal insulation factor", "thermalInsulationFactor", true)}
        {text("Depth derating factor", "depthDeratingFactor", true)}
        {text("Soil thermal resistivity factor", "soilThermalResistivityFactor", true)}
        {text("Grouped circuits", "groupedCircuits")}
        {text("Burial depth (m)", "burialDepthM", true)}
        {text("Soil thermal resistivity (K·m/W)", "soilThermalResistivityKMPerW", true)}
        {text("Conductor spacing (mm)", "conductorSpacingMm", true)}
      </fieldset>

      <fieldset disabled={disabled}>
        <legend>Size schedule (mm², comma-separated, ascending)</legend>
        {text("Phase sizes", "phaseSizesMm2")}
        {text("Neutral sizes", "neutralSizesMm2")}
        {text("Protective sizes", "protectiveSizesMm2")}
      </fieldset>

      {validationError ? <p role="alert">{validationError}</p> : null}

      <button disabled={disabled} type="submit">
        Calculate cable sizing
      </button>
    </form>
  );
}
