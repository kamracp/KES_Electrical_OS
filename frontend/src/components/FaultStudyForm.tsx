import { useState, type FormEvent } from "react";

import {
  shortCircuitStudyRequestSchema,
  type ShortCircuitStudyRequest,
} from "../services/fault";
import { useStudyDraft } from "../hooks/useStudyDraft";
import { describeValidationIssue } from "../utils/validationMessages";
import { FaultBranchRow } from "./FaultBranchRow";
import { FaultBusRow } from "./FaultBusRow";
import { FaultSourceRow } from "./FaultSourceRow";
import {
  FAULT_STUDY_LABELS,
  buildShortCircuitPayload,
  createBranchDraft,
  createBusDraft,
  createInitialFaultStudyDraft,
  createSourceDraft,
  faultStudyDraftSchema,
  seedRowIdCounter,
  type BranchDraft,
  type BusDraft,
  type FaultStudyDraft,
  type SourceDraft,
} from "./faultStudyDraft";

type FaultStudyFormProps = {
  disabled?: boolean;
  onSubmit: (payload: ShortCircuitStudyRequest) => void | Promise<void>;
};

function busLabel(bus: BusDraft, index: number): string {
  return bus.code.trim() ? `Bus ${index + 1} — ${bus.code.trim()}` : `Bus ${index + 1}`;
}

