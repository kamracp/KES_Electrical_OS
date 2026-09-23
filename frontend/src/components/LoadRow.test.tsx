// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  loadScenarioSchema,
  phaseSystemSchema,
  powerBasisSchema,
} from "../services/loadDemandContract";
import {
  LoadRow,
  PHASE_SYSTEM_LABELS,
  POWER_BASIS_LABELS,
  SCENARIO_LABELS,
} from "./LoadRow";
import { createLoadRowDraft, LOAD_STUDY_LABELS } from "./loadStudyDraft";

afterEach(() => {
  cleanup();
});

const FIELD_LABELS = [
  "Load code",
  "Load name",
  "Quantity",
  "Rated power (kW)",
  "Phase system",
  "Voltage (V)",
  "Power factor",
  "Efficiency",
  "Utilization factor",
  "Demand factor",
  "Scenario",
  "Power basis",
  "Notes",
];

function optionValues(label: string): (string | null)[] {
  return within(screen.getByLabelText(label))
    .getAllByRole("option")
    .map((option) => option.getAttribute("value"));
}

describe("LoadRow", () => {
  it("shows every field of the load under its number", () => {
    render(<LoadRow load={createLoadRowDraft()} index={1} onChange={vi.fn()} />);

    const row = screen.getByRole("group", { name: "Load 2" });
    for (const label of FIELD_LABELS) {
      expect(within(row).getByLabelText(label)).toBeInTheDocument();
    }
    // Decimals are plain text inputs, so an exact string such as "0.850" is
    // kept as typed; only the keyboard hint differs.
    for (const label of ["Rated power (kW)", "Voltage (V)", "Power factor", "Efficiency"]) {
      expect(within(row).getByLabelText(label)).toHaveAttribute("inputmode", "decimal");
      expect(within(row).getByLabelText(label)).not.toHaveAttribute("type", "number");
    }
    expect(within(row).getByLabelText("Quantity")).toHaveAttribute("inputmode", "numeric");
  });

  it("uses the labels the validation messages use", () => {
    // The form's messages are built from LOAD_STUDY_LABELS; a field whose
    // on-screen label differs would name one thing and point at another.
    const labels = Object.entries(LOAD_STUDY_LABELS.fields)
      .filter(([path]) => path.startsWith("study.loads.*."))
      .map(([, label]) => label);

    expect(new Set(labels)).toEqual(new Set(FIELD_LABELS));
  });

  it("starts the phase system unchosen and offers every one of the contract", () => {
    render(<LoadRow load={createLoadRowDraft()} index={0} onChange={vi.fn()} />);

    expect(screen.getByLabelText("Phase system")).toHaveValue("");
    expect(optionValues("Phase system")).toEqual(["", ...phaseSystemSchema.options]);
    expect(
      within(screen.getByLabelText("Phase system")).getAllByRole("option")[0],
    ).toHaveTextContent("Select phase system");
  });

  it("offers every scenario and power basis of the contract", () => {
    render(<LoadRow load={createLoadRowDraft()} index={0} onChange={vi.fn()} />);

    expect(optionValues("Scenario")).toEqual([...loadScenarioSchema.options]);
    expect(optionValues("Power basis")).toEqual([...powerBasisSchema.options]);
    // Both have a backend default, so neither carries a "select" placeholder.
    expect(screen.getByLabelText("Scenario")).toHaveValue("NORMAL");
    expect(screen.getByLabelText("Power basis")).toHaveValue("ELECTRICAL_INPUT");
  });

  it("sends every edit up as a patch", () => {
    const onChange = vi.fn();
    render(<LoadRow load={createLoadRowDraft()} index={0} onChange={onChange} />);

    fireEvent.change(screen.getByLabelText("Load code"), { target: { value: "MTR-001" } });
    fireEvent.change(screen.getByLabelText("Quantity"), { target: { value: "2" } });
    fireEvent.change(screen.getByLabelText("Rated power (kW)"), { target: { value: "15" } });
    fireEvent.change(screen.getByLabelText("Utilization factor"), { target: { value: "0.80" } });
    fireEvent.change(screen.getByLabelText("Power basis"), {
      target: { value: "MECHANICAL_OUTPUT" },
    });

    expect(onChange).toHaveBeenNthCalledWith(1, { code: "MTR-001" });
    expect(onChange).toHaveBeenNthCalledWith(2, { quantity: "2" });
    expect(onChange).toHaveBeenNthCalledWith(3, { ratedPowerKw: "15" });
    expect(onChange).toHaveBeenNthCalledWith(4, { utilizationFactor: "0.80" });
    expect(onChange).toHaveBeenNthCalledWith(5, { powerBasis: "MECHANICAL_OUTPUT" });
  });

  it("says a blank factor means not established", () => {
    render(<LoadRow load={createLoadRowDraft()} index={0} onChange={vi.fn()} />);

    expect(document.querySelector("[data-not-established-hint]")).toHaveTextContent(
      "Leave a factor blank if it is not established",
    );
    expect(document.querySelector("[data-efficiency-hint]")).toHaveTextContent(
      "Used only when the power basis is Mechanical output.",
    );
  });

  it("locks and clears the power factor when DC is chosen", () => {
    const onChange = vi.fn();
    const load = { ...createLoadRowDraft(), phaseSystem: "THREE_PHASE", powerFactor: "0.85" };
    render(<LoadRow load={load} index={0} onChange={onChange} />);

    expect(screen.getByLabelText("Power factor")).toBeEnabled();
    expect(document.querySelector("[data-dc-power-factor-hint]")).toBeNull();

    fireEvent.change(screen.getByLabelText("Phase system"), { target: { value: "DC" } });

    // A DC load has no power factor, so the typed value goes with the choice.
    expect(onChange).toHaveBeenCalledWith({ phaseSystem: "DC", powerFactor: "" });
  });

  it("shows the DC hint and the disabled power factor once DC is the choice", () => {
    const load = { ...createLoadRowDraft(), phaseSystem: "DC" };
    render(<LoadRow load={load} index={0} onChange={vi.fn()} />);

    expect(screen.getByLabelText("Power factor")).toBeDisabled();
    expect(document.querySelector("[data-dc-power-factor-hint]")).toHaveTextContent(
      "DC: power factor is 1.",
    );
  });

  it("enables the power factor again when the load goes back to three-phase", () => {
    const onChange = vi.fn();
    const load = { ...createLoadRowDraft(), phaseSystem: "DC" };
    const { rerender } = render(<LoadRow load={load} index={0} onChange={onChange} />);

    fireEvent.change(screen.getByLabelText("Phase system"), { target: { value: "THREE_PHASE" } });
    expect(onChange).toHaveBeenCalledWith({ phaseSystem: "THREE_PHASE" });

    rerender(
      <LoadRow load={{ ...load, phaseSystem: "THREE_PHASE" }} index={0} onChange={onChange} />,
    );
    expect(screen.getByLabelText("Power factor")).toBeEnabled();
    expect(document.querySelector("[data-dc-power-factor-hint]")).toBeNull();
  });

  it("offers no remove button for the last remaining load", () => {
    render(<LoadRow load={createLoadRowDraft()} index={0} onChange={vi.fn()} />);

    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("removes the load it names when the form allows it", () => {
    const onRemove = vi.fn();
    render(
      <LoadRow load={createLoadRowDraft()} index={2} onChange={vi.fn()} onRemove={onRemove} />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Remove load 3" }));

    expect(onRemove).toHaveBeenCalledTimes(1);
  });
});

describe("the LoadRow label maps", () => {
  it("name every value the contract can carry", () => {
    // Drift guard: a value the backend adds must get a label here, not fall
    // through as a blank option.
    expect(Object.keys(PHASE_SYSTEM_LABELS).sort()).toEqual(
      [...phaseSystemSchema.options].sort(),
    );
    expect(Object.keys(SCENARIO_LABELS).sort()).toEqual([...loadScenarioSchema.options].sort());
    expect(Object.keys(POWER_BASIS_LABELS).sort()).toEqual([...powerBasisSchema.options].sort());
  });
});
