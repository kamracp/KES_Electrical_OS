import { faultBranchTypeSchema, type FaultBranchType } from "../services/faultContract";
import type { BranchDraft, BusDraft, ImpedanceDraft } from "./faultStudyDraft";

// Exhaustive map: a new branch type without a label is a compile error.
const BRANCH_TYPE_LABELS: Record<FaultBranchType, string> = {
  CABLE: "Cable",
  OVERHEAD_LINE: "Overhead line",
  TRANSFORMER: "Transformer",
  BUSBAR: "Busbar",
  BUSDUCT: "Bus duct",
  REACTOR: "Reactor",
  EQUIVALENT: "Equivalent impedance",
};

type SequenceKey = "positive" | "negative" | "zero";

type FaultBranchRowProps = {
  branch: BranchDraft;
  // Zero-based position in the branch list; shown to the user as "Branch 1".
  index: number;
  // The buses of the study, for the "From bus" and "To bus" choices.
  buses: BusDraft[];
  onChange: (patch: Partial<BranchDraft>) => void;
  // Always available: a study may have no branch at all.
  onRemove: () => void;
};

function impedancePatch(key: SequenceKey, value: ImpedanceDraft): Partial<BranchDraft> {
  if (key === "positive") {
    return { positive: value };
  }
  if (key === "negative") {
    return { negative: value };
  }
  return { zero: value };
}

// One branch of the fault study: the impedance between two buses. The row
// holds no state of its own: every edit goes up as a patch.
export function FaultBranchRow({ branch, index, buses, onChange, onRemove }: FaultBranchRowProps) {
  const number = index + 1;
  const fieldName = (field: string) => `branch-${number}-${field}`;
  // A branch whose bus was removed shows that end as "not chosen".
  const knownBusId = (busId: string) => (buses.some((bus) => bus.id === busId) ? busId : "");
  const fromBusId = knownBusId(branch.fromBusId);
  const toBusId = knownBusId(branch.toBusId);
  const sameBus = fromBusId !== "" && fromBusId === toBusId;

  const busOptions = buses.map((bus, busIndex) => (
    <option key={bus.id} value={bus.id}>
      {bus.code.trim() ? `Bus ${busIndex + 1} — ${bus.code.trim()}` : `Bus ${busIndex + 1}`}
    </option>
  ));

  const impedanceInput = (label: string, key: SequenceKey, part: keyof ImpedanceDraft) => (
    <label>
      {label}
      <input
        inputMode="decimal"
        name={fieldName(`${key}-${part}`)}
        value={branch[key][part]}
        onChange={(event) =>
          onChange(impedancePatch(key, { ...branch[key], [part]: event.target.value }))
        }
      />
    </label>
  );

  return (
    <fieldset data-branch-row={branch.id}>
      <legend>Branch {number}</legend>

      <label>
        Branch code
        <input
          name={fieldName("code")}
          value={branch.code}
          onChange={(event) => onChange({ code: event.target.value })}
        />
      </label>

      <label>
        Branch name
        <input
          name={fieldName("name")}
          value={branch.name}
          onChange={(event) => onChange({ name: event.target.value })}
        />
      </label>

      <label>
        From bus
        <select
          name={fieldName("from-bus")}
          value={fromBusId}
          onChange={(event) => onChange({ fromBusId: event.target.value })}
        >
          <option value="">Select bus</option>
          {busOptions}
        </select>
      </label>

      <label>
        To bus
        <select
          name={fieldName("to-bus")}
          value={toBusId}
          onChange={(event) => onChange({ toBusId: event.target.value })}
        >
          <option value="">Select bus</option>
          {busOptions}
        </select>
      </label>

      {sameBus ? (
        <p data-same-bus-warning="true">
          From bus and To bus are the same: a branch links two different buses.
        </p>
      ) : null}

      <label>
        Branch type
        <select
          name={fieldName("type")}
          value={branch.branchType}
          onChange={(event) => onChange({ branchType: event.target.value })}
        >
          <option value="">Select branch type</option>
          {faultBranchTypeSchema.options.map((type) => (
            <option key={type} value={type}>
              {BRANCH_TYPE_LABELS[type]}
            </option>
          ))}
        </select>
      </label>

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

      <label>
        Parallel circuits - optional
        <input
          inputMode="numeric"
          name={fieldName("parallel-circuits")}
          value={branch.parallelCircuits}
          onChange={(event) => onChange({ parallelCircuits: event.target.value })}
        />
      </label>

      <label>
        <input
          type="checkbox"
          name={fieldName("in-service")}
          checked={branch.inService}
          onChange={(event) => onChange({ inService: event.target.checked })}
        />
        In service
      </label>

      <button type="button" onClick={onRemove}>
        Remove branch {number}
      </button>
    </fieldset>
  );
}
