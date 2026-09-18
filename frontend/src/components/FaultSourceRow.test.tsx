// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { faultSourceTypeSchema, sourceRepresentationSchema } from "../services/faultContract";
import { FaultSourceRow } from "./FaultSourceRow";
import { createBusDraft, createSourceDraft } from "./faultStudyDraft";

afterEach(() => {
  cleanup();
});

const mainBus = { ...createBusDraft(), code: "MSB-01" };
const unnamedBus = createBusDraft();
const buses = [mainBus, unnamedBus];

function optionValues(label: string): (string | null)[] {
  return within(screen.getByLabelText(label))
    .getAllByRole("option")
    .map((option) => option.getAttribute("value"));
}

describe("FaultSourceRow", () => {
  it("shows the source under its number with a hint until a representation is chosen", () => {
    render(
      <FaultSourceRow source={createSourceDraft(mainBus.id)} index={1} buses={buses} onChange={vi.fn()} />,
    );

    const row = screen.getByRole("group", { name: "Source 2" });
    for (const label of [
      "Source code",
      "Source name",
      "Connected bus",
      "Source type",
      "Source representation",
    ]) {
      expect(within(row).getByLabelText(label)).toBeInTheDocument();
    }
    expect(within(row).getByLabelText("In service")).toBeChecked();
    expect(row.querySelector("[data-representation-hint]")).toHaveTextContent(
      "Choose a source representation first",
    );
    expect(within(row).queryByLabelText("Positive-sequence resistance (Ω)")).not.toBeInTheDocument();
    expect(within(row).queryByLabelText("Current contribution (kA)")).not.toBeInTheDocument();
    expect(within(row).queryByRole("button")).not.toBeInTheDocument();
  });

  it("replaces the hint with the impedance fields for voltage behind impedance", () => {
    const source = { ...createSourceDraft(mainBus.id), representation: "VOLTAGE_BEHIND_IMPEDANCE" };
    render(<FaultSourceRow source={source} index={0} buses={buses} onChange={vi.fn()} />);

    expect(document.querySelector("[data-representation-hint]")).toBeNull();
    for (const label of [
      "Positive-sequence resistance (Ω)",
      "Positive-sequence reactance (Ω)",
      "Negative-sequence resistance (Ω) - optional",
      "Negative-sequence reactance (Ω) - optional",
      "Zero-sequence resistance (Ω) - optional",
      "Zero-sequence reactance (Ω) - optional",
    ]) {
      expect(screen.getByLabelText(label)).toHaveAttribute("inputmode", "decimal");
    }
    expect(screen.queryByLabelText("Current contribution (kA)")).not.toBeInTheDocument();
  });

  it("shows only the current for current injection", () => {
    const source = { ...createSourceDraft(mainBus.id), representation: "CURRENT_INJECTION" };
    const onChange = vi.fn();
    render(<FaultSourceRow source={source} index={0} buses={buses} onChange={onChange} />);

    fireEvent.change(screen.getByLabelText("Current contribution (kA)"), {
      target: { value: "2.750" },
    });
    expect(onChange).toHaveBeenCalledWith({ currentContributionKa: "2.750" });
    expect(screen.queryByLabelText("Positive-sequence resistance (Ω)")).not.toBeInTheDocument();
    expect(document.querySelector("[data-representation-hint]")).toBeNull();
  });

  it("sends every edit up as a patch and keeps the other half of an impedance pair", () => {
    const source = {
      ...createSourceDraft(mainBus.id),
      representation: "VOLTAGE_BEHIND_IMPEDANCE",
      positive: { resistanceOhm: "", reactanceOhm: "0.00709" },
    };
    const onChange = vi.fn();
    render(<FaultSourceRow source={source} index={0} buses={buses} onChange={onChange} />);

    fireEvent.change(screen.getByLabelText("Source code"), { target: { value: "TX-01" } });
    fireEvent.change(screen.getByLabelText("Positive-sequence resistance (Ω)"), {
      target: { value: "0.00087" },
    });
    fireEvent.change(screen.getByLabelText("Zero-sequence reactance (Ω) - optional"), {
      target: { value: "0.0065" },
    });
    fireEvent.click(screen.getByLabelText("In service"));

    expect(onChange).toHaveBeenNthCalledWith(1, { code: "TX-01" });
    expect(onChange).toHaveBeenNthCalledWith(2, {
      positive: { resistanceOhm: "0.00087", reactanceOhm: "0.00709" },
    });
    expect(onChange).toHaveBeenNthCalledWith(3, {
      zero: { resistanceOhm: "", reactanceOhm: "0.0065" },
    });
    expect(onChange).toHaveBeenNthCalledWith(4, { inService: false });
  });

  it("lists the buses of the study for the connected bus", () => {
    const onChange = vi.fn();
    render(
      <FaultSourceRow source={createSourceDraft(mainBus.id)} index={0} buses={buses} onChange={onChange} />,
    );

    const select = screen.getByLabelText("Connected bus");
    expect(select).toHaveValue(mainBus.id);
    expect(within(select).getAllByRole("option").map((option) => option.textContent)).toEqual([
      "Select bus",
      "Bus 1 — MSB-01",
      "Bus 2",
    ]);

    fireEvent.change(select, { target: { value: unnamedBus.id } });
    expect(onChange).toHaveBeenCalledWith({ busId: unnamedBus.id });
  });

  it("shows a source whose bus was removed as not connected", () => {
    render(
      <FaultSourceRow source={createSourceDraft("bus-removed")} index={0} buses={buses} onChange={vi.fn()} />,
    );

    expect(screen.getByLabelText("Connected bus")).toHaveValue("");
  });

  it("offers every source type and representation of the contract", () => {
    render(
      <FaultSourceRow source={createSourceDraft(mainBus.id)} index={0} buses={buses} onChange={vi.fn()} />,
    );

    expect(optionValues("Source type")).toEqual(["", ...faultSourceTypeSchema.options]);
    expect(optionValues("Source representation")).toEqual(["", ...sourceRepresentationSchema.options]);
  });

  it("offers Remove only when the form allows it", () => {
    const onRemove = vi.fn();
    render(
      <FaultSourceRow
        source={createSourceDraft(mainBus.id)}
        index={1}
        buses={buses}
        onChange={vi.fn()}
        onRemove={onRemove}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Remove source 2" }));
    expect(onRemove).toHaveBeenCalledTimes(1);
  });
});
