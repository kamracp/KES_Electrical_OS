import type { TransformerSizingResponse } from "../services/transformerSizing";
import type { TransformerSizingWarningCode } from "../services/transformerSizingContract";
import { EMPTY_QUANTITY, formatQuantity } from "../utils/formatQuantity";
import { REDUNDANCY_LABELS, STATUS_LABELS } from "./TransformerResultSummary";

interface ValueRow {
  key: string;
  label: string;
  // Decimal values are exact backend strings: four significant figures on
  // screen, the exact value in the tooltip (display rule A12). The unit is in
  // the row label. null renders as an em dash.
  value: string | null;
  // The warnings that say this figure was assumed rather than established. A
  // single factor names its own code; the combined derating factor names all
  // three, because any one of them makes the product an assumption too.
  notEstablishedCodes?: readonly TransformerSizingWarningCode[];
  // What follows the figure when one of those warnings is present.
  assumedSuffix?: string;
}

interface TransformerResultPanelProps {
  result: TransformerSizingResponse;
}

const NOT_ESTABLISHED_SUFFIX = " (not established)";
const INCLUDES_NOT_ESTABLISHED_SUFFIX = " (includes a not-established factor)";

// The three factors the combined derating factor is the product of.
const DERATING_CODES = [
  "AMBIENT_DERATING_NOT_ESTABLISHED",
  "ALTITUDE_DERATING_NOT_ESTABLISHED",
  "HARMONIC_DERATING_NOT_ESTABLISHED",
] as const satisfies readonly TransformerSizingWarningCode[];

function demandRows(result: TransformerSizingResponse): ValueRow[] {
  return [
    { key: "demand_power_kw", label: "Demand power (kW)", value: result.demand_power_kw },
    { key: "demand_power_factor", label: "Power factor", value: result.demand_power_factor },
    { key: "base_demand_kva", label: "Base demand (kVA)", value: result.base_demand_kva },
    {
      key: "future_growth_factor",
      label: "Future growth factor",
      value: result.future_growth_factor,
      notEstablishedCodes: ["GROWTH_FACTOR_NOT_ESTABLISHED"],
    },
    { key: "future_demand_kva", label: "Future demand (kVA)", value: result.future_demand_kva },
    {
      key: "design_margin_factor",
      label: "Design margin factor",
      value: result.design_margin_factor,
      notEstablishedCodes: ["DESIGN_MARGIN_NOT_ESTABLISHED"],
    },
    {
      key: "design_required_kva",
      label: "Design required (kVA)",
      value: result.design_required_kva,
    },
    {
      key: "combined_derating_factor",
      label: "Combined derating factor",
      value: result.combined_derating_factor,
      notEstablishedCodes: DERATING_CODES,
      assumedSuffix: INCLUDES_NOT_ESTABLISHED_SUFFIX,
    },
    {
      key: "required_nameplate_capacity_kva",
      label: "Required nameplate capacity (kVA)",
      value: result.required_nameplate_capacity_kva,
    },
  ];
}

function selectionRows(result: TransformerSizingResponse): ValueRow[] {
  return [
    {
      key: "required_unit_rating_kva",
      label: "Required unit rating (kVA)",
      value: result.required_unit_rating_kva,
    },
    {
      key: "installed_nameplate_capacity_kva",
      label: "Installed capacity (kVA)",
      value: result.installed_nameplate_capacity_kva,
    },
    {
      key: "derated_duty_capacity_kva",
      label: "Derated duty capacity (kVA)",
      value: result.derated_duty_capacity_kva,
    },
    {
      key: "spare_derated_capacity_kva",
      label: "Spare derated capacity (kVA)",
      value: result.spare_derated_capacity_kva,
    },
    { key: "loading_percent", label: "Loading (%)", value: result.loading_percent },
  ];
}

function ValueTable({
  title,
  rows,
  warningCodes,
}: {
  title: string;
  rows: ValueRow[];
  warningCodes: ReadonlySet<string>;
}) {
  return (
    <section aria-label={title}>
      <h3>{title}</h3>
      <div data-table-scroll>
        <table>
          <thead>
            <tr>
              <th scope="col">Parameter</th>
              <th scope="col">Value</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const quantity = formatQuantity(row.value);
              // A factor is always a figure; only the warning says whether the
              // engineer established it (A16 (a)). The tooltip keeps the exact
              // value either way.
              const assumed =
                row.notEstablishedCodes?.some((code) => warningCodes.has(code)) ?? false;
              const suffix = row.assumedSuffix ?? NOT_ESTABLISHED_SUFFIX;
              return (
                <tr key={row.key} data-row-key={row.key}>
                  <th scope="row">{row.label}</th>
                  <td title={quantity.exact ?? undefined}>
                    {assumed ? `${quantity.display}${suffix}` : quantity.display}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export function TransformerResultPanel({ result }: TransformerResultPanelProps) {
  const warningCodes = new Set<string>(result.warnings.map((warning) => warning.code));

  return (
    <article aria-label="Transformer sizing result">
      <header>
        <h2>Transformer sizing result</h2>
        <p>
          Study code: <strong data-study-code="true">{result.code}</strong>
          {" - "}
          {result.name}
        </p>
        <p>
          Overall status:{" "}
          <strong data-result-status={result.status}>{STATUS_LABELS[result.status]}</strong>
        </p>
      </header>

      <ValueTable
        title="Demand and design"
        rows={demandRows(result)}
        warningCodes={warningCodes}
      />

      <section aria-label="Selection">
        <h3>Selection</h3>
        <div data-table-scroll>
          <table>
            <thead>
              <tr>
                <th scope="col">Parameter</th>
                <th scope="col">Value</th>
              </tr>
            </thead>
            <tbody>
              <tr data-row-key="selected_unit_rating_kva">
                <th scope="row">Selected unit rating (kVA)</th>
                {/* A catalogue value from the project design basis: shown as
                    sent, so the engineer reads back an orderable rating. */}
                <td>{result.selected_unit_rating_kva ?? EMPTY_QUANTITY}</td>
              </tr>
              <tr data-row-key="duty_units">
                <th scope="row">Duty units</th>
                {/* Counts, not engineering quantities. */}
                <td>{result.duty_units}</td>
              </tr>
              <tr data-row-key="standby_units">
                <th scope="row">Standby units</th>
                <td>{result.standby_units}</td>
              </tr>
              <tr data-row-key="total_units">
                <th scope="row">Total units</th>
                <td>{result.total_units}</td>
              </tr>
              <tr data-row-key="redundancy_mode">
                <th scope="row">Redundancy mode</th>
                <td data-redundancy-mode={result.redundancy_mode}>
                  {REDUNDANCY_LABELS[result.redundancy_mode]}
                </td>
              </tr>
              {selectionRows(result).map((row) => {
                const quantity = formatQuantity(row.value);
                return (
                  <tr key={row.key} data-row-key={row.key}>
                    <th scope="row">{row.label}</th>
                    <td title={quantity.exact ?? undefined}>{quantity.display}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      <section aria-label="Jurisdiction profile">
        <h3>Jurisdiction profile</h3>
        <p data-jurisdiction-profile={result.jurisdiction_profile}>
          Designed under the {result.jurisdiction_profile} profile. The sizing itself carries
          no profile-dependent value; the profile is recorded with the run and must match the
          design basis of the project revision.
        </p>
      </section>

      <footer>
        <p>
          Calculation results are engineering design checks, not a statutory compliance
          declaration. Confirm the governing project basis, the demand data, the rating
          schedule and every growth, margin and derating factor before approval or issue.
        </p>
      </footer>
    </article>
  );
}

export default TransformerResultPanel;
