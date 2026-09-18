import type { ShortCircuitStudyResponse } from "../services/fault";
import { formatQuantity } from "../utils/formatQuantity";

const STATUS_LABELS: Record<ShortCircuitStudyResponse["status"], string> = {
  CALCULATED: "Study calculated",
  WARNING: "Calculated with warnings",
  INDETERMINATE: "Result indeterminate",
};

// A fault study has no pass/fail: the tone states how far the result can be
// relied on, not whether equipment duties are met.
const STATUS_TONE: Record<ShortCircuitStudyResponse["status"], "pass" | "fail" | "warning"> = {
  CALCULATED: "pass",
  WARNING: "warning",
  INDETERMINATE: "fail",
};

type FaultResultSummaryProps = {
  result: ShortCircuitStudyResponse;
};

// The decisive values first (Master Prompt v2.1 section 19): study state, the
// initial symmetrical and peak currents, X/R and the warning count.
// Display rule A12: four significant figures on screen, the exact engine
// decimal in the tooltip (title attribute).
export function FaultResultSummary({ result }: FaultResultSummaryProps) {
  const tone = STATUS_TONE[result.status];
  const warningCount = result.warnings.length;
  const faultType = result.fault_type.split("_").join(" ").toLowerCase();

  const initialCurrent = formatQuantity(result.initial_symmetrical_short_circuit_current_ka, "kA");
  const peakCurrent = formatQuantity(result.peak_short_circuit_current_ka, "kA");
  const earthFaultCurrent = formatQuantity(result.earth_fault_current_ka, "kA");
  const xrRatio = formatQuantity(result.x_r_ratio);

  return (
    <section aria-label="Result summary" data-summary-tone={tone}>
      <header>
        <p data-summary-status={result.status}>{STATUS_LABELS[result.status]}</p>
        <p>
          Study <strong>{result.study_code}</strong> · {faultType} fault at{" "}
          {result.fault_bus_code} · {result.calculation_case.toLowerCase()} case ·{" "}
          {result.jurisdiction_profile} profile · references{" "}
          {result.reference_verification_status.toLowerCase()}
        </p>
      </header>
      <dl data-summary-strip>
        <div>
          <dt>Initial symmetrical current</dt>
          <dd data-summary-field="initial-current" title={initialCurrent.exact ?? undefined}>
            {initialCurrent.display}
          </dd>
        </div>
        <div>
          <dt>Peak current</dt>
          <dd data-summary-field="peak-current" title={peakCurrent.exact ?? undefined}>
            {peakCurrent.display}
          </dd>
        </div>
        {earthFaultCurrent.exact ? (
          <div>
            <dt>Earth-fault current</dt>
            <dd data-summary-field="earth-fault-current" title={earthFaultCurrent.exact}>
              {earthFaultCurrent.display}
            </dd>
          </div>
        ) : null}
        <div>
          <dt>X/R ratio</dt>
          <dd data-summary-field="x-r-ratio" title={xrRatio.exact ?? undefined}>
            {xrRatio.display}
          </dd>
        </div>
        <div>
          <dt>Warnings</dt>
          <dd data-summary-warnings={warningCount}>{warningCount}</dd>
        </div>
      </dl>
    </section>
  );
}
