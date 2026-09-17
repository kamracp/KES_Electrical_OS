// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";
import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import type { ShortCircuitStudyResponse } from "../services/fault";
import { FaultWarningPanel } from "./FaultWarningPanel";

type FaultEngineeringWarning = ShortCircuitStudyResponse["warnings"][number];

afterEach(() => {
  cleanup();
});

const warnings: FaultEngineeringWarning[] = [
  {
    code: "ZERO_SEQUENCE_PATH_BLOCKED",
    severity: "ERROR",
    message: "No zero-sequence path exists to the fault bus.",
    reference_code: "BR-02",
  },
  {
    code: "PEAK_CURRENT_NOT_EVALUATED",
    severity: "WARNING",
    message: "X/R ratio unavailable; peak current not evaluated.",
    reference_code: null,
  },
];

describe("FaultWarningPanel", () => {
  it("renders the empty state when there are no warnings", () => {
    render(<FaultWarningPanel warnings={[]} />);

    const section = screen.getByRole("region", { name: "Engineering warnings" });
    expect(within(section).getByText("No engineering warnings raised.")).toHaveAttribute(
      "data-no-warnings",
      "true",
    );
    expect(within(section).queryByRole("list")).toBeNull();
  });

  it("renders one item per warning with severity, label, message and reference", () => {
    render(<FaultWarningPanel warnings={warnings} />);

    const list = screen.getByRole("list");
    expect(list).toHaveAttribute("data-warning-count", "2");
    const items = within(list).getAllByRole("listitem");
    expect(items).toHaveLength(2);

    expect(items[0]).toHaveAttribute("data-warning-code", "ZERO_SEQUENCE_PATH_BLOCKED");
    expect(items[0]).toHaveAttribute("data-warning-severity", "ERROR");
    expect(items[0]?.textContent).toContain("Error - Zero-sequence path blocked");
    expect(items[0]?.textContent).toContain("No zero-sequence path exists to the fault bus.");
    expect(within(items[0] as HTMLElement).getByText("BR-02")).toBeInTheDocument();

    expect(items[1]).toHaveAttribute("data-warning-severity", "WARNING");
    expect(items[1]?.textContent).toContain("Warning - Peak current not evaluated");
    expect(items[1]?.querySelector("[data-warning-reference]")).toBeNull();
  });
});
