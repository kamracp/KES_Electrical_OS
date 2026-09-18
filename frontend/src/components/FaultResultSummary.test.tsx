// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";
import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import type { ShortCircuitStudyResponse } from "../services/fault";
import { FaultResultSummary } from "./FaultResultSummary";

const calculated: ShortCircuitStudyResponse = {
  study_code: "SC-MSB-01",
  study_name: "Main switchboard three-phase fault",
  calculation_case: "MAXIMUM",
  fault_bus_code: "MSB-01",
  fault_type: "THREE_PHASE",
  nominal_voltage_v: "415",
  frequency_hz: "50",
  status: "CALCULATED",
  initial_symmetrical_short_circuit_current_ka: "35.22",
  peak_short_circuit_current_ka: "84.57",
  symmetrical_breaking_current_ka: null,
  steady_state_short_circuit_current_ka: null,
  thermal_equivalent_short_circuit_current_ka: null,
  earth_fault_current_ka: null,
  kappa_factor: "1.698",
  x_r_ratio: "8.15",
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
  it("shows the study state, identity and the decisive currents verbatim", () => {
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

    expect(field(region, "initial-current")).toHaveTextContent("35.22 kA");
    expect(field(region, "peak-current")).toHaveTextContent("84.57 kA");
    expect(field(region, "x-r-ratio")).toHaveTextContent("8.15");
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
    expect(field(region, "peak-current")).toHaveTextContent("—");
    expect(field(region, "x-r-ratio")).toHaveTextContent("—");
    expect(field(region, "earth-fault-current")).toHaveTextContent("32.915 kA");
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
