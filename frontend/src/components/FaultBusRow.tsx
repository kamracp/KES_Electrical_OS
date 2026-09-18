import { neutralEarthingModeSchema, type NeutralEarthingMode } from "../services/faultContract";
import type { BusDraft } from "./faultStudyDraft";

// Exhaustive map: a new earthing mode without a label is a compile error.
const EARTHING_LABELS: Record<NeutralEarthingMode, string> = {
  SOLIDLY_EARTHED: "Solidly earthed",
  RESISTANCE_EARTHED: "Resistance earthed",
  REACTANCE_EARTHED: "Reactance earthed",
  RESONANT_EARTHED: "Resonant earthed",
  ISOLATED: "Isolated",
};

type FaultBusRowProps = {
  bus: BusDraft;
  // Zero-based position in the bus list; shown to the user as "Bus 1".
  index: number;
  onChange: (patch: Partial<BusDraft>) => void;
  // Left out for the last remaining bus: a study needs at least one.
  onRemove?: () => void;
};

// One bus of the fault study. The labels are those of the Fault UI v1 form;
// the legend "Bus N" tells the rows apart once there is more than one. The
// row holds no state of its own: every edit goes up as a patch.
export function FaultBusRow({ bus, index, onChange, onRemove }: FaultBusRowProps) {
  const number = index + 1;
  const fieldName = (field: string) => `bus-${number}-${field}`;

  return (
    <fieldset data-bus-row={bus.id}>
      <legend>Bus {number}</legend>

      <label>
        Bus code
        <input
          name={fieldName("code")}
          value={bus.code}
          onChange={(event) => onChange({ code: event.target.value })}
        />
      </label>

      <label>
        Bus name
        <input
          name={fieldName("name")}
          value={bus.name}
          onChange={(event) => onChange({ name: event.target.value })}
        />
      </label>

      <label>
        Nominal voltage (V)
        <input
          inputMode="decimal"
          name={fieldName("nominal-voltage")}
          value={bus.nominalVoltageV}
          onChange={(event) => onChange({ nominalVoltageV: event.target.value })}
        />
      </label>

      <label>
        Maximum voltage factor
        <input
          inputMode="decimal"
          name={fieldName("voltage-factor-max")}
          value={bus.voltageFactorMax}
          onChange={(event) => onChange({ voltageFactorMax: event.target.value })}
        />
      </label>

      <label>
        Minimum voltage factor
        <input
          inputMode="decimal"
          name={fieldName("voltage-factor-min")}
          value={bus.voltageFactorMin}
          onChange={(event) => onChange({ voltageFactorMin: event.target.value })}
        />
      </label>

      <label>
        Neutral earthing mode
        <select
          name={fieldName("neutral-earthing-mode")}
          value={bus.neutralEarthingMode}
          onChange={(event) => onChange({ neutralEarthingMode: event.target.value })}
        >
          <option value="">Select earthing mode</option>
          {neutralEarthingModeSchema.options.map((mode) => (
            <option key={mode} value={mode}>
              {EARTHING_LABELS[mode]}
            </option>
          ))}
        </select>
      </label>

      {bus.neutralEarthingMode === "RESISTANCE_EARTHED" ? (
        <label>
          Neutral resistance (Ω)
          <input
            inputMode="decimal"
            name={fieldName("neutral-resistance")}
            value={bus.neutralResistanceOhm}
            onChange={(event) => onChange({ neutralResistanceOhm: event.target.value })}
          />
        </label>
      ) : null}

      {bus.neutralEarthingMode === "REACTANCE_EARTHED" ? (
        <label>
          Neutral reactance (Ω)
          <input
            inputMode="decimal"
            name={fieldName("neutral-reactance")}
            value={bus.neutralReactanceOhm}
            onChange={(event) => onChange({ neutralReactanceOhm: event.target.value })}
          />
        </label>
      ) : null}

      {onRemove ? (
        <button type="button" onClick={onRemove}>
          Remove bus {number}
        </button>
      ) : null}
    </fieldset>
  );
}
