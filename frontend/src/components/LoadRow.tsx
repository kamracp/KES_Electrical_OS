import {
  loadScenarioSchema,
  phaseSystemSchema,
  powerBasisSchema,
  type LoadScenario,
  type PhaseSystem,
  type PowerBasis,
} from "../services/loadDemandContract";
import type { LoadRowDraft } from "./loadStudyDraft";

// Exhaustive maps: a new enum member without a label is a compile error.
const PHASE_SYSTEM_LABELS: Record<PhaseSystem, string> = {
  SINGLE_PHASE: "Single-phase",
  THREE_PHASE: "Three-phase",
  DC: "DC",
};

const SCENARIO_LABELS: Record<LoadScenario, string> = {
  NORMAL: "Normal",
  EMERGENCY: "Emergency",
  OUTAGE: "Outage",
  STARTING: "Starting",
  UPS: "UPS",
  PV: "PV",
  FUTURE: "Future",
};

const POWER_BASIS_LABELS: Record<PowerBasis, string> = {
  ELECTRICAL_INPUT: "Electrical input",
  MECHANICAL_OUTPUT: "Mechanical output (shaft)",
};

type LoadRowProps = {
  load: LoadRowDraft;
  // Zero-based position in the load list; shown to the user as "Load 1".
  index: number;
  onChange: (patch: Partial<LoadRowDraft>) => void;
  // Left out for the last remaining load: a schedule needs at least one.
  onRemove?: () => void;
};

// One load of the schedule, with the labels of LOAD_STUDY_LABELS so a
// validation message and its field carry the same words. The row holds no
// state of its own: every edit goes up as a patch.
export function LoadRow({ load, index, onChange, onRemove }: LoadRowProps) {
  const number = index + 1;
  const fieldName = (field: string) => `load-${number}-${field}`;
  const isDirectCurrent = load.phaseSystem === "DC";

  // A DC load has no power factor. Choosing DC clears whatever was typed, so a
  // value from an earlier choice cannot travel with the study.
  const changePhaseSystem = (phaseSystem: string) =>
    onChange(phaseSystem === "DC" ? { phaseSystem, powerFactor: "" } : { phaseSystem });

  const decimalInput = (
    label: string,
    field: keyof LoadRowDraft,
    name: string,
  ) => (
    <label>
      {label}
      <input
        inputMode="decimal"
        name={fieldName(name)}
        value={load[field] as string}
        onChange={(event) => onChange({ [field]: event.target.value } as Partial<LoadRowDraft>)}
      />
    </label>
  );

  return (
    <fieldset data-load-row={load.id}>
      <legend>Load {number}</legend>

      <label>
        Load code
        <input
          name={fieldName("code")}
          value={load.code}
          onChange={(event) => onChange({ code: event.target.value })}
        />
      </label>

      <label>
        Load name
        <input
          name={fieldName("name")}
          value={load.name}
          onChange={(event) => onChange({ name: event.target.value })}
        />
      </label>

      <label>
        Quantity
        <input
          inputMode="numeric"
          name={fieldName("quantity")}
          value={load.quantity}
          onChange={(event) => onChange({ quantity: event.target.value })}
        />
      </label>

      {decimalInput("Rated power (kW)", "ratedPowerKw", "rated-power")}

      <label>
        Phase system
        <select
          name={fieldName("phase-system")}
          value={load.phaseSystem}
          onChange={(event) => changePhaseSystem(event.target.value)}
        >
          <option value="">Select phase system</option>
          {phaseSystemSchema.options.map((phaseSystem) => (
            <option key={phaseSystem} value={phaseSystem}>
              {PHASE_SYSTEM_LABELS[phaseSystem]}
            </option>
          ))}
        </select>
      </label>

      {decimalInput("Voltage (V)", "voltageV", "voltage")}

      <label>
        Power factor
        <input
          inputMode="decimal"
          name={fieldName("power-factor")}
          value={load.powerFactor}
          disabled={isDirectCurrent}
          onChange={(event) => onChange({ powerFactor: event.target.value })}
        />
      </label>

      {isDirectCurrent ? (
        <p data-dc-power-factor-hint="true">DC: power factor is 1.</p>
      ) : null}

      <label>
        Power basis
        <select
          name={fieldName("power-basis")}
          value={load.powerBasis}
          onChange={(event) => onChange({ powerBasis: event.target.value })}
        >
          {powerBasisSchema.options.map((powerBasis) => (
            <option key={powerBasis} value={powerBasis}>
              {POWER_BASIS_LABELS[powerBasis]}
            </option>
          ))}
        </select>
      </label>

      {decimalInput("Efficiency", "efficiency", "efficiency")}

      <p data-efficiency-hint="true">Used only when the power basis is Mechanical output.</p>

      {decimalInput("Utilization factor", "utilizationFactor", "utilization-factor")}
      {decimalInput("Demand factor", "demandFactor", "demand-factor")}

      <p data-not-established-hint="true">
        Leave a factor blank if it is not established — the result will be marked Review
        required.
      </p>

      <label>
        Scenario
        <select
          name={fieldName("scenario")}
          value={load.scenario}
          onChange={(event) => onChange({ scenario: event.target.value })}
        >
          {loadScenarioSchema.options.map((scenario) => (
            <option key={scenario} value={scenario}>
              {SCENARIO_LABELS[scenario]}
            </option>
          ))}
        </select>
      </label>

      <label>
        Notes
        <input
          name={fieldName("notes")}
          value={load.notes}
          onChange={(event) => onChange({ notes: event.target.value })}
        />
      </label>

      {onRemove ? (
        <button type="button" onClick={onRemove}>
          Remove load {number}
        </button>
      ) : null}
    </fieldset>
  );
}

export { PHASE_SYSTEM_LABELS, POWER_BASIS_LABELS, SCENARIO_LABELS };
