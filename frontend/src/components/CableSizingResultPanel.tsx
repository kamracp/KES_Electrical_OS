import type {
  CableReferenceSource,
  JurisdictionProfile,
  ReferenceVerificationStatus,
} from "../services/cableContract";
import type { CableSizingResponse } from "../services/cable";
import { formatQuantity } from "../utils/formatQuantity";

// Derive nested types from the contract so schema drift fails typecheck here.
type ConductorResult = NonNullable<CableSizingResponse["conductor"]>;
type AmpacityResult = NonNullable<CableSizingResponse["ampacity"]>;
type VoltageDropResult = NonNullable<CableSizingResponse["voltage_drop"]>;
type ShortCircuitResult = NonNullable<CableSizingResponse["short_circuit"]>;
type CheckStatus = AmpacityResult["status"];
type SizingStatus = CableSizingResponse["status"];

interface CheckRow {
  key: string;
  label: string;
  // Decimal values are exact backend strings: four significant figures on
  // screen, the exact value in the tooltip (display rule A12). The unit is in
  // the row label. Integers are rendered as-is.
  value: string | number | null;
  // Set for descriptive text that is not a quantity.
  text?: true;
  status?: CheckStatus;
}

interface CheckTableProps {
  title: string;
  rows: CheckRow[] | null;
}

interface CableSizingResultPanelProps {
  result: CableSizingResponse;
}

const NOT_EVALUATED_TEXT = "Not evaluated";
const EMPTY_VALUE_TEXT = "\u2014";

// Exhaustive maps: adding an enum member without a label is a compile error.
const SIZING_STATUS_LABELS: Record<SizingStatus, string> = {
  DESIGN_CHECK_PASSED: "Design check passed",
  DESIGN_CHECK_FAILED: "Design check failed",
  NO_STANDARD_SIZE_AVAILABLE: "No standard size available",
  REVIEW_REQUIRED: "Engineering review required",
};

const CHECK_STATUS_LABELS: Record<CheckStatus, string> = {
  PASS: "Pass",
  FAIL: "Fail",
  NOT_APPLICABLE: "N/A",
};

function ValueCell({ row }: { row: CheckRow }) {
  const { value } = row;
  if (value === null) {
    return <td>{EMPTY_VALUE_TEXT}</td>;
  }
  if (typeof value === "number" || row.text) {
    return <td>{String(value)}</td>;
  }
  const quantity = formatQuantity(value);
  return <td title={quantity.exact ?? undefined}>{quantity.display}</td>;
}

function conductorRows(section: ConductorResult): CheckRow[] {
  return [
    { key: "phase_area_mm2", label: "Phase conductor area (mm²)", value: section.phase_area_mm2 },
    {
      key: "neutral_area_mm2",
      label: "Neutral conductor area (mm²)",
      value: section.neutral_area_mm2,
      status: section.neutral_status,
    },
    {
      key: "protective_area_mm2",
      label: "Protective conductor area (mm²)",
      value: section.protective_area_mm2,
      status: section.protective_status,
    },
    { key: "parallel_runs", label: "Parallel runs", value: section.parallel_runs },
    {
      key: "phase_conductors_per_run",
      label: "Phase conductors per run",
      value: section.phase_conductors_per_run,
    },
  ];
}

function ampacityRows(section: AmpacityResult): CheckRow[] {
  return [
    {
      key: "tabulated_ampacity_a_per_run",
      label: "Tabulated ampacity per run (A)",
      value: section.tabulated_ampacity_a_per_run,
    },
    {
      key: "combined_derating_factor",
      label: "Combined derating factor",
      value: section.combined_derating_factor,
    },
    {
      key: "derating_established",
      label: "Derating factors",
      value: section.derating_established
        ? "Established"
        : `Not established: ${section.unestablished_derating_factors.join(", ")}`,
      text: true,
    },
    {
      key: "derated_ampacity_a_per_run",
      label: "Derated ampacity per run (A)",
      value: section.derated_ampacity_a_per_run,
    },
    { key: "parallel_runs", label: "Parallel runs", value: section.parallel_runs },
    {
      key: "total_installed_ampacity_a",
      label: "Total installed ampacity (A)",
      value: section.total_installed_ampacity_a,
    },
    { key: "design_current_a", label: "Design current (A)", value: section.design_current_a },
    {
      key: "required_tabulated_ampacity_a_per_run",
      label: "Required tabulated ampacity per run (A)",
      value: section.required_tabulated_ampacity_a_per_run,
    },
    {
      key: "utilization_ratio",
      label: "Utilization ratio",
      value: section.utilization_ratio,
      status: section.status,
    },
  ];
}

