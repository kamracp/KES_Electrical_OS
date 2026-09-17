import type { CableEngineeringWarning } from "../services/cable";

type WarningCode = CableEngineeringWarning["code"];

interface CableWarningPanelProps {
  warnings: CableEngineeringWarning[];
}

const NO_WARNINGS_TEXT = "No engineering warnings raised.";

// Exhaustive map: a new warning code without a label is a compile error.
const WARNING_CODE_LABELS: Record<WarningCode, string> = {
  AMPACITY_INADEQUATE: "Ampacity inadequate",
  VOLTAGE_DROP_EXCEEDED: "Voltage drop exceeded",
  SHORT_CIRCUIT_WITHSTAND_INADEQUATE: "Short-circuit withstand inadequate",
  NEUTRAL_SIZE_INADEQUATE: "Neutral size inadequate",
  PROTECTIVE_CONDUCTOR_INADEQUATE: "Protective conductor inadequate",
  HIGH_TOTAL_DERATING: "High total derating",
  PARALLEL_CABLE_CURRENT_SHARING: "Parallel cable current sharing",
  SOIL_DATA_REQUIRED: "Soil data required",
  AMBIENT_DERATING_NOT_ESTABLISHED: "Ambient derating factor not established",
  GROUPING_DERATING_NOT_ESTABLISHED: "Grouping derating factor not established",
  DERATING_FACTOR_NOT_ESTABLISHED: "Derating factor not established - engineering review required",
  GOVERNING_REFERENCE_NOT_ESTABLISHED:
    "Governing references not registered for this jurisdiction profile",
  GOVERNING_REFERENCE_OVERRIDDEN:
    "Governing references overridden by the project (deviation from profile)",
  NO_STANDARD_SIZE_AVAILABLE: "No standard size available",
};

export function CableWarningPanel({ warnings }: CableWarningPanelProps) {
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
              <span>{warning.message}</span>
              {warning.field_name ? (
                <>
                  {" "}
                  <small data-warning-field={warning.field_name}>
                    (Field: <code>{warning.field_name}</code>)
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

export default CableWarningPanel;
