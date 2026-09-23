import { useEffect, useRef, useState, type FormEvent } from "react";

import {
  transformerRunCreateRequestSchema,
  type TransformerRunCreateRequest,
} from "../services/transformerSizing";
import { loadScenarioSchema } from "../services/loadDemandContract";
import { transformerRedundancyModeSchema } from "../services/transformerSizingContract";
import { describeValidationIssue } from "../utils/validationMessages";
import { SCENARIO_LABELS } from "./LoadRow";
import {
  TRANSFORMER_STUDY_LABELS,
  buildTransformerRunPayload,
  createInitialTransformerStudyDraft,
  createUnitRatingDraft,
  deriveStandbyUnits,
  type TransformerStudyDraft,
  type UnitRatingDraft,
} from "./transformerStudyDraft";

type TransformerRedundancyMode = (typeof transformerRedundancyModeSchema.options)[number];

// Exhaustive maps: a new enum member without a label is a compile error.
const REDUNDANCY_LABELS: Record<TransformerRedundancyMode, string> = {
  NONE: "None (no standby unit)",
  N_PLUS_1: "N+1 (one standby unit)",
  TWO_N: "2N (a standby unit for every duty unit)",
};

const REDUNDANCY_HINTS: Record<TransformerRedundancyMode, string> = {
  NONE: "None: no standby unit.",
  N_PLUS_1: "N+1: one standby unit.",
  TWO_N: "2N: equal to duty units.",
};

type TransformerStudyFormProps = {
  disabled?: boolean;
  onSubmit: (payload: TransformerRunCreateRequest) => void | Promise<void>;
};

// The transformer sizing study (EOS-03a). The form owns the draft. The standby
// count is derived from the redundancy mode rather than typed, so the rule the
// backend enforces cannot be broken here.
//
// The payload carries no project revision: the page adds the selected revision
// when it calls the API, exactly as the Load and Fault pages do.
export { REDUNDANCY_HINTS, REDUNDANCY_LABELS };

