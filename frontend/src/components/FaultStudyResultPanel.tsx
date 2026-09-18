import type {
  JurisdictionProfile,
  ReferenceVerificationStatus,
} from "../services/cableContract";
import type { ShortCircuitStudyResponse } from "../services/fault";
import { formatQuantity } from "../utils/formatQuantity";

// Derive nested types from the contract so schema drift fails typecheck here.
type SequenceResult = ShortCircuitStudyResponse["sequence_results"][number];
type SourceContribution = ShortCircuitStudyResponse["source_contributions"][number];
type ResultStatus = ShortCircuitStudyResponse["status"];
type FaultType = ShortCircuitStudyResponse["fault_type"];
type CalculationCase = ShortCircuitStudyResponse["calculation_case"];
type Sequence = SequenceResult["sequence"];
type SourceType = SourceContribution["source_type"];
type Representation = SourceContribution["representation"];
type ReferenceSource = ShortCircuitStudyResponse["reference_source"];

interface CurrentRow {
  key: string;
  label: string;
  // Decimal values are exact backend strings: four significant figures on
  // screen, the exact value in the tooltip (display rule A12); null renders as
  // an em dash. The unit is in the row label.
  value: string | null;
}

interface FaultStudyResultPanelProps {
  result: ShortCircuitStudyResponse;
}

const EMPTY_VALUE_TEXT = "\u2014";
const NO_ROWS_TEXT = "None reported";

// Exhaustive maps: adding an enum member without a label is a compile error.
const RESULT_STATUS_LABELS: Record<ResultStatus, string> = {
  CALCULATED: "Calculated",
  WARNING: "Calculated with warnings",
  INDETERMINATE: "Indeterminate - review required",
};

const FAULT_TYPE_LABELS: Record<FaultType, string> = {
  THREE_PHASE: "Three-phase",
  TWO_PHASE: "Phase-to-phase",
  TWO_PHASE_TO_EARTH: "Phase-to-phase-to-earth",
  SINGLE_PHASE_TO_EARTH: "Single-phase-to-earth",
};

const CASE_LABELS: Record<CalculationCase, string> = {
  MAXIMUM: "Maximum",
  MINIMUM: "Minimum",
};

const SEQUENCE_LABELS: Record<Sequence, string> = {
  POSITIVE: "Positive",
  NEGATIVE: "Negative",
  ZERO: "Zero",
};

const SOURCE_TYPE_LABELS: Record<SourceType, string> = {
  UTILITY_GRID: "Utility grid",
  SYNCHRONOUS_GENERATOR: "Synchronous generator",
  ASYNCHRONOUS_MOTOR: "Asynchronous motor",
  INVERTER_BASED_RESOURCE: "Inverter-based resource",
  EQUIVALENT_SOURCE: "Equivalent source",
};

const REPRESENTATION_LABELS: Record<Representation, string> = {
  VOLTAGE_BEHIND_IMPEDANCE: "Voltage behind impedance",
  CURRENT_INJECTION: "Current injection",
};

// Exhaustive maps: a new profile, status or source without a label is a compile error.
const JURISDICTION_LABELS: Record<JurisdictionProfile, string> = {
  IN: "India (CEA Regulations, IS, CPWD)",
  IEC: "IEC (international)",
  US: "United States (NEC / NFPA 70)",
  UK: "United Kingdom (BS 7671)",
  AU_NZ: "Australia / New Zealand (AS/NZS 3000)",
  EU: "European Union (HD 60364)",
};

const VERIFICATION_LABELS: Record<ReferenceVerificationStatus, string> = {
  VERIFIED: "Verified",
  UNVERIFIED: "Unverified",
  LEGACY: "Legacy",
  REFERENCE_ONLY: "Reference only",
  UNRESOLVED: "Unresolved - reference data pending",
};

const REFERENCE_SOURCE_LABELS: Record<ReferenceSource, string> = {
  PROFILE: "Jurisdiction profile",
  REQUEST_OVERRIDE: "Project override - deviation from profile",
  NOT_ESTABLISHED: "Not established",
};

