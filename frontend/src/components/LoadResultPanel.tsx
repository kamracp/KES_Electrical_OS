import type { LoadGroupResponse } from "../services/loadDemand";
import { formatQuantity } from "../utils/formatQuantity";
import { PHASE_SYSTEM_LABELS, SCENARIO_LABELS } from "./LoadRow";
import { STATUS_LABELS } from "./LoadResultSummary";

// Derive the nested types from the contract so schema drift fails typecheck here.
type LoadResult = LoadGroupResponse["load_results"][number];

interface TotalRow {
  key: string;
  label: string;
  // Decimal values are exact backend strings: four significant figures on
  // screen, the exact value in the tooltip (display rule A12). The unit is in
  // the row label.
  value: string;
}

interface LoadResultPanelProps {
  result: LoadGroupResponse;
}

const NO_ROWS_TEXT = "None reported";
const NOT_ESTABLISHED_SUFFIX = " (not established)";

interface QuantityCellProps {
  value: string | null;
}

function QuantityCell({ value }: QuantityCellProps) {
  const quantity = formatQuantity(value);
  return <td title={quantity.exact ?? undefined}>{quantity.display}</td>;
}

function totalRows(result: LoadGroupResponse): TotalRow[] {
  return [
    {
      key: "connected_power_kw",
      label: "Connected power (kW)",
      value: result.connected_power_kw,
    },
    {
      key: "pre_coincidence_demand_kw",
      label: "Demand before coincidence (kW)",
      value: result.pre_coincidence_demand_kw,
    },
    {
      key: "coincidence_factor",
      label: "Coincidence factor",
      value: result.coincidence_factor,
    },
    { key: "demand_power_kw", label: "Demand power (kW)", value: result.demand_power_kw },
    {
      key: "apparent_power_kva",
      label: "Apparent power (kVA)",
      value: result.apparent_power_kva,
    },
    {
      key: "reactive_power_kvar",
      label: "Reactive power (kvar)",
      value: result.reactive_power_kvar,
    },
  ];
}

function TotalsTable({
  rows,
  coincidenceNotEstablished,
}: {
  rows: TotalRow[];
  coincidenceNotEstablished: boolean;
}) {
  return (
    <section aria-label="Group totals">
      <h3>Group totals</h3>
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
            // The coincidence factor is always a figure; only the warning says
            // whether the engineer established it (A15 (a)). The tooltip keeps
            // the exact value either way.
            const isAssumedCoincidence =
              row.key === "coincidence_factor" && coincidenceNotEstablished;
            return (
              <tr key={row.key} data-row-key={row.key}>
                <th scope="row">{row.label}</th>
                <td title={quantity.exact ?? undefined}>
                  {isAssumedCoincidence
                    ? `${quantity.display}${NOT_ESTABLISHED_SUFFIX}`
                    : quantity.display}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </section>
  );
}

function LoadsTable({ rows }: { rows: LoadResult[] }) {
  return (
    <section aria-label="Loads">
      <h3>Loads</h3>
      {rows.length === 0 ? (
        <p data-no-rows="true">{NO_ROWS_TEXT}</p>
      ) : (
        <div data-table-scroll>
          <table>
            <thead>
              <tr>
                <th scope="col">Code</th>
                <th scope="col">Name</th>
                <th scope="col">Scenario</th>
                <th scope="col">Phase</th>
                <th scope="col">Connected (kW)</th>
                <th scope="col">Utilized (kW)</th>
                <th scope="col">Demand (kW)</th>
                <th scope="col">Apparent (kVA)</th>
                <th scope="col">Reactive (kvar)</th>
                <th scope="col">Design current (A)</th>
                <th scope="col">Status</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.load_code} data-load-code={row.load_code}>
                  <th scope="row">{row.load_code}</th>
                  <td>{row.load_name}</td>
                  <td data-scenario={row.scenario}>{SCENARIO_LABELS[row.scenario]}</td>
                  <td data-phase-system={row.phase_system}>
                    {PHASE_SYSTEM_LABELS[row.phase_system]}
                  </td>
                  <QuantityCell value={row.connected_power_kw} />
                  <QuantityCell value={row.utilized_power_kw} />
                  <QuantityCell value={row.demand_power_kw} />
                  <QuantityCell value={row.apparent_power_kva} />
                  <QuantityCell value={row.reactive_power_kvar} />
                  <QuantityCell value={row.design_current_a} />
                  <td data-load-status={row.status}>{STATUS_LABELS[row.status]}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

export function LoadResultPanel({ result }: LoadResultPanelProps) {
  const coincidenceNotEstablished = result.warnings.some(
    (warning) => warning.code === "COINCIDENCE_FACTOR_NOT_ESTABLISHED",
  );

  return (
    <article aria-label="Load study result">
      <header>
        <h2>Load study result</h2>
        <p>
          Study code: <strong data-study-code="true">{result.group_code}</strong>
          {" - "}
          {result.group_name}
        </p>
        <p>
          Overall status:{" "}
          <strong data-result-status={result.status}>{STATUS_LABELS[result.status]}</strong>
        </p>
      </header>

      <TotalsTable
        rows={totalRows(result)}
        coincidenceNotEstablished={coincidenceNotEstablished}
      />
      <LoadsTable rows={result.load_results} />

      <section aria-label="Declared assumptions">
        <h3>Declared assumptions</h3>
        {result.assumptions.length === 0 ? (
          <p data-no-rows="true">{NO_ROWS_TEXT}</p>
        ) : (
          <ul data-assumption-count={result.assumptions.length}>
            {result.assumptions.map((assumption) => (
              <li key={assumption}>{assumption}</li>
            ))}
          </ul>
        )}
      </section>

      <footer>
        <p>
          Calculation results are engineering design checks, not a statutory compliance
          declaration. Confirm the governing project basis, the connected load data and every
          diversity, utilization and coincidence factor before approval or issue.
        </p>
      </footer>
    </article>
  );
}

export default LoadResultPanel;
