import type { LoadWarning } from "../services/loadDemand";

type WarningCode = LoadWarning["code"];

interface LoadWarningPanelProps {
  warnings: LoadWarning[];
}

const NO_WARNINGS_TEXT = "No engineering warnings raised.";

// Exhaustive map: a new code without a label is a compile error. A load warning
// carries only a code and a message - there is no severity and no reference
// field on this contract, so none is shown.
const WARNING_CODE_LABELS: Record<WarningCode, string> = {
  ZERO_DEMAND: "Zero demand",
  UTILIZATION_FACTOR_NOT_ESTABLISHED: "Utilization factor not established",
  DEMAND_FACTOR_NOT_ESTABLISHED: "Demand factor not established",
  EFFICIENCY_NOT_ESTABLISHED: "Efficiency not established",
  COINCIDENCE_FACTOR_NOT_ESTABLISHED: "Coincidence factor not established",
};

export function LoadWarningPanel({ warnings }: LoadWarningPanelProps) {
  return (
    <section aria-label="Engineering warnings">
      <h3>Engineering warnings</h3>
      {warnings.length === 0 ? (
        <p data-no-warnings="true">{NO_WARNINGS_TEXT}</p>
      ) : (
        <ul data-warning-count={warnings.length}>
          {warnings.map((warning, index) => (
            <li key={`${warning.code}-${index}`} data-warning-code={warning.code}>
              <strong>{WARNING_CODE_LABELS[warning.code]}</strong>
              {": "}
              {/* The engine's own sentence; a warning that came from one load of
                  the schedule still names that load with its code prefix. */}
              <span>{warning.message}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export { WARNING_CODE_LABELS };

export default LoadWarningPanel;
