// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { CableSizingRequest } from "../services/cable";
import { CableSizingForm } from "./CableSizingForm";

afterEach(() => {
  cleanup();
});

function change(label: string, value: string) {
  fireEvent.change(screen.getByLabelText(label), { target: { value } });
}

function fillMinimumValidDraft() {
  change("Study code", "CBL-001");
  change("Study name", "Feeder to MCC-1");
  change("Design current (A)", "250");
  change("Nominal voltage (V)", "415");
  change("Route length (m)", "120.0");
  change("System", "THREE_PHASE_FOUR_WIRE");
  change("Conductor material", "COPPER");
  change("Insulation", "XLPE");
  change("Construction", "MULTICORE");
  change("Arrangement", "MULTICORE");
  change("Loaded conductors", "3");
  change("Installation method", "CABLE_TRAY");
  change("Ambient temperature (°C)", "40");
  change("Phase sizes", "70, 95, 120, 150");
}

describe("CableSizingForm", () => {
  it("renders the five input groups and the submit button", () => {
    render(<CableSizingForm onSubmit={vi.fn()} />);

    for (const name of [
      "Study definition",
      "Circuit",
      "Cable",
      "Installation",
      "Size schedule (mm², comma-separated, ascending)",
    ]) {
      expect(screen.getByRole("group", { name })).toBeInTheDocument();
    }
    expect(screen.getByRole("button", { name: "Calculate cable sizing" })).toBeEnabled();
  });

  it("blocks an empty draft before calling the submit handler", async () => {
    const onSubmit = vi.fn();
    render(<CableSizingForm onSubmit={onSubmit} />);

    fireEvent.click(screen.getByRole("button", { name: "Calculate cable sizing" }));

    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("submits a validated request with exact decimals and omits blank optionals", async () => {
    const onSubmit = vi.fn<(payload: CableSizingRequest) => void>();
    render(<CableSizingForm onSubmit={onSubmit} />);
    fillMinimumValidDraft();

    fireEvent.click(screen.getByRole("button", { name: "Calculate cable sizing" }));

    await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1));
    const payload = onSubmit.mock.calls[0]?.[0];

    expect(payload).toEqual({
      code: "CBL-001",
      name: "Feeder to MCC-1",
      circuit: {
        design_current_a: "250",
        nominal_voltage_v: "415",
        route_length_m: "120.0",
        system: "THREE_PHASE_FOUR_WIRE",
      },
      cable: {
        conductor_material: "COPPER",
        insulation_material: "XLPE",
        construction: "MULTICORE",
        arrangement: "MULTICORE",
        number_of_loaded_conductors: 3,
        neutral_required: true,
        reduced_neutral_permitted: false,
        armoured: false,
      },
      installation: {
        method: "CABLE_TRAY",
        ambient_temperature_c: "40",
      },
      size_schedule: {
        phase_sizes_mm2: ["70", "95", "120", "150"],
      },
    });
    expect(payload?.circuit).not.toHaveProperty("power_factor");
    expect(payload?.installation).not.toHaveProperty("grouping_derating_factor");
    expect(payload).not.toHaveProperty("notes");
  });

  it("carries optional decimals, integers, checkboxes and extra schedules through", async () => {
    const onSubmit = vi.fn<(payload: CableSizingRequest) => void>();
    render(<CableSizingForm onSubmit={onSubmit} />);
    fillMinimumValidDraft();
    change("Notes", "Route via CT-01");
    change("Power factor", "0.85");
    change("Allowable voltage drop (%)", "3");
    change("Fault current (kA)", "25");
    change("Fault duration (s)", "0.5");
    change("Parallel runs", "2");
    change("Protective conductor", "METALLIC_ARMOUR");
    change("Grouping derating factor", "0.80");
    change("Grouped circuits", "3");
    change("Neutral sizes", "35,50,70,95");
    change("Protective sizes", "35, 50, 70");
    fireEvent.click(screen.getByLabelText("Armoured"));
    fireEvent.click(screen.getByLabelText("Neutral required"));

    fireEvent.click(screen.getByRole("button", { name: "Calculate cable sizing" }));

    await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1));
    const payload = onSubmit.mock.calls[0]?.[0];

    expect(payload).toMatchObject({
      notes: "Route via CT-01",
      circuit: {
        power_factor: "0.85",
        allowable_voltage_drop_percent: "3",
        fault_current_ka: "25",
        fault_duration_s: "0.5",
      },
      cable: {
        parallel_runs: 2,
        protective_conductor_type: "METALLIC_ARMOUR",
        armoured: true,
        neutral_required: false,
      },
      installation: {
        grouping_derating_factor: "0.80",
        grouped_circuits: 3,
      },
      size_schedule: {
        phase_sizes_mm2: ["70", "95", "120", "150"],
        neutral_sizes_mm2: ["35", "50", "70", "95"],
        protective_sizes_mm2: ["35", "50", "70"],
      },
    });
  });

  it("reports a descending size schedule with its field path", async () => {
    const onSubmit = vi.fn();
    render(<CableSizingForm onSubmit={onSubmit} />);
    fillMinimumValidDraft();
    change("Phase sizes", "95, 70, 120");

    fireEvent.click(screen.getByRole("button", { name: "Calculate cable sizing" }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("size_schedule.phase_sizes_mm2.1:");
    expect(alert).toHaveTextContent("ascending");
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("rejects a non-decimal engineering value with its field path", async () => {
    const onSubmit = vi.fn();
    render(<CableSizingForm onSubmit={onSubmit} />);
    fillMinimumValidDraft();
    change("Design current (A)", "250 A");

    fireEvent.click(screen.getByRole("button", { name: "Calculate cable sizing" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("circuit.design_current_a:");
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("disables every input group and the button while a calculation is pending", () => {
    render(<CableSizingForm disabled onSubmit={vi.fn()} />);

    expect(screen.getByRole("button", { name: "Calculate cable sizing" })).toBeDisabled();
    expect(screen.getByLabelText("Design current (A)")).toBeDisabled();
    expect(screen.getByLabelText("Phase sizes")).toBeDisabled();
  });
});
