// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { neutralEarthingModeSchema } from "../services/faultContract";
import { FaultBusRow } from "./FaultBusRow";
import { createBusDraft } from "./faultStudyDraft";

afterEach(() => {
  cleanup();
});

describe("FaultBusRow", () => {
  it("shows the bus under its number with the Fault UI v1 labels", () => {
    render(<FaultBusRow bus={createBusDraft()} index={1} onChange={vi.fn()} />);

    const row = screen.getByRole("group", { name: "Bus 2" });
    for (const label of [
      "Bus code",
      "Bus name",
      "Nominal voltage (V)",
      "Maximum voltage factor",
      "Minimum voltage factor",
      "Neutral earthing mode",
    ]) {
      expect(within(row).getByLabelText(label)).toBeInTheDocument();
    }
    expect(within(row).getByLabelText("Nominal voltage (V)")).toHaveAttribute(
      "inputmode",
      "decimal",
    );
    expect(within(row).queryByLabelText("Neutral resistance (Ω)")).not.toBeInTheDocument();
    expect(within(row).queryByLabelText("Neutral reactance (Ω)")).not.toBeInTheDocument();
    expect(within(row).queryByRole("button")).not.toBeInTheDocument();
  });

  it("sends every edit up as a patch and keeps the text exactly", () => {
    const onChange = vi.fn();
    render(<FaultBusRow bus={createBusDraft()} index={0} onChange={onChange} />);

    fireEvent.change(screen.getByLabelText("Bus code"), { target: { value: "MSB-01" } });
    fireEvent.change(screen.getByLabelText("Maximum voltage factor"), {
      target: { value: "1.10" },
    });
    fireEvent.change(screen.getByLabelText("Neutral earthing mode"), {
      target: { value: "SOLIDLY_EARTHED" },
    });

    expect(onChange).toHaveBeenNthCalledWith(1, { code: "MSB-01" });
    expect(onChange).toHaveBeenNthCalledWith(2, { voltageFactorMax: "1.10" });
    expect(onChange).toHaveBeenNthCalledWith(3, { neutralEarthingMode: "SOLIDLY_EARTHED" });
  });

  it("offers every earthing mode of the contract", () => {
    render(<FaultBusRow bus={createBusDraft()} index={0} onChange={vi.fn()} />);

    const options = within(screen.getByLabelText("Neutral earthing mode")).getAllByRole("option");
    expect(options.map((option) => option.getAttribute("value"))).toEqual([
      "",
      ...neutralEarthingModeSchema.options,
    ]);
  });

  it("shows the neutral impedance that belongs to the earthing mode", () => {
    const onChange = vi.fn();
    const { rerender } = render(
      <FaultBusRow
        bus={{ ...createBusDraft(), neutralEarthingMode: "RESISTANCE_EARTHED" }}
        index={0}
        onChange={onChange}
      />,
    );

    fireEvent.change(screen.getByLabelText("Neutral resistance (Ω)"), {
      target: { value: "12.5" },
    });
    expect(onChange).toHaveBeenCalledWith({ neutralResistanceOhm: "12.5" });
    expect(screen.queryByLabelText("Neutral reactance (Ω)")).not.toBeInTheDocument();

    rerender(
      <FaultBusRow
        bus={{ ...createBusDraft(), neutralEarthingMode: "REACTANCE_EARTHED" }}
        index={0}
        onChange={onChange}
      />,
    );
    expect(screen.getByLabelText("Neutral reactance (Ω)")).toBeInTheDocument();
    expect(screen.queryByLabelText("Neutral resistance (Ω)")).not.toBeInTheDocument();
  });

  it("offers Remove only when the form allows it", () => {
    const onRemove = vi.fn();
    render(<FaultBusRow bus={createBusDraft()} index={1} onChange={vi.fn()} onRemove={onRemove} />);

    fireEvent.click(screen.getByRole("button", { name: "Remove bus 2" }));
    expect(onRemove).toHaveBeenCalledTimes(1);
  });
});