// Fault UI v2: a study of one or more buses, sources and branches. The form
// owns the draft; the rows send patches. It starts as the single-bus study of
// v1 (one bus, one source on it, fault at that bus), so that case is filled in
// and sent exactly as before.
export function FaultStudyForm({ disabled = false, onSubmit }: FaultStudyFormProps) {
  // The entries outlive a reload, Back and the sidebar for as long as the tab is open.
  const { draft, setDraft, restored, clear } = useStudyDraft<FaultStudyDraft>({
    module: "fault-study",
    createInitial: createInitialFaultStudyDraft,
    schema: faultStudyDraftSchema,
  });
  const [validationError, setValidationError] = useState<string | null>(null);

  function updateStudy(patch: Partial<FaultStudyDraft>) {
    setDraft((current) => ({ ...current, ...patch }));
  }

  function updateBus(id: string, patch: Partial<BusDraft>) {
    setDraft((current) => ({
      ...current,
      buses: current.buses.map((bus) => (bus.id === id ? { ...bus, ...patch } : bus)),
    }));
  }

  function updateSource(id: string, patch: Partial<SourceDraft>) {
    setDraft((current) => ({
      ...current,
      sources: current.sources.map((source) =>
        source.id === id ? { ...source, ...patch } : source,
      ),
    }));
  }

  function updateBranch(id: string, patch: Partial<BranchDraft>) {
    setDraft((current) => ({
      ...current,
      branches: current.branches.map((branch) =>
        branch.id === id ? { ...branch, ...patch } : branch,
      ),
    }));
  }

  // A restored draft brings ids the counter of this page load has not handed out yet.
  function seedFromDraft() {
    seedRowIdCounter(
      [...draft.buses, ...draft.sources, ...draft.branches].map((row) => row.id),
    );
  }

  function addBus() {
    seedFromDraft();
    const bus = createBusDraft();
    setDraft((current) => ({ ...current, buses: [...current.buses, bus] }));
  }

  // A new source is connected for the user only when there is no choice to make.
  function addSource() {
    const onlyBus = draft.buses.length === 1 ? draft.buses[0] : undefined;
    seedFromDraft();
    const source = createSourceDraft(onlyBus?.id ?? "");
    setDraft((current) => ({ ...current, sources: [...current.sources, source] }));
  }

  function addBranch() {
    seedFromDraft();
    const branch = createBranchDraft();
    setDraft((current) => ({ ...current, branches: [...current.branches, branch] }));
  }

  // Sources and branches on the removed bus lose that link in the same update:
  // their rows show "not chosen" and the validation names them, and the draft
  // never holds an id of a bus that is gone (a stored draft with one is refused
  // on restore). The fault moves only when a single bus is left, otherwise the
  // user chooses again.
  function removeBus(id: string) {
    const unlink = (busId: string) => (busId === id ? "" : busId);
    setDraft((current) => {
      const buses = current.buses.filter((bus) => bus.id !== id);
      const faultBusKept = buses.some((bus) => bus.id === current.faultBusId);
      const onlyBus = buses.length === 1 ? buses[0] : undefined;
      return {
        ...current,
        buses,
        sources: current.sources.map((source) => ({ ...source, busId: unlink(source.busId) })),
        branches: current.branches.map((branch) => ({
          ...branch,
          fromBusId: unlink(branch.fromBusId),
          toBusId: unlink(branch.toBusId),
        })),
        faultBusId: faultBusKept ? current.faultBusId : (onlyBus?.id ?? ""),
      };
    });
  }

  function removeSource(id: string) {
    setDraft((current) => ({
      ...current,
      sources: current.sources.filter((source) => source.id !== id),
    }));
  }

  function removeBranch(id: string) {
    setDraft((current) => ({
      ...current,
      branches: current.branches.filter((branch) => branch.id !== id),
    }));
  }

  // Empties the form only; a result already on the page stays until "Clear results".
  function clearForm() {
    setValidationError(null);
    clear();
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setValidationError(null);

    const parsed = shortCircuitStudyRequestSchema.safeParse(buildShortCircuitPayload(draft));

    if (!parsed.success) {
      const issue = parsed.error.issues[0];
      setValidationError(
        issue
          ? describeValidationIssue(issue, FAULT_STUDY_LABELS)
          : "Review the fault-study inputs.",
      );
      return;
    }

    await onSubmit(parsed.data);
  }

  const faultBusId = draft.buses.some((bus) => bus.id === draft.faultBusId)
    ? draft.faultBusId
    : "";

  return (
    <form aria-label="Fault study inputs" onSubmit={handleSubmit}>
      {restored ? <p role="status">Draft restored from this session.</p> : null}

      <fieldset disabled={disabled}>
        <legend>Study definition</legend>

        <label>
          Study code
          <input
            name="studyCode"
            value={draft.studyCode}
            onChange={(event) => updateStudy({ studyCode: event.target.value })}
          />
        </label>

        <label>
          Study name
          <input
            name="studyName"
            value={draft.studyName}
            onChange={(event) => updateStudy({ studyName: event.target.value })}
          />
        </label>

        <label>
          Calculation case
          <select
            name="calculationCase"
            value={draft.calculationCase}
            onChange={(event) => updateStudy({ calculationCase: event.target.value })}
          >
            <option value="">Select case</option>
            <option value="MAXIMUM">Maximum</option>
            <option value="MINIMUM">Minimum</option>
          </select>
        </label>

        <label>
          Fault type
          <select
            name="faultType"
            value={draft.faultType}
            onChange={(event) => updateStudy({ faultType: event.target.value })}
          >
            <option value="">Select fault type</option>
            <option value="THREE_PHASE">Three-phase</option>
            <option value="TWO_PHASE">Phase-to-phase</option>
            <option value="TWO_PHASE_TO_EARTH">Phase-to-phase-to-earth</option>
            <option value="SINGLE_PHASE_TO_EARTH">Single-phase-to-earth</option>
          </select>
        </label>

        <label>
          Fault at bus
          <select
            name="faultBus"
            value={faultBusId}
            onChange={(event) => updateStudy({ faultBusId: event.target.value })}
          >
            <option value="">Select bus</option>
            {draft.buses.map((bus, index) => (
              <option key={bus.id} value={bus.id}>
                {busLabel(bus, index)}
              </option>
            ))}
          </select>
        </label>

        <label>
          Frequency (Hz)
          <input
            inputMode="decimal"
            name="frequencyHz"
            value={draft.frequencyHz}
            onChange={(event) => updateStudy({ frequencyHz: event.target.value })}
          />
        </label>

        <label>
          Jurisdiction profile
          <select
            name="jurisdictionProfile"
            value={draft.jurisdictionProfile}
            onChange={(event) => updateStudy({ jurisdictionProfile: event.target.value })}
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
          The jurisdiction profile selects the governing short-circuit and earth-current
          references; engine physics does not change with the profile.
        </p>
      </fieldset>

      <fieldset disabled={disabled}>
        <legend>Buses</legend>
        {draft.buses.map((bus, index) => (
          <FaultBusRow
            key={bus.id}
            bus={bus}
            index={index}
            onChange={(patch) => updateBus(bus.id, patch)}
            onRemove={draft.buses.length > 1 ? () => removeBus(bus.id) : undefined}
          />
        ))}
        <button type="button" onClick={addBus}>
          Add bus
        </button>
      </fieldset>

      <fieldset disabled={disabled}>
        <legend>Sources</legend>
        {draft.sources.map((source, index) => (
          <FaultSourceRow
            key={source.id}
            source={source}
            index={index}
            buses={draft.buses}
            onChange={(patch) => updateSource(source.id, patch)}
            onRemove={draft.sources.length > 1 ? () => removeSource(source.id) : undefined}
          />
        ))}
        <button type="button" onClick={addSource}>
          Add source
        </button>
      </fieldset>

      <fieldset disabled={disabled}>
        <legend>Branches</legend>
        {draft.branches.length === 0 ? (
          <p data-no-branches="true">
            No branches: every source feeds its bus directly. Add a branch to link two buses
            through an impedance (cable, transformer, busbar, reactor).
          </p>
        ) : null}
        {draft.branches.map((branch, index) => (
          <FaultBranchRow
            key={branch.id}
            branch={branch}
            index={index}
            buses={draft.buses}
            onChange={(patch) => updateBranch(branch.id, patch)}
            onRemove={() => removeBranch(branch.id)}
          />
        ))}
        <button type="button" onClick={addBranch}>
          Add branch
        </button>
      </fieldset>

      {validationError ? <p role="alert">{validationError}</p> : null}

      <button disabled={disabled} type="submit">
        Calculate fault study
      </button>
      <button disabled={disabled} type="button" onClick={clearForm}>
        Clear form
      </button>
    </form>
  );
}
