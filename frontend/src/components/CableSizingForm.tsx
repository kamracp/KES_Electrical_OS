import { useState, type FormEvent } from "react";

import {
  cableSizingRequestSchema,
  type CableSizingRequest,
} from "../services/cable";
import { describeValidationIssue } from "../utils/validationMessages";
import { CABLE_SIZING_LABELS } from "./cableSizingLabels";
import {
  buildCableSizingPayload,
  createInitialCableSizingDraft,
  type CableSizingDraft,
} from "./cableSizingDraft";

type CableSizingFormProps = {
  disabled?: boolean;
  onSubmit: (payload: CableSizingRequest) => void | Promise<void>;
};

export function CableSizingForm({ disabled = false, onSubmit }: CableSizingFormProps) {
  const [draft, setDraft] = useState<CableSizingDraft>(createInitialCableSizingDraft);
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

    const parsed = cableSizingRequestSchema.safeParse(buildCableSizingPayload(draft));

    if (!parsed.success) {
      const issue = parsed.error.issues[0];
      setValidationError(
        issue
          ? describeValidationIssue(issue, CABLE_SIZING_LABELS)
          : "Review the cable sizing inputs.",
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
        <label>
          Jurisdiction profile
          <select
            name="jurisdictionProfile"
            value={draft.jurisdictionProfile}
            onChange={(event) => updateField("jurisdictionProfile", event.target.value)}
          >
            <option value="IN">India (CEA Regulations, IS, CPWD)</option>
            <option value="IEC">IEC (international, no national layer)</option>
            <option value="UK">United Kingdom (BS 7671) - reference data pending</option>
            <option value="EU">European Union (HD 60364) - reference data pending</option>
            <option value="US">United States (NEC / NFPA 70) - reference data pending</option>
            <option value="AU_NZ">Australia / New Zealand (AS/NZS 3000) - reference data pending</option>
          </select>
        </label>
        <p>
          The jurisdiction profile governs reference precedence and ambient
          conventions; engine physics does not change with the profile.
        </p>
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
