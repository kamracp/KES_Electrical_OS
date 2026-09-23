// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";
import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import type { LoadGroupResponse } from "../services/loadDemand";
import { LoadResultPanel } from "./LoadResultPanel";

afterEach(() => {
  cleanup();
});

// The exact JSON the backend returns for study LOAD-001, taken from
// LoadGroupCalculationResponse at commit 2a25a8b.
const calculated: LoadGroupResponse = {
  group_code: "LOAD-001",
  group_name: "Process Pump Loads",
  coincidence_factor: "0.90",
  connected_power_kw: "32.6087",
  pre_coincidence_demand_kw: "23.4783",
  demand_power_kw: "21.1304",
  apparent_power_kva: "24.8593",
  reactive_power_kvar: "13.0955",
  load_results: [
    {
      load_code: "MTR-001",
      load_name: "Process Water Pump",
      scenario: "NORMAL",
      phase_system: "THREE_PHASE",
      connected_power_kw: "32.6087",
      utilized_power_kw: "26.0870",
      demand_power_kw: "23.4783",
      apparent_power_kva: "27.6215",
      reactive_power_kvar: "14.5505",
      design_current_a: "38.4272",
      status: "VALID",
      warnings: [],
    },
  ],
  status: "VALID",
  warnings: [],
  assumptions: ["The group coincidence factor is applied equally to active and reactive demand."],
  jurisdiction_profile: "IN",
};

function totalRow(key: string): HTMLElement {
  const row = document.querySelector<HTMLElement>(`[data-row-key="${key}"]`);
  if (row === null) {
    throw new Error(`No totals row ${key}`);
  }
  return row;
}

function totalValue(key: string): HTMLElement {
  return within(totalRow(key)).getAllByRole("cell")[0];
}

function loadCells(code: string): HTMLElement[] {
  const row = document.querySelector<HTMLElement>(`[data-load-code="${code}"]`);
  if (row === null) {
    throw new Error(`No load row ${code}`);
  }
  return within(row).getAllByRole("cell");
}

describe("LoadResultPanel", () => {
  it("names the study and its overall status", () => {
    render(<LoadResultPanel result={calculated} />);

    const panel = screen.getByRole("article", { name: "Load study result" });
    expect(within(panel).getByRole("heading", { level: 2 })).toHaveTextContent(
      "Load study result",
    );
    expect(document.querySelector("[data-study-code]")).toHaveTextContent("LOAD-001");
    expect(panel).toHaveTextContent("Process Pump Loads");
    expect(document.querySelector("[data-result-status]")).toHaveTextContent("Calculated");
  });

  it("shows the group totals to four significant figures with the exact value behind them", () => {
    render(<LoadResultPanel result={calculated} />);

    expect(totalValue("connected_power_kw")).toHaveTextContent("32.61");
    expect(totalValue("connected_power_kw")).toHaveAttribute("title", "32.6087");
    expect(totalValue("pre_coincidence_demand_kw")).toHaveTextContent("23.48");
    expect(totalValue("pre_coincidence_demand_kw")).toHaveAttribute("title", "23.4783");
    expect(totalValue("coincidence_factor")).toHaveTextContent("0.90");
    expect(totalValue("demand_power_kw")).toHaveTextContent("21.13");
    expect(totalValue("demand_power_kw")).toHaveAttribute("title", "21.1304");
    expect(totalValue("apparent_power_kva")).toHaveTextContent("24.86");
    expect(totalValue("apparent_power_kva")).toHaveAttribute("title", "24.8593");
    expect(totalValue("reactive_power_kvar")).toHaveTextContent("13.10");
    expect(totalValue("reactive_power_kvar")).toHaveAttribute("title", "13.0955");
  });

  it("puts the unit in the row label, not in the figure", () => {
    render(<LoadResultPanel result={calculated} />);

    expect(within(totalRow("demand_power_kw")).getByRole("rowheader")).toHaveTextContent(
      "Demand power (kW)",
    );
    expect(totalValue("demand_power_kw")).not.toHaveTextContent("kW");
  });

  it("shows every load with its design current and readable words", () => {
    render(<LoadResultPanel result={calculated} />);

    const cells = loadCells("MTR-001");
    expect(cells[0]).toHaveTextContent("Process Water Pump");
    expect(cells[1]).toHaveTextContent("Normal");
    expect(cells[2]).toHaveTextContent("Three-phase");
    expect(cells[3]).toHaveTextContent("32.61");
    expect(cells[4]).toHaveTextContent("26.09");
    expect(cells[4]).toHaveAttribute("title", "26.0870");
    expect(cells[5]).toHaveTextContent("23.48");
    expect(cells[6]).toHaveTextContent("27.62");
    expect(cells[7]).toHaveTextContent("14.55");
    // The design current is the figure a cable or a breaker is chosen against.
    expect(cells[8]).toHaveTextContent("38.43");
    expect(cells[8]).toHaveAttribute("title", "38.4272");
    expect(cells[9]).toHaveTextContent("Calculated");
  });

  it("keeps the wide load table inside a scroll container", () => {
    render(<LoadResultPanel result={calculated} />);

    const loads = screen.getByRole("region", { name: "Loads" });
    expect(loads.querySelector("[data-table-scroll] table")).not.toBeNull();
  });

  it("states the declared assumption of the aggregation", () => {
    render(<LoadResultPanel result={calculated} />);

    const assumptions = screen.getByRole("region", { name: "Declared assumptions" });
    expect(within(assumptions).getByRole("list")).toHaveAttribute("data-assumption-count", "1");
    expect(assumptions).toHaveTextContent(
      "The group coincidence factor is applied equally to active and reactive demand.",
    );
  });

  it("says when the coincidence factor was not established", () => {
    const reviewed: LoadGroupResponse = {
      ...calculated,
      coincidence_factor: "1",
      status: "REVIEW_REQUIRED",
      warnings: [
        { code: "COINCIDENCE_FACTOR_NOT_ESTABLISHED", message: "not established." },
      ],
    };
    render(<LoadResultPanel result={reviewed} />);

    expect(totalValue("coincidence_factor")).toHaveTextContent("1 (not established)");
    // The exact figure the engine used stays in the tooltip.
    expect(totalValue("coincidence_factor")).toHaveAttribute("title", "1");
    expect(document.querySelector("[data-result-status]")).toHaveTextContent(
      "Engineering review required",
    );
  });

  it("does not mark an established coincidence factor", () => {
    const warned: LoadGroupResponse = {
      ...calculated,
      status: "WARNING",
      warnings: [{ code: "ZERO_DEMAND", message: "MTR-001: demand is zero." }],
    };
    render(<LoadResultPanel result={warned} />);

    expect(totalValue("coincidence_factor")).not.toHaveTextContent("not established");
  });

  it("shows a DC load with its own words and no reactive power", () => {
    const withDc: LoadGroupResponse = {
      ...calculated,
      load_results: [
        {
          ...calculated.load_results[0],
          load_code: "DC-001",
          load_name: "DC Control Load",
          scenario: "UPS",
          phase_system: "DC",
          reactive_power_kvar: "0.0000",
          status: "REVIEW_REQUIRED",
          warnings: [
            { code: "UTILIZATION_FACTOR_NOT_ESTABLISHED", message: "not established." },
          ],
        },
      ],
    };
    render(<LoadResultPanel result={withDc} />);

    const cells = loadCells("DC-001");
    expect(cells[1]).toHaveTextContent("UPS");
    expect(cells[2]).toHaveTextContent("DC");
    expect(cells[7]).toHaveTextContent("0");
    expect(cells[9]).toHaveTextContent("Engineering review required");
  });
});
