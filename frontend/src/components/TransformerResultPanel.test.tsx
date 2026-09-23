// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";
import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import type { TransformerSizingResponse } from "../services/transformerSizing";
import { TransformerResultPanel } from "./TransformerResultPanel";

afterEach(() => {
  cleanup();
});

// The exact JSON the backend returns for study TR-001, taken from
// TransformerSizingResponse at commit 7853d51.
const calculated: TransformerSizingResponse = {
  code: "TR-001",
  name: "Main Transformer",
  scenario: "NORMAL",
  redundancy_mode: "NONE",
  demand_power_kw: "800",
  demand_power_factor: "0.80",
  base_demand_kva: "1000.0000",
  future_growth_factor: "1",
  future_demand_kva: "1000.0000",
  design_margin_factor: "1.10",
  design_required_kva: "1100.0000",
  combined_derating_factor: "1.0000",
  required_nameplate_capacity_kva: "1100.0000",
  duty_units: 1,
  standby_units: 0,
  total_units: 1,
  required_unit_rating_kva: "1100.0000",
  selected_unit_rating_kva: "1250",
  installed_nameplate_capacity_kva: "1250.0000",
  derated_duty_capacity_kva: "1250.0000",
  spare_derated_capacity_kva: "150.0000",
  loading_percent: "88.0000",
  status: "VALID",
  warnings: [],
  jurisdiction_profile: "IN",
};

function row(key: string): HTMLElement {
  const element = document.querySelector<HTMLElement>(`[data-row-key="${key}"]`);
  if (element === null) {
    throw new Error(`No row ${key}`);
  }
  return element;
}

function value(key: string): HTMLElement {
  return within(row(key)).getAllByRole("cell")[0];
}

