// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { ShortCircuitStudyRequest } from "../services/fault";
import { FaultStudyForm } from "./FaultStudyForm";

afterEach(() => {
  cleanup();
});

function group(name: string): HTMLElement {
  return screen.getByRole("group", { name });
}

function change(label: string, value: string, scope: HTMLElement = document.body) {
  fireEvent.change(within(scope).getByLabelText(label), { target: { value } });
}

// Chooses a select option by the text the user sees; the value is a row id.
function choose(label: string, optionText: string, scope: HTMLElement = document.body) {
  const select = within(scope).getByLabelText(label);
  const option = within(select).getByRole("option", { name: optionText }) as HTMLOptionElement;
  fireEvent.change(select, { target: { value: option.value } });
}

function submit() {
  fireEvent.click(screen.getByRole("button", { name: "Calculate fault study" }));
}

function fillBaseStudy() {
  change("Study code", "FAULT-001");
  change("Study name", "Main LV Bus Fault Study");
  change("Calculation case", "MAXIMUM");
  change("Fault type", "THREE_PHASE");
  change("Bus code", "BUS-1");
  change("Bus name", "Main LV Bus");
  change("Nominal voltage (V)", "415");
  change("Maximum voltage factor", "1.10");
  change("Minimum voltage factor", "0.95");
  change("Neutral earthing mode", "SOLIDLY_EARTHED");
  change("Source code", "GRID-1");
  change("Source name", "Utility Grid");
  change("Source type", "UTILITY_GRID");
}

function fillImpedanceSource() {
  change("Source representation", "VOLTAGE_BEHIND_IMPEDANCE");
  change("Positive-sequence resistance (Ω)", "0.0100");
  change("Positive-sequence reactance (Ω)", "0.0200");
}

