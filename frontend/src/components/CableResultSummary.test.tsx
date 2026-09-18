// @vitest-environment jsdom
import { cleanup, render, screen } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import { afterEach, describe, expect, it } from "vitest";

import type { CableSizingResponse } from "../services/cable";
import { CableResultSummary } from "./CableResultSummary";

const base: CableSizingResponse = {
  study_code: "CBL-001",
  status: "REVIEW_REQUIRED",
  conductor: null,
  ampacity: null,
  voltage_drop: null,
  short_circuit: null,
  warnings: [
    { code: "DERATING_FACTOR_NOT_ESTABLISHED", message: "x", field_name: "depth_derating_factor" },
  ],
  standard_reference: "IEC 60364-5-52",
  ampacity_reference: "IEC 60287",
  reference_source: "PROFILE",
  jurisdiction_profile: "IN",
  reference_verification_status: "UNVERIFIED",
  notes: null,
} as unknown as CableSizingResponse;

function field(section: HTMLElement, name: string): Element | null {
  return section.querySelector(`[data-summary-field="${name}"]`);
}

describe("CableResultSummary", () => {
  afterEach(cleanup);

  it("shows the status label, study identity and em dashes for missing sections", () => {
    render(<CableResultSummary result={base} />);

    const section = screen.getByRole("region", { name: "Result summary" });
    expect(section).toHaveAttribute("data-summary-tone", "warning");
    expect(screen.getByText("Engineering review required")).toBeInTheDocument();
    expect(section.textContent).toContain("CBL-001");
    expect(field(section, "phase-conductor")?.textContent).toBe("—");
    expect(field(section, "phase-conductor")).not.toHaveAttribute("title");
    expect(field(section, "voltage-drop")?.textContent).toBe("—");
    expect(field(section, "voltage-drop")).not.toHaveAttribute("title");
    expect(section.querySelector("[data-summary-warnings]")?.textContent).toBe("1");
  });

  it("shows four significant figures and keeps the exact engine value in the tooltip (A12)", () => {
    const passed = {
      ...base,
      status: "DESIGN_CHECK_PASSED",
      warnings: [],
      conductor: { phase_area_mm2: "150" },
      ampacity: { utilization_ratio: "0.880512" },
      voltage_drop: { voltage_drop_percent: "2.058823", allowable_voltage_drop_percent: "5" },
    } as unknown as CableSizingResponse;
    render(<CableResultSummary result={passed} />);

    const section = screen.getByRole("region", { name: "Result summary" });
    expect(section).toHaveAttribute("data-summary-tone", "pass");

    expect(field(section, "phase-conductor")?.textContent).toBe("150 mm²");
    expect(field(section, "phase-conductor")).toHaveAttribute("title", "150 mm²");

    expect(field(section, "thermal-utilization")?.textContent).toBe("0.8805");
    expect(field(section, "thermal-utilization")).toHaveAttribute("title", "0.880512");

    expect(field(section, "voltage-drop")?.textContent).toBe("2.059 % of 5 %");
    expect(field(section, "voltage-drop")).toHaveAttribute("title", "2.058823 % of 5 %");

    expect(section.textContent).not.toContain("0.880512");
    expect(section.querySelector("[data-summary-warnings]")?.textContent).toBe("0");
  });
});
