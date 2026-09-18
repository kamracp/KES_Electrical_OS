import type { ShortCircuitStudyResponse } from "../services/fault";

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

function kiloamps(value: string | null | undefined): string {
  return value ? `${value} kA` : "—";
}

// The decisive values first (Master Prompt v2.1 section 19): study state, the
// initial symmetrical and peak currents, X/R and the warning count. Every
// figure is the exact decimal string from the engine.
export function FaultResultSummary({ result }: FaultResultSummaryProps) {
  const tone = STATUS_TONE[result.status];
  const warningCount = result.warnings.length;
  const faultType = result.fault_type.split("_").join(" ").toLowerCase();

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
          <dd data-summary-field="initial-current">
            {kiloamps(result.initial_symmetrical_short_circuit_current_ka)}
          </dd>
        </div>
        <div>
          <dt>Peak current</dt>
          <dd data-summary-field="peak-current">
            {kiloamps(result.peak_short_circuit_current_ka)}
          </dd>
        </div>
        {result.earth_fault_current_ka ? (
          <div>
            <dt>Earth-fault current</dt>
            <dd data-summary-field="earth-fault-current">
              {kiloamps(result.earth_fault_current_ka)}
            </dd>
          </div>
        ) : null}
        <div>
          <dt>X/R ratio</dt>
          <dd data-summary-field="x-r-ratio">{result.x_r_ratio ?? "—"}</dd>
        </div>
        <div>
          <dt>Warnings</dt>
          <dd data-summary-warnings={warningCount}>{warningCount}</dd>
        </div>
      </dl>
    </section>
  );
}
