import type { LoadGroupResponse } from "../services/loadDemand";
import { NOT_ESTABLISHED_WARNING_CODES } from "../services/loadDemandContract";
import { formatQuantity } from "../utils/formatQuantity";

// The same words and the same colour as the Cable summary: an unestablished
// factor is a review the engineer owes, not a design failure.
const STATUS_LABELS: Record<LoadGroupResponse["status"], string> = {
  VALID: "Calculated",
  WARNING: "Calculated with warnings",
  REVIEW_REQUIRED: "Engineering review required",
};

const STATUS_TONE: Record<LoadGroupResponse["status"], "pass" | "fail" | "warning"> = {
  VALID: "pass",
  WARNING: "warning",
  REVIEW_REQUIRED: "warning",
};

type LoadResultSummaryProps = {
  result: LoadGroupResponse;
};

// The decisive values first (Master Prompt v2.1 section 19): group state, the
// demand the schedule imposes, the power components, and how many factors the
// engineer still has to establish.
// Display rule A12: four significant figures on screen, the exact engine
// decimal in the tooltip (title attribute).
export function LoadResultSummary({ result }: LoadResultSummaryProps) {
  const tone = STATUS_TONE[result.status];
  const warningCount = result.warnings.length;
  // The group's warning list already repeats every member's warning under the
  // load code, so it alone is the count; adding load_results would count a
  // member's factor twice.
  const notEstablishedCount = result.warnings.filter((warning) =>
    (NOT_ESTABLISHED_WARNING_CODES as readonly string[]).includes(warning.code),
  ).length;
  const coincidenceNotEstablished = result.warnings.some(
    (warning) => warning.code === "COINCIDENCE_FACTOR_NOT_ESTABLISHED",
  );

  const demandPower = formatQuantity(result.demand_power_kw, "kW");
  const apparentPower = formatQuantity(result.apparent_power_kva, "kVA");
  const reactivePower = formatQuantity(result.reactive_power_kvar, "kvar");
  const connectedPower = formatQuantity(result.connected_power_kw, "kW");
  const preCoincidenceDemand = formatQuantity(result.pre_coincidence_demand_kw, "kW");
  // The factor the aggregation used; it is always present, so the warning -
  // not the value - is what says whether it was established (A15 (a)).
  const coincidenceFactor = formatQuantity(result.coincidence_factor);

  return (
    <section aria-label="Result summary" data-summary-tone={tone}>
      <header>
        <p data-summary-status={result.status}>{STATUS_LABELS[result.status]}</p>
        <p>
          Study <strong>{result.group_code}</strong> · {result.group_name} ·{" "}
          {result.jurisdiction_profile} profile
        </p>
      </header>
      <dl data-summary-strip>
        <div>
          <dt>Demand power</dt>
          <dd data-summary-field="demand-power" title={demandPower.exact ?? undefined}>
            {demandPower.display}
          </dd>
        </div>
        <div>
          <dt>Apparent power</dt>
          <dd data-summary-field="apparent-power" title={apparentPower.exact ?? undefined}>
            {apparentPower.display}
          </dd>
        </div>
        <div>
          <dt>Reactive power</dt>
          <dd data-summary-field="reactive-power" title={reactivePower.exact ?? undefined}>
            {reactivePower.display}
          </dd>
        </div>
        <div>
          <dt>Connected power</dt>
          <dd data-summary-field="connected-power" title={connectedPower.exact ?? undefined}>
            {connectedPower.display}
          </dd>
        </div>
        <div>
          <dt>Demand before coincidence</dt>
          <dd
            data-summary-field="pre-coincidence-demand"
            title={preCoincidenceDemand.exact ?? undefined}
          >
            {preCoincidenceDemand.display}
          </dd>
        </div>
        <div>
          <dt>Coincidence factor</dt>
          <dd data-summary-field="coincidence-factor" title={coincidenceFactor.exact ?? undefined}>
            {coincidenceNotEstablished
              ? `${coincidenceFactor.display} (not established)`
              : coincidenceFactor.display}
          </dd>
        </div>
        <div>
          <dt>Loads</dt>
          <dd data-summary-field="loads">{result.load_results.length}</dd>
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

export { STATUS_LABELS, STATUS_TONE };
