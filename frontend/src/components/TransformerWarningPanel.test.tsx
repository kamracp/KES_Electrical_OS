// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";
import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import type { TransformerSizingWarning } from "../services/transformerSizing";
import { transformerSizingWarningCodeSchema } from "../services/transformerSizingContract";
import { TransformerWarningPanel, WARNING_CODE_LABELS } from "./TransformerWarningPanel";

afterEach(() => {
  cleanup();
});

describe("TransformerWarningPanel", () => {
  it("says so plainly when the engine raised nothing", () => {
    render(<TransformerWarningPanel warnings={[]} />);

    expect(screen.getByRole("region", { name: "Engineering warnings" })).toBeInTheDocument();
    expect(document.querySelector("[data-no-warnings]")).toHaveTextContent(
      "No engineering warnings raised.",
    );
    expect(screen.queryByRole("list")).not.toBeInTheDocument();
  });

  it("names the factor and keeps the engine's own sentence", () => {
    const warnings: TransformerSizingWarning[] = [
      {
        code: "DESIGN_MARGIN_NOT_ESTABLISHED",
        message:
          "Design margin factor is not established; the calculation used 1. " +
          "The engineer must establish this factor.",
      },
    ];
    render(<TransformerWarningPanel warnings={warnings} />);

    const item = document.querySelector('[data-warning-code="DESIGN_MARGIN_NOT_ESTABLISHED"]');
    expect(item).toHaveTextContent("Design margin factor not established");
    expect(item).toHaveTextContent("the calculation used 1");
    expect(screen.getByRole("list")).toHaveAttribute("data-warning-count", "1");
  });

  it("shows several warnings in the order the engine raised them", () => {
    const warnings: TransformerSizingWarning[] = [
      { code: "GROWTH_FACTOR_NOT_ESTABLISHED", message: "Growth not established." },
      { code: "DERATING_APPLIED", message: "Derating factors were applied." },
      { code: "NO_STANDARD_RATING_AVAILABLE", message: "No rating satisfies the requirement." },
    ];
    render(<TransformerWarningPanel warnings={warnings} />);

    const items = within(screen.getByRole("list")).getAllByRole("listitem");
    expect(items[0]).toHaveTextContent("Future growth factor not established");
    expect(items[1]).toHaveTextContent("Derating applied");
    expect(items[2]).toHaveTextContent("No standard rating available");
    expect(screen.getByRole("list")).toHaveAttribute("data-warning-count", "3");
  });
});

describe("the TransformerWarningPanel label map", () => {
  it("names every warning code the contract can carry", () => {
    // Drift guard: a code the backend adds must get words here.
    expect(Object.keys(WARNING_CODE_LABELS).sort()).toEqual(
      [...transformerSizingWarningCodeSchema.options].sort(),
    );
  });
});
