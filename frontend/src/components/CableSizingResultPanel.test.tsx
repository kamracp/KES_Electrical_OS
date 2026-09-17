// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";
import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import type { CableSizingResponse } from "../services/cable";
import { CableSizingResultPanel } from "./CableSizingResultPanel";

afterEach(() => {
  cleanup();
});

// Decimal strings deliberately carry trailing zeros to prove verbatim rendering.
const fullResult: CableSizingResponse = {
  study_code: "CBL-001",
  status: "DESIGN_CHECK_PASSED",
  conductor: {
    phase_area_mm2: "120.50",
    neutral_area_mm2: "70.00",
    protective_area_mm2: null,
    parallel_runs: 2,
    phase_conductors_per_run: 3,
    neutral_status: "PASS",
    protective_status: "NOT_APPLICABLE",
  },
  ampacity: {
    tabulated_ampacity_a_per_run: "251.00",
    combined_derating_factor: "0.8700",
    derated_ampacity_a_per_run: "218.37",
    parallel_runs: 2,
    total_installed_ampacity_a: "436.74",
    design_current_a: "400.00",
    required_tabulated_ampacity_a_per_run: "229.89",
    utilization_ratio: "0.9158",
    status: "PASS",
  },
  voltage_drop: {
    resistance_ohm_per_km: "0.1530",
    reactance_ohm_per_km: "0.0780",
    voltage_drop_v: "9.4200",
    voltage_drop_percent: "2.2700",
    allowable_voltage_drop_percent: "5.00",
    status: "PASS",
  },
  short_circuit: {
    fault_current_ka: "25.000",
    fault_duration_s: "1.00",
    material_constant_k: "143",
    required_area_mm2: "174.83",
    selected_area_mm2: "240.00",
    withstand_current_ka: "34.32",
    status: "FAIL",
  },
  warnings: [],
  standard_reference: "IS 732:2019 (UNVERIFIED)",
  ampacity_reference: "IS 3961 tabulated data (UNVERIFIED)",
  reference_source: "PROFILE",
  jurisdiction_profile: "IN",
  reference_verification_status: "UNVERIFIED",
  notes: "Derating applied for grouping and ambient.",
};

function region(name: string): HTMLElement {
  return screen.getByRole("region", { name });
}

describe("CableSizingResultPanel", () => {
  it("renders the study code, overall status badge, and all four check tables", () => {
    render(<CableSizingResultPanel result={fullResult} />);

    expect(screen.getByText("CBL-001")).toHaveAttribute("data-study-code", "true");
    const badge = screen.getByText("Design check passed");
    expect(badge).toHaveAttribute("data-sizing-status", "DESIGN_CHECK_PASSED");

    for (const title of [
      "Conductor selection",
      "Ampacity check",
      "Voltage drop check",
      "Short-circuit withstand check",
    ]) {
      expect(within(region(title)).getByRole("table")).toBeInTheDocument();
    }
  });

  it("gives the two voltage drop rows distinct keys and labels", () => {
    render(<CableSizingResultPanel result={fullResult} />);
    const table = region("Voltage drop check");

    const voltsRow = table.querySelector('[data-row-key="voltage_drop_v"]');
    const percentRow = table.querySelector('[data-row-key="voltage_drop_percent"]');
    expect(voltsRow).not.toBeNull();
    expect(percentRow).not.toBeNull();
    expect(voltsRow).toHaveTextContent("Voltage drop (V)");
    expect(voltsRow).toHaveTextContent("9.4200");
    expect(percentRow).toHaveTextContent("Voltage drop (%)");
    expect(percentRow).toHaveTextContent("2.2700");
  });

  it("renders decimals verbatim and an em dash for null values", () => {
    render(<CableSizingResultPanel result={fullResult} />);

    const conductor = region("Conductor selection");
    expect(within(conductor).getByText("120.50")).toBeInTheDocument();
    expect(within(conductor).queryByText("120.5")).toBeNull();

    const protectiveRow = conductor.querySelector('[data-row-key="protective_area_mm2"]');
    expect(protectiveRow).not.toBeNull();
    const cells = protectiveRow!.querySelectorAll("td");
    expect(cells[0]).toHaveTextContent("\u2014");
    expect(cells[1]).toHaveTextContent("N/A");
    expect(cells[1]).toHaveAttribute("data-check-status", "NOT_APPLICABLE");
  });

  it("maps check statuses to Pass, Fail, and N/A labels", () => {
    render(<CableSizingResultPanel result={fullResult} />);

    const neutralRow = region("Conductor selection").querySelector(
      '[data-row-key="neutral_area_mm2"]',
    );
    expect(neutralRow).toHaveTextContent("Pass");

    const selectedRow = region("Short-circuit withstand check").querySelector(
      '[data-row-key="selected_area_mm2"]',
    );
    expect(selectedRow).toHaveTextContent("Fail");
    expect(selectedRow!.querySelector("[data-check-status]")).toHaveAttribute(
      "data-check-status",
      "FAIL",
    );
  });

  it("shows Not evaluated instead of a table when a section is null", () => {
    const partial: CableSizingResponse = {
      ...fullResult,
      status: "NO_STANDARD_SIZE_AVAILABLE",
      ampacity: null,
      voltage_drop: null,
      short_circuit: null,
    };
    render(<CableSizingResultPanel result={partial} />);

    expect(screen.getByText("No standard size available")).toHaveAttribute(
      "data-sizing-status",
      "NO_STANDARD_SIZE_AVAILABLE",
    );
    for (const title of ["Ampacity check", "Voltage drop check", "Short-circuit withstand check"]) {
      const section = region(title);
      expect(within(section).getByText("Not evaluated")).toBeInTheDocument();
      expect(within(section).queryByRole("table")).toBeNull();
    }
    expect(within(region("Conductor selection")).getByRole("table")).toBeInTheDocument();
  });

  it("renders references, optional notes, and the design-check footer", () => {
    const { unmount } = render(<CableSizingResultPanel result={fullResult} />);

    expect(screen.getByText("IS 732:2019 (UNVERIFIED)")).toBeInTheDocument();
    expect(screen.getByText("IS 3961 tabulated data (UNVERIFIED)")).toBeInTheDocument();
    expect(screen.getByText("Derating applied for grouping and ambient.")).toHaveAttribute(
      "data-notes",
      "true",
    );
    expect(screen.getByText(/not a statutory compliance certification/i)).toBeInTheDocument();
    unmount();

    render(<CableSizingResultPanel result={{ ...fullResult, notes: null }} />);
    expect(document.querySelector("[data-notes]")).toBeNull();
    expect(screen.getByText(/not a statutory compliance certification/i)).toBeInTheDocument();
  });
});