export function TransformerStudyForm({
  disabled = false,
  onSubmit,
}: TransformerStudyFormProps) {
  const [draft, setDraft] = useState<TransformerStudyDraft>(
    createInitialTransformerStudyDraft,
  );
  const [validationError, setValidationError] = useState<string | null>(null);
  const [ratingToFocus, setRatingToFocus] = useState<string | null>(null);
  const formRef = useRef<HTMLFormElement>(null);

  // A new entry is at the end of a long form, so the cursor goes to it.
  useEffect(() => {
    if (ratingToFocus === null) {
      return;
    }
    formRef.current
      ?.querySelector<HTMLInputElement>(`input[name="rating-${ratingToFocus}"]`)
      ?.focus();
    setRatingToFocus(null);
  }, [ratingToFocus]);

  // Every edit keeps the derived standby count in step with what it is made of.
  function updateStudy(patch: Partial<TransformerStudyDraft>) {
    setDraft((current) => {
      const next = { ...current, ...patch };
      return {
        ...next,
        standbyUnits: deriveStandbyUnits(next.redundancyMode, next.dutyUnits),
      };
    });
  }

  function updateRating(id: string, value: string) {
    setDraft((current) => ({
      ...current,
      unitRatings: current.unitRatings.map((rating) =>
        rating.id === id ? { ...rating, value } : rating,
      ),
    }));
  }

  function addRating() {
    const rating: UnitRatingDraft = createUnitRatingDraft();
    setDraft((current) => ({ ...current, unitRatings: [...current.unitRatings, rating] }));
    setRatingToFocus(rating.id);
  }

  function removeRating(id: string) {
    setDraft((current) => ({
      ...current,
      unitRatings: current.unitRatings.filter((rating) => rating.id !== id),
    }));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setValidationError(null);

    const parsed = transformerRunCreateRequestSchema.safeParse(
      buildTransformerRunPayload(draft),
    );

    if (!parsed.success) {
      const issue = parsed.error.issues[0];
      setValidationError(
        issue
          ? describeValidationIssue(issue, TRANSFORMER_STUDY_LABELS)
          : "Review the transformer sizing inputs.",
      );
      return;
    }

    await onSubmit(parsed.data);
  }

  const redundancyMode = draft.redundancyMode as TransformerRedundancyMode;

  const decimalField = (label: string, field: keyof TransformerStudyDraft, name: string) => (
    <label>
      {label}
      <input
        inputMode="decimal"
        name={name}
        value={draft[field] as string}
        onChange={(event) =>
          updateStudy({ [field]: event.target.value } as Partial<TransformerStudyDraft>)
        }
      />
    </label>
  );

  return (
    <form aria-label="Transformer sizing inputs" ref={formRef} onSubmit={handleSubmit}>
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
          The sizing itself carries no profile-dependent value; the profile is recorded with
          the run and must match the design basis of the project revision.
        </p>

        <label>
          Scenario
          <select
            name="scenario"
            value={draft.scenario}
            onChange={(event) => updateStudy({ scenario: event.target.value })}
          >
            {loadScenarioSchema.options.map((scenario) => (
              <option key={scenario} value={scenario}>
                {SCENARIO_LABELS[scenario]}
              </option>
            ))}
          </select>
        </label>

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
        <legend>Demand</legend>
        {decimalField("Demand power (kW)", "demandPowerKw", "demandPowerKw")}
        {decimalField("Power factor", "demandPowerFactor", "demandPowerFactor")}
      </fieldset>

      <fieldset disabled={disabled}>
        <legend>Factors</legend>
        {decimalField("Future growth factor", "futureGrowthFactor", "futureGrowthFactor")}
        {decimalField("Design margin factor", "designMarginFactor", "designMarginFactor")}
        {decimalField("Ambient derating factor", "ambientDeratingFactor", "ambientDeratingFactor")}
        {decimalField(
          "Altitude derating factor",
          "altitudeDeratingFactor",
          "altitudeDeratingFactor",
        )}
        {decimalField(
          "Harmonic derating factor",
          "harmonicDeratingFactor",
          "harmonicDeratingFactor",
        )}
        <p data-not-established-hint="true">
          Leave a factor blank if it is not established — the result will be marked
          Engineering review required.
        </p>
      </fieldset>

      <fieldset disabled={disabled}>
        <legend>Units and redundancy</legend>

        <label>
          Duty units
          <input
            inputMode="numeric"
            name="dutyUnits"
            value={draft.dutyUnits}
            onChange={(event) => updateStudy({ dutyUnits: event.target.value })}
          />
        </label>

        <label>
          Redundancy mode
          <select
            name="redundancyMode"
            value={draft.redundancyMode}
            onChange={(event) => updateStudy({ redundancyMode: event.target.value })}
          >
            {transformerRedundancyModeSchema.options.map((mode) => (
              <option key={mode} value={mode}>
                {REDUNDANCY_LABELS[mode]}
              </option>
            ))}
          </select>
        </label>

        <label>
          Standby units
          <input name="standbyUnits" value={draft.standbyUnits} readOnly />
        </label>
        <p data-standby-hint="true">{REDUNDANCY_HINTS[redundancyMode]}</p>
      </fieldset>

      <fieldset disabled={disabled}>
        <legend>Unit ratings</legend>
        {draft.unitRatings.map((rating, index) => (
          <div key={rating.id} data-rating-entry={rating.id}>
            <label>
              Unit rating {index + 1}
              <input
                inputMode="decimal"
                name={`rating-${rating.id}`}
                value={rating.value}
                onChange={(event) => updateRating(rating.id, event.target.value)}
              />
            </label>
            {draft.unitRatings.length > 1 ? (
              <button type="button" onClick={() => removeRating(rating.id)}>
                Remove rating {index + 1}
              </button>
            ) : null}
          </div>
        ))}
        <button type="button" onClick={addRating}>
          Add rating
        </button>
        <p data-ratings-hint="true">
          Enter the ratings from the project design basis in ascending order.
        </p>
      </fieldset>

      {validationError ? <p role="alert">{validationError}</p> : null}

      <button disabled={disabled} type="submit">
        Calculate transformer size
      </button>
    </form>
  );
}
