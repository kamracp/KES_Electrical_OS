// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";
import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import type { LoadWarning } from "../services/loadDemand";
import { loadWarningCodeSchema } from "../services/loadDemandContract";
import { LoadWarningPanel, WARNING_CODE_LABELS } from "./LoadWarningPanel";

afterEach(() => {
  cleanup();
});

describe("LoadWarningPanel", () => {
  it("says so plainly when the engine raised nothing", () => {
    render(<LoadWarningPanel warnings={[]} />);

    expect(screen.getByRole("region", { name: "Engineering warnings" })).toBeInTheDocument();
    expect(document.querySelector("[data-no-warnings]")).toHaveTextContent(
      "No engineering warnings raised.",
    );
    expect(screen.queryByRole("list")).not.toBeInTheDocument();
  });

  it("names the factor and keeps the engine's own sentence", () => {
    const warnings: LoadWarning[] = [
      {
        code: "COINCIDENCE_FACTOR_NOT_ESTABLISHED",
        message:
          "Group coincidence factor is not established; the calculation used 1. " +
          "The engineer must establish this factor.",
      },
    ];
    render(<LoadWarningPanel warnings={warnings} />);

    const item = document.querySelector(
      '[data-warning-code="COINCIDENCE_FACTOR_NOT_ESTABLISHED"]',
    );
    expect(item).toHaveTextContent("Coincidence factor not established");
    expect(item).toHaveTextContent("the calculation used 1");
    expect(screen.getByRole("list")).toHaveAttribute("data-warning-count", "1");
  });

  it("keeps the load code a member warning was raised under", () => {
    const warnings: LoadWarning[] = [
      {
        code: "UTILIZATION_FACTOR_NOT_ESTABLISHED",
        message: "MTR-001: Utilization factor is not established; the calculation used 1.",
      },
      { code: "ZERO_DEMAND", message: "MTR-002: Calculated demand is zero." },
    ];
    render(<LoadWarningPanel warnings={warnings} />);

    // The engine prefixes a member's warning with its load code; the panel must
    // not strip it, or the reader cannot tell which load is meant.
    const items = within(screen.getByRole("list")).getAllByRole("listitem");
    expect(items[0]).toHaveTextContent("MTR-001:");
    expect(items[1]).toHaveTextContent("MTR-002:");
    expect(items[1]).toHaveTextContent("Zero demand");
    expect(screen.getByRole("list")).toHaveAttribute("data-warning-count", "2");
  });

  it("shows the same code twice when two loads raise it", () => {
    const warnings: LoadWarning[] = [
      { code: "DEMAND_FACTOR_NOT_ESTABLISHED", message: "MTR-001: not established." },
      { code: "DEMAND_FACTOR_NOT_ESTABLISHED", message: "MTR-002: not established." },
    ];
    render(<LoadWarningPanel warnings={warnings} />);

    expect(
      document.querySelectorAll('[data-warning-code="DEMAND_FACTOR_NOT_ESTABLISHED"]'),
    ).toHaveLength(2);
  });
});

describe("the LoadWarningPanel label map", () => {
  it("names every warning code the contract can carry", () => {
    // Drift guard: a code the backend adds must get words here.
    expect(Object.keys(WARNING_CODE_LABELS).sort()).toEqual(
      [...loadWarningCodeSchema.options].sort(),
    );
  });
});