const REFERENCE_PENDING_TEXT =
  "Reference pending - not registered for this jurisdiction profile";

function ReferenceValue({ value }: { value: string | null }) {
  if (value === null) {
    return <dd data-reference-pending="true">{REFERENCE_PENDING_TEXT}</dd>;
  }
  return <dd>{value}</dd>;
}

// Descriptive text (codes, reasons). Quantities go through QuantityCell.
function formatText(value: string | null): string {
  return value === null ? EMPTY_VALUE_TEXT : value;
}

interface QuantityCellProps {
  value: string | null;
  // Adds data-evaluated so a not-evaluated current can be told from a value.
  markEvaluated?: boolean;
}

function QuantityCell({ value, markEvaluated = false }: QuantityCellProps) {
  const quantity = formatQuantity(value);
  const evaluated = value === null ? "false" : "true";
  return (
    <td data-evaluated={markEvaluated ? evaluated : undefined} title={quantity.exact ?? undefined}>
      {quantity.display}
    </td>
  );
}

function formatCodes(codes: string[]): string {
  return codes.length === 0 ? EMPTY_VALUE_TEXT : codes.join(", ");
}

function currentRows(result: ShortCircuitStudyResponse): CurrentRow[] {
  return [
    {
      key: "initial_symmetrical_short_circuit_current_ka",
      label: "Initial symmetrical short-circuit current Ik'' (kA)",
      value: result.initial_symmetrical_short_circuit_current_ka,
    },
    {
      key: "peak_short_circuit_current_ka",
      label: "Peak short-circuit current ip (kA)",
      value: result.peak_short_circuit_current_ka,
    },
    {
      key: "symmetrical_breaking_current_ka",
      label: "Symmetrical breaking current Ib (kA)",
      value: result.symmetrical_breaking_current_ka,
    },
    {
      key: "steady_state_short_circuit_current_ka",
      label: "Steady-state short-circuit current Ik (kA)",
      value: result.steady_state_short_circuit_current_ka,
    },
    {
      key: "thermal_equivalent_short_circuit_current_ka",
      label: "Thermal equivalent current Ith (kA)",
      value: result.thermal_equivalent_short_circuit_current_ka,
    },
    {
      key: "earth_fault_current_ka",
      label: "Earth-fault current (kA)",
      value: result.earth_fault_current_ka,
    },
    { key: "kappa_factor", label: "Peak factor kappa", value: result.kappa_factor },
    { key: "x_r_ratio", label: "X/R ratio", value: result.x_r_ratio },
    { key: "clearing_time_s", label: "Clearing time (s)", value: result.clearing_time_s },
  ];
}

