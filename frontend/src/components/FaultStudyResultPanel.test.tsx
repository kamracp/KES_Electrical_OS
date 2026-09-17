// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";
import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import type { ShortCircuitStudyResponse } from "../services/fault";
import { FaultStudyResultPanel } from "./FaultStudyResultPanel";

afterEach(() => {
  cleanup();
});

function region(name: string): HTMLElement {
  return screen.getByRole("region", { name });
}

// Decimal strings deliberately carry trailing zeros to prove verbatim rendering.
const fullResult: ShortCircuitStudyResponse = {
  study_code: "SC-001",
  study_name: "Main switchboard three-phase fault",
  calculation_case: "MAXIMUM",
  fault_bus_code: "MSB-01",
  fault_type: "THREE_PHASE",
  nominal_voltage_v: "415",
  frequency_hz: "50",
  status: "CALCULATED",
  initial_symmetrical_short_circuit_current_ka: "25.40",
  peak_short_circuit_current_ka: "55.80",
  symmetrical_breaking_current_ka: "25.40",
  steady_state_short_circuit_current_ka: "24.90",
  thermal_equivalent_short_circuit_current_ka: null,
  earth_fault_current_ka: null,
  kappa_factor: "1.550",
  x_r_ratio: "6.20",
  clearing_time_s: null,
  sequence_results: [
    {
      sequence: "POSITIVE",
      available: true,
      resistance_ohm: "0.00120",
      reactance_ohm: "0.00930",
      path_reference_codes: ["SRC-01", "BR-01"],
      blocking_reference_codes: [],
    },
    {
      sequence: "ZERO",
      available: false,
      resistance_ohm: null,
      reactance_ohm: null,
      path_reference_codes: [],
      blocking_reference_codes: ["TX-01"],
    },
  ],
  source_contributions: [
    {
      source_code: "SRC-01",
      source_type: "UTILITY_GRID",
      representation: "VOLTAGE_BEHIND_IMPEDANCE",
      included: true,
      initial_symmetrical_current_ka: "25.40",
      peak_current_ka: "55.80",
      exclusion_reason: null,
    },
    {
      source_code: "M-07",
      source_type: "ASYNCHRONOUS_MOTOR",
      representation: "CURRENT_INJECTION",
      included: false,
      initial_symmetrical_current_ka: "0.00",
      peak_current_ka: null,
      exclusion_reason: "Out of service in the selected operating state",
    },
  ],
  warnings: [],
  standard_reference: "IEC 60909-0 (UNVERIFIED)",
  earth_current_reference: "IEC 60909-0 (UNVERIFIED)",
  operating_state_code: "NORMAL",
  notes: "Grid contribution from utility declared fault level.",
};

describe("FaultStudyResultPanel", () => {
  it("renders the header, fault definition and fault currents verbatim", () => {
    render(<FaultStudyResultPanel result={fullResult} />);

    expect(screen.getByText("SC-001")).toHaveAttribute("data-study-code", "true");
    expect(screen.getByText("Calculated")).toHaveAttribute("data-result-status", "CALCULATED");

    const definition = region("Fault definition");
    expect(within(definition).getByText("MSB-01")).toHaveAttribute("data-fault-bus", "MSB-01");
    expect(within(definition).getByText("Three-phase")).toHaveAttribute(
      "data-fault-type",
      "THREE_PHASE",
    );
    expect(within(definition).getByText("Maximum")).toHaveAttribute(
      "data-calculation-case",
      "MAXIMUM",
    );

    const currents = region("Fault currents");
    expect(within(currents).getByText("55.80")).toBeInTheDocument();
    expect(within(currents).queryByText("55.8")).toBeNull();
    expect(within(currents).getByText("1.550")).toBeInTheDocument();
  });

  it("renders an em dash and data-evaluated=false for currents that were not evaluated", () => {
    render(<FaultStudyResultPanel result={fullResult} />);

    const currents = region("Fault currents");
    const notEvaluated = currents.querySelectorAll('[data-evaluated="false"]');
    expect(notEvaluated).toHaveLength(3);
    for (const cell of notEvaluated) {
      expect(cell.textContent).toBe("\u2014");
    }
    expect(currents.querySelectorAll('[data-evaluated="true"]')).toHaveLength(6);
  });

  it("renders sequence rows and source contributions with availability and inclusion flags", () => {
    render(<FaultStudyResultPanel result={fullResult} />);

    const sequences = region("Sequence impedances");
    const zero = sequences.querySelector('[data-sequence="ZERO"]');
    expect(zero).toHaveAttribute("data-sequence", "ZERO");
    expect(zero?.querySelector("[data-available]")).toHaveAttribute("data-available", "false");
    expect(zero?.textContent).toContain("TX-01");
    expect(within(sequences).getByText("SRC-01, BR-01")).toBeInTheDocument();

    const contributions = region("Source contributions");
    const motor = contributions.querySelector('[data-source-code="M-07"]');
    expect(motor?.querySelector("[data-included]")).toHaveAttribute("data-included", "false");
    expect(motor?.textContent).toContain("Asynchronous motor");
    expect(motor?.textContent).toContain("Out of service in the selected operating state");
  });

  it("shows None reported for empty tables and renders references, notes and footer", () => {
    const { unmount } = render(<FaultStudyResultPanel result={fullResult} />);
    expect(screen.getAllByText("IEC 60909-0 (UNVERIFIED)", { selector: "dd" })).toHaveLength(2);
    expect(screen.getByText("Grid contribution from utility declared fault level.")).toHaveAttribute(
      "data-notes",
      "true",
    );
    expect(screen.getByText(/not a statutory compliance/i)).toBeInTheDocument();
    unmount();

    render(
      <FaultStudyResultPanel
        result={{ ...fullResult, sequence_results: [], source_contributions: [], notes: null }}
      />,
    );
    expect(document.querySelectorAll('[data-no-rows="true"]')).toHaveLength(2);
    expect(document.querySelector("[data-notes]")).toBeNull();
  });
});