function voltageDropRows(section: VoltageDropResult): CheckRow[] {
  return [
    {
      key: "resistance_ohm_per_km",
      label: "Resistance (Ω/km)",
      value: section.resistance_ohm_per_km,
    },
    {
      key: "reactance_ohm_per_km",
      label: "Reactance (Ω/km)",
      value: section.reactance_ohm_per_km,
    },
    { key: "voltage_drop_v", label: "Voltage drop (V)", value: section.voltage_drop_v },
    {
      key: "voltage_drop_percent",
      label: "Voltage drop (%)",
      value: section.voltage_drop_percent,
      status: section.status,
    },
    {
      key: "allowable_voltage_drop_percent",
      label: "Allowable voltage drop (%)",
      value: section.allowable_voltage_drop_percent,
    },
  ];
}

function shortCircuitRows(section: ShortCircuitResult): CheckRow[] {
  return [
    { key: "fault_current_ka", label: "Fault current (kA)", value: section.fault_current_ka },
    { key: "fault_duration_s", label: "Fault duration (s)", value: section.fault_duration_s },
    {
      key: "material_constant_k",
      label: "Material constant k",
      value: section.material_constant_k,
    },
    { key: "required_area_mm2", label: "Required area (mm²)", value: section.required_area_mm2 },
    {
      key: "selected_area_mm2",
      label: "Selected area (mm²)",
      value: section.selected_area_mm2,
      status: section.status,
    },
    {
      key: "withstand_current_ka",
      label: "Withstand current (kA)",
      value: section.withstand_current_ka,
    },
  ];
}

function CheckTable({ title, rows }: CheckTableProps) {
  if (rows === null) {
    return (
      <section aria-label={title}>
        <h3>{title}</h3>
        <p data-not-evaluated="true">{NOT_EVALUATED_TEXT}</p>
      </section>
    );
  }

  return (
    <section aria-label={title}>
      <h3>{title}</h3>
      <table>
        <thead>
          <tr>
            <th scope="col">Parameter</th>
            <th scope="col">Value</th>
            <th scope="col">Status</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.key} data-row-key={row.key}>
              <th scope="row">{row.label}</th>
              <ValueCell row={row} />
              <td data-check-status={row.status ?? ""}>
                {row.status ? CHECK_STATUS_LABELS[row.status] : EMPTY_VALUE_TEXT}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

// Exhaustive maps: a new profile or status without a label is a compile error.
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

const REFERENCE_SOURCE_LABELS: Record<CableReferenceSource, string> = {
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

export function CableSizingResultPanel({ result }: CableSizingResultPanelProps) {
  return (
    <article aria-label="Cable sizing result">
      <header>
        <h2>Cable sizing result</h2>
        <p>
          Study code: <strong data-study-code="true">{result.study_code}</strong>
        </p>
        <p>
          Overall status:{" "}
          <strong data-sizing-status={result.status}>{SIZING_STATUS_LABELS[result.status]}</strong>
        </p>
      </header>

      <CheckTable
        title="Conductor selection"
        rows={result.conductor ? conductorRows(result.conductor) : null}
      />
      <CheckTable
        title="Ampacity check"
        rows={result.ampacity ? ampacityRows(result.ampacity) : null}
      />
      <CheckTable
        title="Voltage drop check"
        rows={result.voltage_drop ? voltageDropRows(result.voltage_drop) : null}
      />
      <CheckTable
        title="Short-circuit withstand check"
        rows={result.short_circuit ? shortCircuitRows(result.short_circuit) : null}
      />

      <section aria-label="References">
        <h3>References</h3>
        <dl>
          <dt>Sizing standard</dt>
          <ReferenceValue value={result.standard_reference} />
          <dt>Ampacity data</dt>
          <ReferenceValue value={result.ampacity_reference} />
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
          These figures are engineering design checks against the referenced standard data. They
          are not a statutory compliance certification and require independent engineering review
          before use.
        </p>
      </footer>
    </article>
  );
}

export default CableSizingResultPanel;
