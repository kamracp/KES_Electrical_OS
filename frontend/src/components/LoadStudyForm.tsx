import { useEffect, useRef, useState, type FormEvent } from "react";

import {
  loadRunCreateRequestSchema,
  type LoadRunCreateRequest,
} from "../services/loadDemand";
import { describeValidationIssue } from "../utils/validationMessages";
import { LoadRow } from "./LoadRow";
import {
  LOAD_STUDY_LABELS,
  buildLoadRunPayload,
  createInitialLoadStudyDraft,
  createLoadRowDraft,
  type LoadRowDraft,
  type LoadStudyDraft,
} from "./loadStudyDraft";

type LoadStudyFormProps = {
  disabled?: boolean;
  onSubmit: (payload: LoadRunCreateRequest) => void | Promise<void>;
};

// The load and demand study (EOS-02): a schedule of loads with one coincidence
// factor. The form owns the draft; the rows send patches. It validates the
// whole run request, so a message names the row and the field the user sees.
//
// The payload carries no project revision: the page adds the selected revision
// when it calls the API, exactly as the Fault page does.
export function LoadStudyForm({ disabled = false, onSubmit }: LoadStudyFormProps) {
  const [draft, setDraft] = useState<LoadStudyDraft>(createInitialLoadStudyDraft);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [rowToFocus, setRowToFocus] = useState<string | null>(null);
  const formRef = useRef<HTMLFormElement>(null);

  // A new row is far down a long form, so the cursor goes to it.
  useEffect(() => {
    if (rowToFocus === null) {
      return;
    }
    formRef.current
      ?.querySelector<HTMLInputElement>(`[data-load-row="${rowToFocus}"] input[name$="-code"]`)
      ?.focus();
    setRowToFocus(null);
  }, [rowToFocus]);

  function updateStudy(patch: Partial<LoadStudyDraft>) {
    setDraft((current) => ({ ...current, ...patch }));
  }

  function updateLoad(id: string, patch: Partial<LoadRowDraft>) {
    setDraft((current) => ({
      ...current,
      loads: current.loads.map((load) => (load.id === id ? { ...load, ...patch } : load)),
    }));
  }

  function addLoad() {
    const load = createLoadRowDraft();
    setDraft((current) => ({ ...current, loads: [...current.loads, load] }));
    setRowToFocus(load.id);
  }

  function removeLoad(id: string) {
    setDraft((current) => ({
      ...current,
      loads: current.loads.filter((load) => load.id !== id),
    }));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setValidationError(null);

    const parsed = loadRunCreateRequestSchema.safeParse(buildLoadRunPayload(draft));

    if (!parsed.success) {
      const issue = parsed.error.issues[0];
      setValidationError(
        issue ? describeValidationIssue(issue, LOAD_STUDY_LABELS) : "Review the load study inputs.",
      );
      return;
    }

    await onSubmit(parsed.data);
  }

  return (
    <form aria-label="Load study inputs" ref={formRef} onSubmit={handleSubmit}>
      <fieldset disabled={disabled}>
        <legend>Study definition</legend>

        <label>
          Study code
          <input
            name="studyCode"
            value={draft.code}
            onChange={(event) => updateStudy({ code: event.target.value })}
          />
        </label>

        <label>
          Study name
          <input
            name="studyName"
            value={draft.name}
            onChange={(event) => updateStudy({ name: event.target.value })}
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
          The load calculation itself carries no profile-dependent value; the profile is
          recorded with the run and must match the design basis of the project revision.
        </p>

        <label>
          Coincidence factor
          <input
            inputMode="decimal"
            name="coincidenceFactor"
            value={draft.coincidenceFactor}
            onChange={(event) => updateStudy({ coincidenceFactor: event.target.value })}
          />
        </label>
        <p data-coincidence-hint="true">
          Applied to the whole group, equally to active and reactive demand. Leave blank if
          not established — the result will be marked Review required.
        </p>

        <label>
          Study notes
          <input
            name="studyNotes"
            value={draft.notes}
            onChange={(event) => updateStudy({ notes: event.target.value })}
          />
        </label>
      </fieldset>

      <fieldset disabled={disabled}>
        <legend>Loads</legend>
        {draft.loads.map((load, index) => (
          <LoadRow
            key={load.id}
            load={load}
            index={index}
            onChange={(patch) => updateLoad(load.id, patch)}
            onRemove={draft.loads.length > 1 ? () => removeLoad(load.id) : undefined}
          />
        ))}
        <button type="button" onClick={addLoad}>
          Add load
        </button>
      </fieldset>

      {validationError ? <p role="alert">{validationError}</p> : null}

      <button disabled={disabled} type="submit">
        Calculate load study
      </button>
    </form>
  );
}
