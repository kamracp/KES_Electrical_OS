import {
  faultSourceTypeSchema,
  sourceRepresentationSchema,
  type FaultSourceType,
  type SourceRepresentation,
} from "../services/faultContract";
import type { BusDraft, ImpedanceDraft, SourceDraft } from "./faultStudyDraft";

// Exhaustive maps: a new enum member without a label is a compile error.
const SOURCE_TYPE_LABELS: Record<FaultSourceType, string> = {
  UTILITY_GRID: "Utility grid",
  SYNCHRONOUS_GENERATOR: "Synchronous generator",
  ASYNCHRONOUS_MOTOR: "Asynchronous motor",
  INVERTER_BASED_RESOURCE: "Inverter-based resource",
  EQUIVALENT_SOURCE: "Equivalent source",
};

const REPRESENTATION_LABELS: Record<SourceRepresentation, string> = {
  VOLTAGE_BEHIND_IMPEDANCE: "Voltage behind impedance",
  CURRENT_INJECTION: "Current injection",
};

type SequenceKey = "positive" | "negative" | "zero";

type FaultSourceRowProps = {
  source: SourceDraft;
  // Zero-based position in the source list; shown to the user as "Source 1".
  index: number;
  // The buses of the study, for the "Connected bus" choice.
  buses: BusDraft[];
  onChange: (patch: Partial<SourceDraft>) => void;
  // Left out for the last remaining source: a study needs at least one.
  onRemove?: () => void;
};

function impedancePatch(key: SequenceKey, value: ImpedanceDraft): Partial<SourceDraft> {
  if (key === "positive") {
    return { positive: value };
  }
  if (key === "negative") {
    return { negative: value };
  }
  return { zero: value };
}

// One source of the fault study, with the Fault UI v1 labels. The row holds no
// state of its own: every edit goes up as a patch.
export function FaultSourceRow({ source, index, buses, onChange, onRemove }: FaultSourceRowProps) {
  const number = index + 1;
  const fieldName = (field: string) => `source-${number}-${field}`;
  const usesImpedance = source.representation === "VOLTAGE_BEHIND_IMPEDANCE";
  const usesCurrentInjection = source.representation === "CURRENT_INJECTION";
  // A source whose bus was removed shows as "not chosen".
  const connectedBusId = buses.some((bus) => bus.id === source.busId) ? source.busId : "";

  const impedanceInput = (label: string, key: SequenceKey, part: keyof ImpedanceDraft) => (
    <label>
      {label}
      <input
        inputMode="decimal"
        name={fieldName(`${key}-${part}`)}
        value={source[key][part]}
        onChange={(event) =>
          onChange(impedancePatch(key, { ...source[key], [part]: event.target.value }))
        }
      />
    </label>
  );

  return (
    <fieldset data-source-row={source.id}>
      <legend>Source {number}</legend>

      <label>
        Source code
        <input
          name={fieldName("code")}
          value={source.code}
          onChange={(event) => onChange({ code: event.target.value })}
        />
      </label>

      <label>
        Source name
        <input
          name={fieldName("name")}
          value={source.name}
          onChange={(event) => onChange({ name: event.target.value })}
        />
      </label>

      <label>
        Connected bus
        <select
          name={fieldName("bus")}
          value={connectedBusId}
          onChange={(event) => onChange({ busId: event.target.value })}
        >
          <option value="">Select bus</option>
          {buses.map((bus, busIndex) => (
            <option key={bus.id} value={bus.id}>
              {bus.code.trim() ? `Bus ${busIndex + 1} — ${bus.code.trim()}` : `Bus ${busIndex + 1}`}
            </option>
          ))}
        </select>
      </label>

      <label>
        Source type
        <select
          name={fieldName("type")}
          value={source.sourceType}
          onChange={(event) => onChange({ sourceType: event.target.value })}
        >
          <option value="">Select source type</option>
          {faultSourceTypeSchema.options.map((type) => (
            <option key={type} value={type}>
              {SOURCE_TYPE_LABELS[type]}
            </option>
          ))}
        </select>
      </label>

      <label>
        Source representation
        <select
          name={fieldName("representation")}
          value={source.representation}
          onChange={(event) => onChange({ representation: event.target.value })}
        >
          <option value="">Select representation</option>
          {sourceRepresentationSchema.options.map((representation) => (
            <option key={representation} value={representation}>
              {REPRESENTATION_LABELS[representation]}
            </option>
          ))}
        </select>
      </label>

      {source.representation === "" ? (
        <p data-representation-hint="true">
          Choose a source representation first: the impedance or current fields appear once it
          is selected.
        </p>
      ) : null}

      {usesImpedance ? (
        <>
          {impedanceInput("Positive-sequence resistance (Ω)", "positive", "resistanceOhm")}
          {impedanceInput("Positive-sequence reactance (Ω)", "positive", "reactanceOhm")}
          {impedanceInput("Negative-sequence resistance (Ω) - optional", "negative", "resistanceOhm")}
          {impedanceInput("Negative-sequence reactance (Ω) - optional", "negative", "reactanceOhm")}
          {impedanceInput("Zero-sequence resistance (Ω) - optional", "zero", "resistanceOhm")}
          {impedanceInput("Zero-sequence reactance (Ω) - optional", "zero", "reactanceOhm")}
          <p>
            Negative- and zero-sequence impedances are required for phase-to-phase and earth
            faults; leave both fields of a pair blank to omit it.
          </p>
        </>
      ) : null}

      {usesCurrentInjection ? (
        <label>
          Current contribution (kA)
          <input
            inputMode="decimal"
            name={fieldName("current-contribution")}
            value={source.currentContributionKa}
            onChange={(event) => onChange({ currentContributionKa: event.target.value })}
          />
        </label>
      ) : null}

      <label>
        <input
          type="checkbox"
          name={fieldName("in-service")}
          checked={source.inService}
          onChange={(event) => onChange({ inService: event.target.checked })}
        />
        In service
      </label>

      {onRemove ? (
        <button type="button" onClick={onRemove}>
          Remove source {number}
        </button>
      ) : null}
    </fieldset>
  );
}
