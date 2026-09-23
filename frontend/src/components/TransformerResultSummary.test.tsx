// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import type {
  TransformerSizingResponse,
  TransformerSizingWarning,
} from "../services/transformerSizing";
import {
  transformerRedundancyModeSchema,
  transformerSizingStatusSchema,
} from "../services/transformerSizingContract";
import {
  REDUNDANCY_LABELS,
  STATUS_LABELS,
  STATUS_TONE,
  TransformerResultSummary,
} from "./TransformerResultSummary";

afterEach(() => {
  cleanup();
});

// The exact JSON the backend returns for study TR-001 (800 kW at 0.80, margin
// 1.10, schedule 1000 / 1250 / 1600), taken from TransformerSizingResponse at
// commit 7853d51.
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

function warning(code: TransformerSizingWarning["code"]): TransformerSizingWarning {
  return { code, message: `${code} message.` };
}

function field(name: string): HTMLElement {
  const element = document.querySelector<HTMLElement>(`[data-summary-field="${name}"]`);
  if (element === null) {
    throw new Error(`No summary field ${name}`);
  }
  return element;
}

describe("TransformerResultSummary", () => {
  it("shows the computed figures to four significant figures with the exact value behind", () => {
    render(<TransformerResultSummary result={calculated} />);

    expect(field("required-rating")).toHaveTextContent("1100 kVA");
    expect(field("required-rating")).toHaveAttribute("title", "1100.0000 kVA");
    expect(field("design-required")).toHaveTextContent("1100 kVA");
    expect(field("installed")).toHaveTextContent("1250 kVA");
    expect(field("installed")).toHaveAttribute("title", "1250.0000 kVA");
    // Four significant figures of "150.0000" is "150.0", not "150".
    expect(field("spare")).toHaveTextContent("150.0 kVA");
    expect(field("spare")).toHaveAttribute("title", "150.0000 kVA");
    expect(field("loading")).toHaveTextContent("88.00 %");
    expect(field("loading")).toHaveAttribute("title", "88.0000 %");
  });

  it("shows the selected rating exactly as the schedule gave it", () => {
    render(<TransformerResultSummary result={calculated} />);

    // A catalogue value, not a calculated one: no rounding and no tooltip, so
    // the engineer reads back the rating that is actually orderable.
    expect(field("selected-rating")).toHaveTextContent("1250 kVA");
    expect(field("selected-rating")).not.toHaveAttribute("title");
  });

  it("shows the unit counts as the integers they are", () => {
    render(<TransformerResultSummary result={calculated} />);

    expect(field("units")).toHaveTextContent("1 duty + 0 standby");
    expect(field("units")).toHaveTextContent("no redundancy");
  });

  it("names the study, the transformer and the profile", () => {
    render(<TransformerResultSummary result={calculated} />);

    const summary = screen.getByRole("region", { name: "Result summary" });
    expect(summary).toHaveTextContent("TR-001");
    expect(summary).toHaveTextContent("Main Transformer");
    expect(summary).toHaveTextContent("IN profile");
  });

  it("reads as calculated and clean when every factor is established", () => {
    render(<TransformerResultSummary result={calculated} />);

    const summary = screen.getByRole("region", { name: "Result summary" });
    expect(summary).toHaveAttribute("data-summary-tone", "pass");
    expect(summary.querySelector("[data-summary-status]")).toHaveTextContent("Calculated");
    expect(summary.querySelector("[data-summary-warnings]")).toHaveAttribute(
      "data-summary-warnings",
      "0",
    );
    expect(document.querySelector('[data-summary-field="not-established"]')).toBeNull();
    expect(document.querySelector("[data-no-rating]")).toBeNull();
  });

  it("counts the open factors when a margin was not established", () => {
    const reviewed: TransformerSizingResponse = {
      ...calculated,
      design_margin_factor: "1",
      design_required_kva: "1000.0000",
      required_unit_rating_kva: "1000.0000",
      status: "REVIEW_REQUIRED",
      warnings: [warning("DESIGN_MARGIN_NOT_ESTABLISHED")],
    };
    render(<TransformerResultSummary result={reviewed} />);

    const summary = screen.getByRole("region", { name: "Result summary" });
    expect(summary).toHaveAttribute("data-summary-tone", "warning");
    expect(summary.querySelector("[data-summary-status]")).toHaveTextContent(
      "Engineering review required",
    );
    expect(field("not-established")).toHaveTextContent("1");
    expect(field("design-required")).toHaveTextContent("1000 kVA");
  });

  it("counts only the unestablished factors, not every warning", () => {
    const warned: TransformerSizingResponse = {
      ...calculated,
      status: "WARNING",
      warnings: [warning("DERATING_APPLIED")],
    };
    render(<TransformerResultSummary result={warned} />);

    const summary = screen.getByRole("region", { name: "Result summary" });
    expect(summary).toHaveAttribute("data-summary-tone", "warning");
    expect(summary.querySelector("[data-summary-status]")).toHaveTextContent(
      "Calculated with warnings",
    );
    expect(document.querySelector('[data-summary-field="not-established"]')).toBeNull();
  });

  it("says plainly when no rating in the schedule is big enough", () => {
    const noSolution: TransformerSizingResponse = {
      ...calculated,
      selected_unit_rating_kva: null,
      installed_nameplate_capacity_kva: null,
      derated_duty_capacity_kva: null,
      spare_derated_capacity_kva: null,
      loading_percent: null,
      status: "NO_SOLUTION",
      warnings: [warning("NO_STANDARD_RATING_AVAILABLE")],
    };
    render(<TransformerResultSummary result={noSolution} />);

    const summary = screen.getByRole("region", { name: "Result summary" });
    expect(summary).toHaveAttribute("data-summary-tone", "fail");
    expect(summary.querySelector("[data-summary-status]")).toHaveTextContent(
      "No standard rating fits",
    );
    expect(document.querySelector("[data-no-rating]")).toHaveTextContent(
      "No rating in the schedule covers 1100 kVA.",
    );
    // The five fields that come with a selected rating are all empty together.
    for (const name of ["selected-rating", "installed", "spare", "loading"]) {
      expect(field(name)).toHaveTextContent("—");
    }
    // What the design needed is still shown: it is what a bigger schedule must beat.
    expect(field("required-rating")).toHaveTextContent("1100 kVA");
  });

  it("names the redundancy arrangement of a standby unit", () => {
    const redundant: TransformerSizingResponse = {
      ...calculated,
      redundancy_mode: "N_PLUS_1",
      duty_units: 2,
      standby_units: 1,
      total_units: 3,
    };
    render(<TransformerResultSummary result={redundant} />);

    expect(field("units")).toHaveTextContent("2 duty + 1 standby");
    expect(field("units")).toHaveTextContent("N+1");
  });
});

describe("the TransformerResultSummary maps", () => {
  it("give every status a label and a tone, and every redundancy mode a name", () => {
    // Drift guard: a value the backend adds must get words and a colour here.
    expect(Object.keys(STATUS_LABELS).sort()).toEqual(
      [...transformerSizingStatusSchema.options].sort(),
    );
    expect(Object.keys(STATUS_TONE).sort()).toEqual(
      [...transformerSizingStatusSchema.options].sort(),
    );
    expect(Object.keys(REDUNDANCY_LABELS).sort()).toEqual(
      [...transformerRedundancyModeSchema.options].sort(),
    );
    expect(STATUS_TONE.REVIEW_REQUIRED).toBe("warning");
    expect(STATUS_TONE.NO_SOLUTION).toBe("fail");
  });
});
