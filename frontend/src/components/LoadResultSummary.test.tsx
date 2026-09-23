// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import type { LoadGroupResponse, LoadWarning } from "../services/loadDemand";
import { loadCalculationStatusSchema } from "../services/loadDemandContract";
import { LoadResultSummary, STATUS_LABELS, STATUS_TONE } from "./LoadResultSummary";

afterEach(() => {
  cleanup();
});

// The exact JSON the backend returns for study LOAD-001 (one motor, two units,
// coincidence 0.90), taken from LoadGroupCalculationResponse at commit 2a25a8b.
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

function warning(code: LoadWarning["code"]): LoadWarning {
  return { code, message: `${code} message.` };
}

function field(name: string): HTMLElement {
  const element = document.querySelector<HTMLElement>(`[data-summary-field="${name}"]`);
  if (element === null) {
    throw new Error(`No summary field ${name}`);
  }
  return element;
}

describe("LoadResultSummary", () => {
  it("shows the group figures to four significant figures with the exact value behind them", () => {
    render(<LoadResultSummary result={calculated} />);

    // A12: rounded on screen, the engine's own decimal in the tooltip.
    expect(field("demand-power")).toHaveTextContent("21.13 kW");
    expect(field("demand-power")).toHaveAttribute("title", "21.1304 kW");
    expect(field("apparent-power")).toHaveTextContent("24.86 kVA");
    expect(field("apparent-power")).toHaveAttribute("title", "24.8593 kVA");
    expect(field("reactive-power")).toHaveTextContent("13.10 kvar");
    expect(field("reactive-power")).toHaveAttribute("title", "13.0955 kvar");
    expect(field("connected-power")).toHaveTextContent("32.61 kW");
    expect(field("connected-power")).toHaveAttribute("title", "32.6087 kW");
    expect(field("pre-coincidence-demand")).toHaveTextContent("23.48 kW");
    expect(field("pre-coincidence-demand")).toHaveAttribute("title", "23.4783 kW");
    expect(field("coincidence-factor")).toHaveTextContent("0.90");
    expect(field("loads")).toHaveTextContent("1");
  });

  it("names the study, the group and the profile", () => {
    render(<LoadResultSummary result={calculated} />);

    const summary = screen.getByRole("region", { name: "Result summary" });
    expect(summary).toHaveTextContent("LOAD-001");
    expect(summary).toHaveTextContent("Process Pump Loads");
    expect(summary).toHaveTextContent("IN profile");
  });

  it("reads as calculated and clean when every factor is established", () => {
    render(<LoadResultSummary result={calculated} />);

    const summary = screen.getByRole("region", { name: "Result summary" });
    expect(summary).toHaveAttribute("data-summary-tone", "pass");
    expect(summary.querySelector("[data-summary-status]")).toHaveTextContent("Calculated");
    expect(summary.querySelector("[data-summary-warnings]")).toHaveAttribute(
      "data-summary-warnings",
      "0",
    );
    expect(document.querySelector('[data-summary-field="not-established"]')).toBeNull();
  });

  it("says the coincidence factor was not established and counts the open factors", () => {
    const reviewed: LoadGroupResponse = {
      ...calculated,
      coincidence_factor: "1",
      status: "REVIEW_REQUIRED",
      // The group's own factor, and a member's factor repeated at group level
      // under the same code: both are factors the engineer still owes.
      warnings: [
        warning("COINCIDENCE_FACTOR_NOT_ESTABLISHED"),
        warning("UTILIZATION_FACTOR_NOT_ESTABLISHED"),
      ],
    };
    render(<LoadResultSummary result={reviewed} />);

    const summary = screen.getByRole("region", { name: "Result summary" });
    // Same words and the same colour as a cable review: work still to do,
    // not a design failure.
    expect(summary).toHaveAttribute("data-summary-tone", "warning");
    expect(summary.querySelector("[data-summary-status]")).toHaveTextContent(
      "Engineering review required",
    );
    // The figure used is shown, and said to be an assumption in the same breath.
    expect(field("coincidence-factor")).toHaveTextContent("1 (not established)");
    expect(field("coincidence-factor")).toHaveAttribute("title", "1");
    expect(field("not-established")).toHaveTextContent("2");
    expect(summary.querySelector("[data-summary-warnings]")).toHaveAttribute(
      "data-summary-warnings",
      "2",
    );
  });

  it("counts a member's factor once, from the group list that already repeats it", () => {
    const memberOnly: LoadGroupResponse = {
      ...calculated,
      status: "REVIEW_REQUIRED",
      // Coincidence was given; one load left its utilization factor blank. The
      // engine reports that load's warning on the load AND, prefixed with the
      // load code, on the group.
      warnings: [
        {
          code: "UTILIZATION_FACTOR_NOT_ESTABLISHED",
          message: "MTR-001: Utilization factor is not established; the calculation used 1.",
        },
      ],
      load_results: [
        {
          ...calculated.load_results[0],
          status: "REVIEW_REQUIRED",
          warnings: [warning("UTILIZATION_FACTOR_NOT_ESTABLISHED")],
        },
      ],
    };
    render(<LoadResultSummary result={memberOnly} />);

    expect(field("not-established")).toHaveTextContent("1");
    expect(field("coincidence-factor")).toHaveTextContent("0.90");
    expect(field("coincidence-factor")).not.toHaveTextContent("not established");
  });

  it("counts only the unestablished factors, not every warning", () => {
    const zeroDemand: LoadGroupResponse = {
      ...calculated,
      status: "WARNING",
      warnings: [warning("ZERO_DEMAND")],
    };
    render(<LoadResultSummary result={zeroDemand} />);

    const summary = screen.getByRole("region", { name: "Result summary" });
    expect(summary).toHaveAttribute("data-summary-tone", "warning");
    expect(summary.querySelector("[data-summary-status]")).toHaveTextContent(
      "Calculated with warnings",
    );
    expect(document.querySelector('[data-summary-field="not-established"]')).toBeNull();
    expect(field("coincidence-factor")).toHaveTextContent("0.90");
    expect(field("coincidence-factor")).not.toHaveTextContent("not established");
  });

  it("counts every load of the schedule", () => {
    const twoLoads: LoadGroupResponse = {
      ...calculated,
      load_results: [
        calculated.load_results[0],
        { ...calculated.load_results[0], load_code: "DC-001", phase_system: "DC" },
      ],
    };
    render(<LoadResultSummary result={twoLoads} />);

    expect(field("loads")).toHaveTextContent("2");
  });
});

describe("the LoadResultSummary status maps", () => {
  it("give every calculation status a label and a tone", () => {
    // Drift guard: a status the backend adds must get words and a colour here.
    expect(Object.keys(STATUS_LABELS).sort()).toEqual(
      [...loadCalculationStatusSchema.options].sort(),
    );
    expect(Object.keys(STATUS_TONE).sort()).toEqual(
      [...loadCalculationStatusSchema.options].sort(),
    );
    expect(STATUS_TONE.REVIEW_REQUIRED).toBe("warning");
    expect(STATUS_LABELS.REVIEW_REQUIRED).toBe("Engineering review required");
  });
});
