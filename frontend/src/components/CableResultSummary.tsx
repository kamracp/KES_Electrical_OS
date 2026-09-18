import type { CableSizingResponse } from "../services/cable";
import { formatQuantity } from "../utils/formatQuantity";

const STATUS_LABELS: Record<CableSizingResponse["status"], string> = {
  DESIGN_CHECK_PASSED: "Design check passed",
  DESIGN_CHECK_FAILED: "Design check failed",
  NO_STANDARD_SIZE_AVAILABLE: "No standard size available",
  REVIEW_REQUIRED: "Engineering review required",
};

const STATUS_TONE: Record<CableSizingResponse["status"], "pass" | "fail" | "warning"> = {
  DESIGN_CHECK_PASSED: "pass",
  DESIGN_CHECK_FAILED: "fail",
  NO_STANDARD_SIZE_AVAILABLE: "fail",
  REVIEW_REQUIRED: "warning",
};

type CableResultSummaryProps = {
  result: CableSizingResponse;
};

// The decisive values first (Master Prompt v2.1 section 19): design-check
// state, selected size, thermal utilization, voltage drop, warning count.
// Display rule A12: four significant figures on screen, the exact engine
// decimal in the tooltip (title attribute).
export function CableResultSummary({ result }: CableResultSummaryProps) {
  const tone = STATUS_TONE[result.status];
  const warningCount = result.warnings.length;

  const phaseArea = formatQuantity(result.conductor?.phase_area_mm2, "mm²");
  const utilization = formatQuantity(result.ampacity?.utilization_ratio);
  const voltageDrop = formatQuantity(result.voltage_drop?.voltage_drop_percent, "%");
  const allowableDrop = formatQuantity(result.voltage_drop?.allowable_voltage_drop_percent, "%");
  const voltageDropExact =
    voltageDrop.exact && allowableDrop.exact
      ? `${voltageDrop.exact} of ${allowableDrop.exact}`
      : undefined;

  return (
    <section aria-label="Result summary" data-summary-tone={tone}>
      <header>
        <p data-summary-status={result.status}>{STATUS_LABELS[result.status]}</p>
        <p>
          Study <strong>{result.study_code}</strong> · {result.jurisdiction_profile} profile ·
          references {result.reference_verification_status.toLowerCase()}
        </p>
      </header>
      <dl data-summary-strip>
        <div>
          <dt>Phase conductor</dt>
          <dd data-summary-field="phase-conductor" title={phaseArea.exact ?? undefined}>
            {phaseArea.display}
          </dd>
        </div>
        <div>
          <dt>Thermal utilization</dt>
          <dd data-summary-field="thermal-utilization" title={utilization.exact ?? undefined}>
            {utilization.display}
          </dd>
        </div>
        <div>
          <dt>Voltage drop</dt>
          <dd data-summary-field="voltage-drop" title={voltageDropExact}>
            {result.voltage_drop ? `${voltageDrop.display} of ${allowableDrop.display}` : "—"}
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