describe("FaultStudyForm", () => {
  it("starts as a single-bus study: one bus, one source on it, no branch", () => {
    render(<FaultStudyForm onSubmit={vi.fn()} />);

    for (const name of ["Study definition", "Buses", "Sources", "Branches", "Bus 1", "Source 1"]) {
      expect(group(name)).toBeInTheDocument();
    }
    expect(screen.queryByRole("group", { name: "Bus 2" })).not.toBeInTheDocument();
    expect(screen.queryByRole("group", { name: "Branch 1" })).not.toBeInTheDocument();
    expect(document.querySelector("[data-no-branches]")).toBeInTheDocument();
    expect(document.querySelector("[data-representation-hint]")).toBeInTheDocument();

    expect(screen.getByLabelText("Fault at bus")).not.toHaveValue("");
    expect(screen.getByLabelText("Connected bus")).toHaveValue(
      (screen.getByLabelText("Fault at bus") as HTMLSelectElement).value,
    );
    expect(screen.queryByRole("button", { name: /^Remove/ })).not.toBeInTheDocument();
    expect(
      screen.queryByLabelText("Positive-sequence resistance (Ω)"),
    ).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Current contribution (kA)")).not.toBeInTheDocument();
  });

  it("blocks an invalid draft with a readable message before calling the submit handler", async () => {
    const onSubmit = vi.fn();
    render(<FaultStudyForm onSubmit={onSubmit} />);

    submit();

    expect(await screen.findByRole("alert")).toHaveTextContent("Study code is required.");
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("submits a validated voltage-behind-impedance request with exact decimals", async () => {
    const onSubmit = vi.fn<(payload: ShortCircuitStudyRequest) => void>();
    render(<FaultStudyForm onSubmit={onSubmit} />);
    fillBaseStudy();
    change("Frequency (Hz)", "50.0");
    fillImpedanceSource();

    submit();

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
    expect(payload).not.toHaveProperty("branches");
  });

  it("switches to current-injection input and preserves the exact contribution", async () => {
    const onSubmit = vi.fn<(payload: ShortCircuitStudyRequest) => void>();
    render(<FaultStudyForm onSubmit={onSubmit} />);
    fillBaseStudy();

    change("Source representation", "CURRENT_INJECTION");

    expect(screen.getByLabelText("Current contribution (kA)")).toBeInTheDocument();
    expect(
      screen.queryByLabelText("Positive-sequence resistance (Ω)"),
    ).not.toBeInTheDocument();

    change("Current contribution (kA)", "2.750");
    submit();

    await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1));
    expect(onSubmit.mock.calls[0]?.[0].sources[0]).toMatchObject({
      representation: "CURRENT_INJECTION",
      current_contribution_ka: "2.750",
    });
    expect(onSubmit.mock.calls[0]?.[0].sources[0]).not.toHaveProperty(
      "positive_sequence_impedance",
    );
  });

  it("rewrites the raw source-name message the founder saw", async () => {
    const onSubmit = vi.fn();
    render(<FaultStudyForm onSubmit={onSubmit} />);
    fillBaseStudy();
    fillImpedanceSource();
    change("Source name", "");

    submit();

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Source 1 — Source name is required.",
    );
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("builds a two-bus network: second bus, a cable branch and the fault at the far bus", async () => {
    const onSubmit = vi.fn<(payload: ShortCircuitStudyRequest) => void>();
    render(<FaultStudyForm onSubmit={onSubmit} />);
    fillBaseStudy();
    fillImpedanceSource();

    fireEvent.click(screen.getByRole("button", { name: "Add bus" }));
    const board = group("Bus 2");
    change("Bus code", "DB-01", board);
    change("Bus name", "Distribution board", board);
    change("Nominal voltage (V)", "415", board);
    change("Maximum voltage factor", "1.10", board);
    change("Minimum voltage factor", "0.95", board);
    change("Neutral earthing mode", "SOLIDLY_EARTHED", board);

    fireEvent.click(screen.getByRole("button", { name: "Add branch" }));
    const feeder = group("Branch 1");
    expect(document.querySelector("[data-no-branches]")).not.toBeInTheDocument();
    change("Branch code", "CBL-01", feeder);
    change("Branch name", "Feeder to DB-01", feeder);
    choose("From bus", "Bus 1 — BUS-1", feeder);
    choose("To bus", "Bus 2 — DB-01", feeder);
    change("Branch type", "CABLE", feeder);
    change("Positive-sequence resistance (Ω)", "0.0124", feeder);
    change("Positive-sequence reactance (Ω)", "0.0080", feeder);

    choose("Fault at bus", "Bus 2 — DB-01");
    submit();

    await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1));
    const payload = onSubmit.mock.calls[0]?.[0];

    expect(payload?.fault.bus_code).toBe("DB-01");
    expect(payload?.buses.map((bus) => bus.code)).toEqual(["BUS-1", "DB-01"]);
    expect(payload?.sources[0]?.bus_code).toBe("BUS-1");
    expect(payload?.branches).toEqual([
      {
        code: "CBL-01",
        name: "Feeder to DB-01",
        from_bus_code: "BUS-1",
        to_bus_code: "DB-01",
        branch_type: "CABLE",
        positive_sequence_impedance: { resistance_ohm: "0.0124", reactance_ohm: "0.0080" },
      },
    ]);
  });

  it("adds and removes rows and never removes the last bus or source", () => {
    render(<FaultStudyForm onSubmit={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: "Add source" }));
    expect(group("Source 2")).toBeInTheDocument();
    // One bus only: the new source is connected without asking.
    expect(within(group("Source 2")).getByLabelText("Connected bus")).not.toHaveValue("");

    fireEvent.click(screen.getByRole("button", { name: "Remove source 1" }));
    expect(screen.queryByRole("group", { name: "Source 2" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^Remove source/ })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Add branch" }));
    fireEvent.click(screen.getByRole("button", { name: "Remove branch 1" }));
    expect(screen.queryByRole("group", { name: "Branch 1" })).not.toBeInTheDocument();
    expect(document.querySelector("[data-no-branches]")).toBeInTheDocument();
  });

  it("moves the fault to the only bus left and names a source that lost its bus", async () => {
    const onSubmit = vi.fn();
    render(<FaultStudyForm onSubmit={onSubmit} />);
    fillBaseStudy();
    fillImpedanceSource();

    fireEvent.click(screen.getByRole("button", { name: "Add bus" }));
    change("Bus code", "DB-01", group("Bus 2"));
    choose("Fault at bus", "Bus 2 — DB-01");
    choose("Connected bus", "Bus 2 — DB-01");

    fireEvent.click(screen.getByRole("button", { name: "Remove bus 2" }));

    const faultBus = screen.getByLabelText("Fault at bus") as HTMLSelectElement;
    expect(within(faultBus).getByRole("option", { name: "Bus 1 — BUS-1" })).toHaveValue(
      faultBus.value,
    );
    expect(screen.getByLabelText("Connected bus")).toHaveValue("");

    submit();

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Source 1 — Connected bus is required.",
    );
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("disables the engineering inputs and every action when requested", () => {
    render(<FaultStudyForm disabled onSubmit={vi.fn()} />);

    expect(screen.getByRole("button", { name: "Calculate fault study" })).toBeDisabled();
    expect(screen.getByLabelText("Study code")).toBeDisabled();
    expect(screen.getByLabelText("Source representation")).toBeDisabled();
    expect(screen.getByRole("button", { name: "Add bus" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Add branch" })).toBeDisabled();
  });
});
