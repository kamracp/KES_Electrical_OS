import type { TransformerSizingWarning } from "../services/transformerSizing";

type WarningCode = TransformerSizingWarning["code"];

interface TransformerWarningPanelProps {
  warnings: TransformerSizingWarning[];
}

const NO_WARNINGS_TEXT = "No engineering warnings raised.";

// Exhaustive map: a new code without a label is a compile error. A transformer
// warning carries only a code and a message - there is no severity and no
// reference field on this contract, so none is shown.
const WARNING_CODE_LABELS: Record<WarningCode, string> = {
  DERATING_APPLIED: "Derating applied",
  NO_STANDARD_RATING_AVAILABLE: "No standard rating available",
  GROWTH_FACTOR_NOT_ESTABLISHED: "Future growth factor not established",
  DESIGN_MARGIN_NOT_ESTABLISHED: "Design margin factor not established",
  AMBIENT_DERATING_NOT_ESTABLISHED: "Ambient derating factor not established",
  ALTITUDE_DERATING_NOT_ESTABLISHED: "Altitude derating factor not established",
  HARMONIC_DERATING_NOT_ESTABLISHED: "Harmonic derating factor not established",
};

export function TransformerWarningPanel({ warnings }: TransformerWarningPanelProps) {
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
              {/* The engine's own sentence, kept as it was sent. */}
              <span>{warning.message}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export { WARNING_CODE_LABELS };

export default TransformerWarningPanel;
