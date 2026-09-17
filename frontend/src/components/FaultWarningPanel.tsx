import type { ShortCircuitStudyResponse } from "../services/fault";

type FaultEngineeringWarning = ShortCircuitStudyResponse["warnings"][number];
type WarningCode = FaultEngineeringWarning["code"];
type WarningSeverity = FaultEngineeringWarning["severity"];

interface FaultWarningPanelProps {
  warnings: FaultEngineeringWarning[];
}

const NO_WARNINGS_TEXT = "No engineering warnings raised.";

// Exhaustive maps: a new code or severity without a label is a compile error.
const WARNING_CODE_LABELS: Record<WarningCode, string> = {
  NO_FAULT_CURRENT_PATH: "No fault current path",
  ZERO_SEQUENCE_PATH_BLOCKED: "Zero-sequence path blocked",
  INCOMPLETE_SEQUENCE_DATA: "Incomplete sequence data",
  CURRENT_INJECTION_APPROXIMATION: "Current-injection source approximated",
  PEAK_CURRENT_NOT_EVALUATED: "Peak current not evaluated",
  BREAKING_CURRENT_NOT_EVALUATED: "Breaking current not evaluated",
  STEADY_STATE_CURRENT_NOT_EVALUATED: "Steady-state current not evaluated",
  THERMAL_CURRENT_NOT_EVALUATED: "Thermal equivalent current not evaluated",
  ENGINEERING_REVIEW_REQUIRED: "Engineering review required",
  CALCULATION_FAILED: "Calculation failed",
};

const SEVERITY_LABELS: Record<WarningSeverity, string> = {
  WARNING: "Warning",
  ERROR: "Error",
};

export function FaultWarningPanel({ warnings }: FaultWarningPanelProps) {
  return (
    <section aria-label="Engineering warnings">
      <h3>Engineering warnings</h3>
      {warnings.length === 0 ? (
        <p data-no-warnings="true">{NO_WARNINGS_TEXT}</p>
      ) : (
        <ul data-warning-count={warnings.length}>
          {warnings.map((warning, index) => (
            <li
              key={`${warning.code}-${index}`}
              data-warning-code={warning.code}
              data-warning-severity={warning.severity}
            >
              <strong>
                {SEVERITY_LABELS[warning.severity]}
                {" - "}
                {WARNING_CODE_LABELS[warning.code]}
              </strong>
              {": "}
              <span>{warning.message}</span>
              {warning.reference_code ? (
                <>
                  {" "}
                  <small data-warning-reference={warning.reference_code}>
                    (Reference: <code>{warning.reference_code}</code>)
                  </small>
                </>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export default FaultWarningPanel;