describe("TransformerResultPanel", () => {
  it("names the study and its overall status", () => {
    render(<TransformerResultPanel result={calculated} />);

    const panel = screen.getByRole("article", { name: "Transformer sizing result" });
    expect(within(panel).getByRole("heading", { level: 2 })).toHaveTextContent(
      "Transformer sizing result",
    );
    expect(document.querySelector("[data-study-code]")).toHaveTextContent("TR-001");
    expect(panel).toHaveTextContent("Main Transformer");
    expect(document.querySelector("[data-result-status]")).toHaveTextContent("Calculated");
  });

  it("walks from demand to the required nameplate capacity", () => {
    render(<TransformerResultPanel result={calculated} />);

    expect(value("demand_power_kw")).toHaveTextContent("800");
    expect(value("demand_power_factor")).toHaveTextContent("0.80");
    expect(value("base_demand_kva")).toHaveTextContent("1000");
    expect(value("base_demand_kva")).toHaveAttribute("title", "1000.0000");
    expect(value("future_growth_factor")).toHaveTextContent("1");
    expect(value("future_demand_kva")).toHaveTextContent("1000");
    expect(value("design_margin_factor")).toHaveTextContent("1.10");
    expect(value("design_required_kva")).toHaveTextContent("1100");
    expect(value("design_required_kva")).toHaveAttribute("title", "1100.0000");
    expect(value("combined_derating_factor")).toHaveTextContent("1.000");
    expect(value("required_nameplate_capacity_kva")).toHaveTextContent("1100");
  });

  it("puts the unit in the row label, not in the figure", () => {
    render(<TransformerResultPanel result={calculated} />);

    expect(within(row("design_required_kva")).getByRole("rowheader")).toHaveTextContent(
      "Design required (kVA)",
    );
    expect(value("design_required_kva")).not.toHaveTextContent("kVA");
  });

  it("shows the selection with the counts as integers", () => {
    render(<TransformerResultPanel result={calculated} />);

    expect(value("required_unit_rating_kva")).toHaveTextContent("1100");
    // A catalogue value: shown as sent, with no rounding and no tooltip.
    expect(value("selected_unit_rating_kva")).toHaveTextContent("1250");
    expect(value("selected_unit_rating_kva")).not.toHaveAttribute("title");
    expect(value("duty_units")).toHaveTextContent("1");
    expect(value("standby_units")).toHaveTextContent("0");
    expect(value("total_units")).toHaveTextContent("1");
    expect(value("redundancy_mode")).toHaveTextContent("no redundancy");
    expect(value("installed_nameplate_capacity_kva")).toHaveTextContent("1250");
    expect(value("derated_duty_capacity_kva")).toHaveTextContent("1250");
    expect(value("spare_derated_capacity_kva")).toHaveTextContent("150.0");
    expect(value("loading_percent")).toHaveTextContent("88.00");
    expect(value("loading_percent")).toHaveAttribute("title", "88.0000");
  });

  it("keeps every table in its own scroll container", () => {
    render(<TransformerResultPanel result={calculated} />);

    const tables = document.querySelectorAll("table");
    expect(tables.length).toBe(2);
    for (const table of tables) {
      expect(table.closest("[data-table-scroll]")).not.toBeNull();
    }
  });

  it("says when a factor was not established", () => {
    const reviewed: TransformerSizingResponse = {
      ...calculated,
      design_margin_factor: "1",
      design_required_kva: "1000.0000",
      status: "REVIEW_REQUIRED",
      warnings: [
        { code: "DESIGN_MARGIN_NOT_ESTABLISHED", message: "not established." },
      ],
    };
    render(<TransformerResultPanel result={reviewed} />);

    expect(value("design_margin_factor")).toHaveTextContent("1 (not established)");
    // The exact figure the engine used stays in the tooltip.
    expect(value("design_margin_factor")).toHaveAttribute("title", "1");
    // A factor with no such warning is not marked.
    expect(value("future_growth_factor")).not.toHaveTextContent("not established");
    expect(document.querySelector("[data-result-status]")).toHaveTextContent(
      "Engineering review required",
    );
  });

  it("marks every factor whose warning the engine raised", () => {
    const reviewed: TransformerSizingResponse = {
      ...calculated,
      future_growth_factor: "1",
      status: "REVIEW_REQUIRED",
      warnings: [
        { code: "GROWTH_FACTOR_NOT_ESTABLISHED", message: "not established." },
        { code: "DESIGN_MARGIN_NOT_ESTABLISHED", message: "not established." },
      ],
    };
    render(<TransformerResultPanel result={reviewed} />);

    expect(value("future_growth_factor")).toHaveTextContent("not established");
    expect(value("design_margin_factor")).toHaveTextContent("not established");
  });

  it("marks the combined derating factor when one of its three was assumed", () => {
    const reviewed: TransformerSizingResponse = {
      ...calculated,
      status: "REVIEW_REQUIRED",
      warnings: [
        { code: "AMBIENT_DERATING_NOT_ESTABLISHED", message: "not established." },
      ],
    };
    render(<TransformerResultPanel result={reviewed} />);

    // The combined factor is the product of ambient, altitude and harmonic, so
    // one assumed factor makes the product an assumption too.
    expect(value("combined_derating_factor")).toHaveTextContent(
      "1.000 (includes a not-established factor)",
    );
    expect(value("combined_derating_factor")).toHaveAttribute("title", "1.0000");
  });

  it("leaves the combined derating factor unmarked when all three are given", () => {
    const warned: TransformerSizingResponse = {
      ...calculated,
      status: "WARNING",
      warnings: [{ code: "DERATING_APPLIED", message: "Derating factors were applied." }],
    };
    render(<TransformerResultPanel result={warned} />);

    expect(value("combined_derating_factor")).toHaveTextContent("1.000");
    expect(value("combined_derating_factor")).not.toHaveTextContent("not-established");
  });

  it("leaves the selection rows empty when no rating fits", () => {
    const noSolution: TransformerSizingResponse = {
      ...calculated,
      selected_unit_rating_kva: null,
      installed_nameplate_capacity_kva: null,
      derated_duty_capacity_kva: null,
      spare_derated_capacity_kva: null,
      loading_percent: null,
      status: "NO_SOLUTION",
      warnings: [
        { code: "NO_STANDARD_RATING_AVAILABLE", message: "No rating satisfies it." },
      ],
    };
    render(<TransformerResultPanel result={noSolution} />);

    for (const key of [
      "selected_unit_rating_kva",
      "installed_nameplate_capacity_kva",
      "derated_duty_capacity_kva",
      "spare_derated_capacity_kva",
      "loading_percent",
    ]) {
      expect(value(key)).toHaveTextContent("—");
    }
    // What the design needed is still shown: a bigger schedule must beat it.
    expect(value("required_unit_rating_kva")).toHaveTextContent("1100");
    expect(document.querySelector("[data-result-status]")).toHaveTextContent(
      "No standard rating fits",
    );
  });

  it("records the profile the study was designed under", () => {
    render(<TransformerResultPanel result={calculated} />);

    const profile = screen.getByRole("region", { name: "Jurisdiction profile" });
    expect(profile.querySelector("[data-jurisdiction-profile]")).toHaveAttribute(
      "data-jurisdiction-profile",
      "IN",
    );
    expect(profile).toHaveTextContent("no profile-dependent value");
  });
});
