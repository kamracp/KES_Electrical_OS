// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { ShortCircuitStudyRequest } from "../services/fault";
import { FaultStudyForm } from "./FaultStudyForm";

afterEach(() => {
  cleanup();
});

function fillBaseStudy() {
  fireEvent.change(screen.getByLabelText("Study code"), {
    target: { value: "FAULT-001" },
  });
  fireEvent.change(screen.getByLabelText("Study name"), {
    target: { value: "Main LV Bus Fault Study" },
  });
  fireEvent.change(screen.getByLabelText("Calculation case"), {
    target: { value: "MAXIMUM" },
  });
  fireEvent.change(screen.getByLabelText("Fault type"), {
    target: { value: "THREE_PHASE" },
  });
  fireEvent.change(screen.getByLabelText("Bus code"), {
    target: { value: "BUS-1" },
  });
  fireEvent.change(screen.getByLabelText("Bus name"), {
    target: { value: "Main LV Bus" },
  });
  fireEvent.change(screen.getByLabelText("Nominal voltage (V)"), {
    target: { value: "415" },
  });
  fireEvent.change(screen.getByLabelText("Maximum voltage factor"), {
    target: { value: "1.10" },
  });
  fireEvent.change(screen.getByLabelText("Minimum voltage factor"), {
    target: { value: "0.95" },
  });
  fireEvent.change(screen.getByLabelText("Neutral earthing mode"), {
    target: { value: "SOLIDLY_EARTHED" },
  });
  fireEvent.change(screen.getByLabelText("Source code"), {
    target: { value: "GRID-1" },
  });
  fireEvent.change(screen.getByLabelText("Source name"), {
    target: { value: "Utility Grid" },
  });
  fireEvent.change(screen.getByLabelText("Source type"), {
    target: { value: "UTILITY_GRID" },
  });
}

describe("FaultStudyForm", () => {
  it("renders the study, fault-bus, and source input groups", () => {
    render(<FaultStudyForm onSubmit={vi.fn()} />);

    expect(screen.getByRole("group", { name: "Study definition" })).toBeInTheDocument();
    expect(screen.getByRole("group", { name: "Fault bus" })).toBeInTheDocument();
    expect(screen.getByRole("group", { name: "Source" })).toBeInTheDocument();
    expect(
      screen.queryByLabelText("Positive-sequence resistance (Ω)"),
    ).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Current contribution (kA)")).not.toBeInTheDocument();
  });

  it("blocks an invalid draft before calling the submit handler", async () => {
    const onSubmit = vi.fn();
    render(<FaultStudyForm onSubmit={onSubmit} />);

    fireEvent.click(screen.getByRole("button", { name: "Calculate fault study" }));

    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("submits a validated voltage-behind-impedance request with exact decimals", async () => {
    const onSubmit = vi.fn<(payload: ShortCircuitStudyRequest) => void>();
    render(<FaultStudyForm onSubmit={onSubmit} />);
    fillBaseStudy();

    fireEvent.change(screen.getByLabelText("Frequency (Hz)"), {
      target: { value: "50.0" },
    });
    fireEvent.change(screen.getByLabelText("Source representation"), {
      target: { value: "VOLTAGE_BEHIND_IMPEDANCE" },
    });
    fireEvent.change(screen.getByLabelText("Positive-sequence resistance (Ω)"), {
      target: { value: "0.0100" },
    });
    fireEvent.change(screen.getByLabelText("Positive-sequence reactance (Ω)"), {
      target: { value: "0.0200" },
    });

    fireEvent.click(screen.getByRole("button", { name: "Calculate fault study" }));

    await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1));
    const payload = onSubmit.mock.calls[0]?.[0];

    expect(payload).toMatchObject({
      code: "FAULT-001",
      name: "Main LV Bus Fault Study",
      calculation_case: "MAXIMUM",
      frequency_hz: "50.0",
      fault: {
        bus_code: "BUS-1",
        fault_type: "THREE_PHASE",
      },
      buses: [
        {
          code: "BUS-1",
          name: "Main LV Bus",
          nominal_voltage_v: "415",
          voltage_factor_max: "1.10",
          voltage_factor_min: "0.95",
          neutral_earthing_mode: "SOLIDLY_EARTHED",
        },
      ],
      sources: [
        {
          code: "GRID-1",
          name: "Utility Grid",
          bus_code: "BUS-1",
          source_type: "UTILITY_GRID",
          representation: "VOLTAGE_BEHIND_IMPEDANCE",
          positive_sequence_impedance: {
            resistance_ohm: "0.0100",
            reactance_ohm: "0.0200",
          },
        },
      ],
    });
    expect(payload?.sources[0]).not.toHaveProperty("current_contribution_ka");
  });

  it("switches to current-injection input and preserves the exact contribution", async () => {
    const onSubmit = vi.fn<(payload: ShortCircuitStudyRequest) => void>();
    render(<FaultStudyForm onSubmit={onSubmit} />);
    fillBaseStudy();

    fireEvent.change(screen.getByLabelText("Source representation"), {
      target: { value: "CURRENT_INJECTION" },
    });

    expect(screen.getByLabelText("Current contribution (kA)")).toBeInTheDocument();
    expect(
      screen.queryByLabelText("Positive-sequence resistance (Ω)"),
    ).not.toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Current contribution (kA)"), {
      target: { value: "2.750" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Calculate fault study" }));

    await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1));
    expect(onSubmit.mock.calls[0]?.[0].sources[0]).toMatchObject({
      representation: "CURRENT_INJECTION",
      current_contribution_ka: "2.750",
    });
    expect(onSubmit.mock.calls[0]?.[0].sources[0]).not.toHaveProperty(
      "positive_sequence_impedance",
    );
  });

  it("disables the engineering inputs and submit action when requested", () => {
    render(<FaultStudyForm disabled onSubmit={vi.fn()} />);

    expect(screen.getByRole("button", { name: "Calculate fault study" })).toBeDisabled();
    expect(screen.getByLabelText("Study code")).toBeDisabled();
    expect(screen.getByLabelText("Source representation")).toBeDisabled();
  });
});
