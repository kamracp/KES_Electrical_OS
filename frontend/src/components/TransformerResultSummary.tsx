import type { TransformerSizingResponse } from "../services/transformerSizing";
import {
  NOT_ESTABLISHED_WARNING_CODES,
  type TransformerRedundancyMode,
} from "../services/transformerSizingContract";
import { EMPTY_QUANTITY, formatQuantity } from "../utils/formatQuantity";

// The same words and the same colour as the Cable and Load summaries: an
// unestablished factor is a review the engineer owes, not a design failure.
// No adequate rating is a failure - there is nothing to build with.
const STATUS_LABELS: Record<TransformerSizingResponse["status"], string> = {
  VALID: "Calculated",
  WARNING: "Calculated with warnings",
  REVIEW_REQUIRED: "Engineering review required",
  NO_SOLUTION: "No standard rating fits",
};

const STATUS_TONE: Record<TransformerSizingResponse["status"], "pass" | "fail" | "warning"> = {
  VALID: "pass",
  WARNING: "warning",
  REVIEW_REQUIRED: "warning",
  NO_SOLUTION: "fail",
};

// Compact names for the strip; the form's select uses longer ones because it
// has to explain each choice.
const REDUNDANCY_LABELS: Record<TransformerRedundancyMode, string> = {
  NONE: "no redundancy",
  N_PLUS_1: "N+1",
  TWO_N: "2N",
};

type TransformerResultSummaryProps = {
  result: TransformerSizingResponse;
};

// The decisive values first (Master Prompt v2.1 section 19): sizing state, the
// rating chosen from the schedule, what the design required, the installed
// capacity and the loading it leads to.
// Display rule A12: four significant figures on screen, the exact engine
// decimal in the tooltip (title attribute). The selected rating is a catalogue
// value the engineer supplied, so it is shown exactly as it was sent.
export function TransformerResultSummary({ result }: TransformerResultSummaryProps) {
  const tone = STATUS_TONE[result.status];
  const warningCount = result.warnings.length;
  const notEstablishedCount = result.warnings.filter((warning) =>
    (NOT_ESTABLISHED_WARNING_CODES as readonly string[]).includes(warning.code),
  ).length;

  const requiredRating = formatQuantity(result.required_unit_rating_kva, "kVA");
  const designRequired = formatQuantity(result.design_required_kva, "kVA");
  const installed = formatQuantity(result.installed_nameplate_capacity_kva, "kVA");
  const spare = formatQuantity(result.spare_derated_capacity_kva, "kVA");
  const loading = formatQuantity(result.loading_percent, "%");

  return (
    <section aria-label="Result summary" data-summary-tone={tone}>
      <header>
        <p data-summary-status={result.status}>{STATUS_LABELS[result.status]}</p>
        <p>
          Study <strong>{result.code}</strong> · {result.name} ·{" "}
          {result.jurisdiction_profile} profile
        </p>
        {result.selected_unit_rating_kva === null ? (
          <p data-no-rating="true">
            No rating in the schedule covers {requiredRating.display}.
          </p>
        ) : null}
      </header>
      <dl data-summary-strip>
        <div>
          <dt>Selected unit rating</dt>
          {/* A catalogue value from the project design basis: shown as sent, so
              the engineer reads back the rating that is actually orderable. */}
          <dd data-summary-field="selected-rating">
            {result.selected_unit_rating_kva === null
              ? EMPTY_QUANTITY
              : `${result.selected_unit_rating_kva} kVA`}
          </dd>
        </div>
        <div>
          <dt>Required unit rating</dt>
          <dd data-summary-field="required-rating" title={requiredRating.exact ?? undefined}>
            {requiredRating.display}
          </dd>
        </div>
        <div>
          <dt>Design required</dt>
          <dd data-summary-field="design-required" title={designRequired.exact ?? undefined}>
            {designRequired.display}
          </dd>
        </div>
        <div>
          <dt>Installed capacity</dt>
          <dd data-summary-field="installed" title={installed.exact ?? undefined}>
            {installed.display}
          </dd>
        </div>
        <div>
          <dt>Spare derated capacity</dt>
          <dd data-summary-field="spare" title={spare.exact ?? undefined}>
            {spare.display}
          </dd>
        </div>
        <div>
          <dt>Loading</dt>
          <dd data-summary-field="loading" title={loading.exact ?? undefined}>
            {loading.display}
          </dd>
        </div>
        <div>
          <dt>Units</dt>
          {/* Counts, not engineering quantities: shown as the integers they are. */}
          <dd data-summary-field="units">
            {result.duty_units} duty + {result.standby_units} standby ·{" "}
            {REDUNDANCY_LABELS[result.redundancy_mode]}
          </dd>
        </div>
        {notEstablishedCount > 0 ? (
          <div>
            <dt>Factors not established</dt>
            <dd data-summary-field="not-established">{notEstablishedCount}</dd>
          </div>
        ) : null}
        <div>
          <dt>Warnings</dt>
          <dd data-summary-warnings={warningCount}>{warningCount}</dd>
        </div>
      </dl>
    </section>
  );
}

export { REDUNDANCY_LABELS, STATUS_LABELS, STATUS_TONE };
