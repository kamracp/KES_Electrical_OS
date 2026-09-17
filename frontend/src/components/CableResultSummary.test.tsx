// @vitest-environment jsdom
import { cleanup, render, screen } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import "@testing-library/jest-dom/vitest";
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

describe("CableResultSummary", () => {
  afterEach(cleanup);

  it("shows the status label, study identity and em dashes for missing sections", () => {
    render(<CableResultSummary result={base} />);

    const section = screen.getByRole("region", { name: "Result summary" });
    expect(section).toHaveAttribute("data-summary-tone", "warning");
    expect(screen.getByText("Engineering review required")).toBeInTheDocument();
    expect(section.textContent).toContain("CBL-001");
    expect(section.querySelectorAll("dd")[0]?.textContent).toBe("—");
    expect(section.querySelector("[data-summary-warnings]")?.textContent).toBe("1");
  });

  it("renders decisive values verbatim from the engine", () => {
    const passed = {
      ...base,
      status: "DESIGN_CHECK_PASSED",
      warnings: [],
      conductor: { phase_area_mm2: "150" },
      ampacity: { utilization_ratio: "0.8804" },
      voltage_drop: { voltage_drop_percent: "2.0588", allowable_voltage_drop_percent: "5" },
    } as unknown as CableSizingResponse;
    render(<CableResultSummary result={passed} />);

    const section = screen.getByRole("region", { name: "Result summary" });
    expect(section).toHaveAttribute("data-summary-tone", "pass");
    expect(section.textContent).toContain("150 mm²");
    expect(section.textContent).toContain("0.8804");
    expect(section.textContent).toContain("2.0588 % of 5 %");
    expect(section.querySelector("[data-summary-warnings]")?.textContent).toBe("0");
  });
});
