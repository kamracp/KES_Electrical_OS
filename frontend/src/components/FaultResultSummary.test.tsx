// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";
import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import type { ShortCircuitStudyResponse } from "../services/fault";
import { FaultResultSummary } from "./FaultResultSummary";

// The currents and X/R carry more than four significant figures to prove
// display rule A12: rounded on screen, exact in the tooltip.
const calculated: ShortCircuitStudyResponse = {
  study_code: "SC-MSB-01",
  study_name: "Main switchboard three-phase fault",
  calculation_case: "MAXIMUM",
  fault_bus_code: "MSB-01",
  fault_type: "THREE_PHASE",
  nominal_voltage_v: "415",
  frequency_hz: "50",
  status: "CALCULATED",
  initial_symmetrical_short_circuit_current_ka: "35.219668322",
  peak_short_circuit_current_ka: "84.583705423",
  symmetrical_breaking_current_ka: null,
  steady_state_short_circuit_current_ka: null,
  thermal_equivalent_short_circuit_current_ka: null,
  earth_fault_current_ka: null,
  kappa_factor: "1.698",
  x_r_ratio: "8.149425287",
  clearing_time_s: null,
  sequence_results: [],
  source_contributions: [],
  warnings: [],
  standard_reference: "IEC 60909-0",
  earth_current_reference: "IEC 60909-3",
  reference_source: "PROFILE",
  jurisdiction_profile: "IN",
  reference_verification_status: "UNVERIFIED",
  operating_state_code: null,
  notes: null,
};

function field(region: HTMLElement, name: string): Element | null {
  return region.querySelector(`[data-summary-field="${name}"]`);
}

afterEach(() => {
  cleanup();
});

describe("FaultResultSummary", () => {
  it("shows the study state, identity and the decisive currents with four figures (A12)", () => {
    render(<FaultResultSummary result={calculated} />);

    const region = screen.getByRole("region", { name: "Result summary" });
    expect(region).toHaveAttribute("data-summary-tone", "pass");
    expect(within(region).getByText("Study calculated")).toHaveAttribute(
      "data-summary-status",
      "CALCULATED",
    );
    expect(region).toHaveTextContent("SC-MSB-01");
    expect(region).toHaveTextContent("three phase fault at MSB-01");
    expect(region).toHaveTextContent("maximum case");
    expect(region).toHaveTextContent("references unverified");

    expect(field(region, "initial-current")?.textContent).toBe("35.22 kA");
    expect(field(region, "initial-current")).toHaveAttribute("title", "35.219668322 kA");
    expect(field(region, "peak-current")?.textContent).toBe("84.58 kA");
    expect(field(region, "peak-current")).toHaveAttribute("title", "84.583705423 kA");
    expect(field(region, "x-r-ratio")?.textContent).toBe("8.149");
    expect(field(region, "x-r-ratio")).toHaveAttribute("title", "8.149425287");
    expect(region.textContent).not.toContain("35.219668322");

    expect(field(region, "earth-fault-current")).toBeNull();
    expect(region.querySelector("[data-summary-warnings]")).toHaveAttribute(
      "data-summary-warnings",
      "0",
    );
  });

  it("uses the warning tone, counts warnings and shows an earth-fault current when given", () => {
    const withWarnings: ShortCircuitStudyResponse = {
      ...calculated,
      status: "WARNING",
      fault_type: "SINGLE_PHASE_TO_EARTH" as ShortCircuitStudyResponse["fault_type"],
      peak_short_circuit_current_ka: null,
      x_r_ratio: null,
      earth_fault_current_ka: "32.915",
      warnings: [{}, {}] as unknown as ShortCircuitStudyResponse["warnings"],
    };
    render(<FaultResultSummary result={withWarnings} />);

    const region = screen.getByRole("region", { name: "Result summary" });
    expect(region).toHaveAttribute("data-summary-tone", "warning");
    expect(within(region).getByText("Calculated with warnings")).toBeInTheDocument();

    expect(field(region, "peak-current")?.textContent).toBe("—");
    expect(field(region, "peak-current")).not.toHaveAttribute("title");
    expect(field(region, "x-r-ratio")?.textContent).toBe("—");
    expect(field(region, "x-r-ratio")).not.toHaveAttribute("title");

    // Half-up on the fifth figure: 32.915 -> 32.92.
    expect(field(region, "earth-fault-current")?.textContent).toBe("32.92 kA");
    expect(field(region, "earth-fault-current")).toHaveAttribute("title", "32.915 kA");

    expect(region.querySelector("[data-summary-warnings]")).toHaveAttribute(
      "data-summary-warnings",
      "2",
    );
  });

  it("uses the fail tone for an indeterminate result", () => {
    render(<FaultResultSummary result={{ ...calculated, status: "INDETERMINATE" }} />);

    const region = screen.getByRole("region", { name: "Result summary" });
    expect(region).toHaveAttribute("data-summary-tone", "fail");
    expect(within(region).getByText("Result indeterminate")).toBeInTheDocument();
  });
});