function CurrentsTable({ rows }: { rows: CurrentRow[] }) {
  return (
    <section aria-label="Fault currents">
      <h3>Fault currents</h3>
      <table>
        <thead>
          <tr>
            <th scope="col">Parameter</th>
            <th scope="col">Value</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.key} data-row-key={row.key}>
              <th scope="row">{row.label}</th>
              <QuantityCell value={row.value} markEvaluated />
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

function SequenceTable({ rows }: { rows: SequenceResult[] }) {
  return (
    <section aria-label="Sequence impedances">
      <h3>Sequence impedances at the fault bus</h3>
      {rows.length === 0 ? (
        <p data-no-rows="true">{NO_ROWS_TEXT}</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th scope="col">Sequence</th>
              <th scope="col">Available</th>
              <th scope="col">R (ohm)</th>
              <th scope="col">X (ohm)</th>
              <th scope="col">Path references</th>
              <th scope="col">Blocking references</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.sequence} data-sequence={row.sequence}>
                <th scope="row">{SEQUENCE_LABELS[row.sequence]}</th>
                <td data-available={row.available ? "true" : "false"}>
                  {row.available ? "Yes" : "No"}
                </td>
                <QuantityCell value={row.resistance_ohm} />
                <QuantityCell value={row.reactance_ohm} />
                <td>{formatCodes(row.path_reference_codes)}</td>
                <td>{formatCodes(row.blocking_reference_codes)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}

function ContributionsTable({ rows }: { rows: SourceContribution[] }) {
  return (
    <section aria-label="Source contributions">
      <h3>Source contributions</h3>
      {rows.length === 0 ? (
        <p data-no-rows="true">{NO_ROWS_TEXT}</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th scope="col">Source</th>
              <th scope="col">Type</th>
              <th scope="col">Representation</th>
              <th scope="col">Included</th>
              <th scope="col">Ik'' (kA)</th>
              <th scope="col">ip (kA)</th>
              <th scope="col">Exclusion reason</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.source_code} data-source-code={row.source_code}>
                <th scope="row">{row.source_code}</th>
                <td>{SOURCE_TYPE_LABELS[row.source_type]}</td>
                <td>{REPRESENTATION_LABELS[row.representation]}</td>
                <td data-included={row.included ? "true" : "false"}>
                  {row.included ? "Yes" : "No"}
                </td>
                <QuantityCell value={row.initial_symmetrical_current_ka} />
                <QuantityCell value={row.peak_current_ka} />
                <td>{formatText(row.exclusion_reason)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}

export function FaultStudyResultPanel({ result }: FaultStudyResultPanelProps) {
  return (
    <article aria-label="Fault study result">
      <header>
        <h2>Fault study result</h2>
        <p>
          Study code: <strong data-study-code="true">{result.study_code}</strong>
          {" - "}
          {result.study_name}
        </p>
        <p>
          Overall status:{" "}
          <strong data-result-status={result.status}>{RESULT_STATUS_LABELS[result.status]}</strong>
        </p>
      </header>

      <section aria-label="Fault definition">
        <h3>Fault definition</h3>
        <dl>
          <dt>Fault bus</dt>
          <dd data-fault-bus={result.fault_bus_code}>{result.fault_bus_code}</dd>
          <dt>Fault type</dt>
          <dd data-fault-type={result.fault_type}>{FAULT_TYPE_LABELS[result.fault_type]}</dd>
          <dt>Calculation case</dt>
          <dd data-calculation-case={result.calculation_case}>
            {CASE_LABELS[result.calculation_case]}
          </dd>
          <dt>Nominal voltage (V)</dt>
          <dd>{result.nominal_voltage_v}</dd>
          <dt>Frequency (Hz)</dt>
          <dd>{result.frequency_hz}</dd>
          <dt>Operating state</dt>
          <dd>{formatText(result.operating_state_code)}</dd>
        </dl>
      </section>

      <CurrentsTable rows={currentRows(result)} />
      <SequenceTable rows={result.sequence_results} />
      <ContributionsTable rows={result.source_contributions} />

      <section aria-label="References">
        <h3>References</h3>
        <dl>
          <dt>Short-circuit standard</dt>
          <ReferenceValue value={result.standard_reference} />
          <dt>Earth-current basis</dt>
          <ReferenceValue value={result.earth_current_reference} />
          <dt>Reference source</dt>
          <dd data-reference-source={result.reference_source}>
            {REFERENCE_SOURCE_LABELS[result.reference_source]}
          </dd>
          <dt>Jurisdiction profile</dt>
          <dd data-jurisdiction-profile={result.jurisdiction_profile}>
            {JURISDICTION_LABELS[result.jurisdiction_profile]}
          </dd>
          <dt>Reference data status</dt>
          <dd data-reference-verification-status={result.reference_verification_status}>
            {VERIFICATION_LABELS[result.reference_verification_status]}
          </dd>
        </dl>
        {result.notes ? <p data-notes="true">{result.notes}</p> : null}
      </section>

      <footer>
        <p>
          Calculation results are engineering design checks, not a statutory compliance
          declaration. Confirm the governing project basis, the verified edition of the
          applicable standard, network data and protective device duties before approval or
          issue.
        </p>
      </footer>
    </article>
  );
}

export default FaultStudyResultPanel;
