// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { faultBranchTypeSchema } from "../services/faultContract";
import { FaultBranchRow } from "./FaultBranchRow";
import { createBranchDraft, createBusDraft } from "./faultStudyDraft";

afterEach(() => {
  cleanup();
});

const mainBus = { ...createBusDraft(), code: "MSB-01" };
const boardBus = { ...createBusDraft(), code: "DB-01" };
const buses = [mainBus, boardBus];

function optionTexts(label: string): (string | null)[] {
  return within(screen.getByLabelText(label))
    .getAllByRole("option")
    .map((option) => option.textContent);
}

describe("FaultBranchRow", () => {
  it("shows the branch under its number with its fields, in service and removable", () => {
    render(
      <FaultBranchRow
        branch={createBranchDraft()}
        index={0}
        buses={buses}
        onChange={vi.fn()}
        onRemove={vi.fn()}
      />,
    );

    const row = screen.getByRole("group", { name: "Branch 1" });
    for (const label of [
      "Branch code",
      "Branch name",
      "From bus",
      "To bus",
      "Branch type",
      "Parallel circuits - optional",
    ]) {
      expect(within(row).getByLabelText(label)).toBeInTheDocument();
    }
    expect(within(row).getByLabelText("In service")).toBeChecked();
    expect(within(row).getByRole("button", { name: "Remove branch 1" })).toBeInTheDocument();
    expect(row.querySelector("[data-same-bus-warning]")).toBeNull();
  });

  it("always shows the three impedance pairs; only the positive one is not optional", () => {
    render(
      <FaultBranchRow
        branch={createBranchDraft()}
        index={0}
        buses={buses}
        onChange={vi.fn()}
        onRemove={vi.fn()}
      />,
    );

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
  });

  it("lists the buses of the study for both ends and sends the chosen ids", () => {
    const onChange = vi.fn();
    render(
      <FaultBranchRow
        branch={createBranchDraft()}
        index={0}
        buses={buses}
        onChange={onChange}
        onRemove={vi.fn()}
      />,
    );

    expect(optionTexts("From bus")).toEqual(["Select bus", "Bus 1 — MSB-01", "Bus 2 — DB-01"]);
    expect(optionTexts("To bus")).toEqual(["Select bus", "Bus 1 — MSB-01", "Bus 2 — DB-01"]);

    fireEvent.change(screen.getByLabelText("From bus"), { target: { value: mainBus.id } });
    fireEvent.change(screen.getByLabelText("To bus"), { target: { value: boardBus.id } });

    expect(onChange).toHaveBeenNthCalledWith(1, { fromBusId: mainBus.id });
    expect(onChange).toHaveBeenNthCalledWith(2, { toBusId: boardBus.id });
  });

  it("sends every edit up as a patch and keeps the other half of an impedance pair", () => {
    const branch = {
      ...createBranchDraft(),
      positive: { resistanceOhm: "0.0124", reactanceOhm: "" },
    };
    const onChange = vi.fn();
    render(
      <FaultBranchRow branch={branch} index={0} buses={buses} onChange={onChange} onRemove={vi.fn()} />,
    );

    fireEvent.change(screen.getByLabelText("Branch code"), { target: { value: "CBL-01" } });
    fireEvent.change(screen.getByLabelText("Branch type"), { target: { value: "CABLE" } });
    fireEvent.change(screen.getByLabelText("Positive-sequence reactance (Ω)"), {
      target: { value: "0.0080" },
    });
    fireEvent.change(screen.getByLabelText("Parallel circuits - optional"), {
      target: { value: "2" },
    });
    fireEvent.click(screen.getByLabelText("In service"));

    expect(onChange).toHaveBeenNthCalledWith(1, { code: "CBL-01" });
    expect(onChange).toHaveBeenNthCalledWith(2, { branchType: "CABLE" });
    expect(onChange).toHaveBeenNthCalledWith(3, {
      positive: { resistanceOhm: "0.0124", reactanceOhm: "0.0080" },
    });
    expect(onChange).toHaveBeenNthCalledWith(4, { parallelCircuits: "2" });
    expect(onChange).toHaveBeenNthCalledWith(5, { inService: false });
  });

  it("shows an end whose bus was removed as not chosen", () => {
    const branch = { ...createBranchDraft(), fromBusId: "bus-removed", toBusId: boardBus.id };
    render(
      <FaultBranchRow branch={branch} index={0} buses={buses} onChange={vi.fn()} onRemove={vi.fn()} />,
    );

    expect(screen.getByLabelText("From bus")).toHaveValue("");
    expect(screen.getByLabelText("To bus")).toHaveValue(boardBus.id);
  });

  it("warns when both ends are the same bus", () => {
    const branch = { ...createBranchDraft(), fromBusId: mainBus.id, toBusId: mainBus.id };
    render(
      <FaultBranchRow branch={branch} index={0} buses={buses} onChange={vi.fn()} onRemove={vi.fn()} />,
    );

    expect(document.querySelector("[data-same-bus-warning]")).toHaveTextContent(
      "a branch links two different buses",
    );
  });

  it("offers every branch type of the contract", () => {
    render(
      <FaultBranchRow
        branch={createBranchDraft()}
        index={0}
        buses={buses}
        onChange={vi.fn()}
        onRemove={vi.fn()}
      />,
    );

    const values = within(screen.getByLabelText("Branch type"))
      .getAllByRole("option")
      .map((option) => option.getAttribute("value"));
    expect(values).toEqual(["", ...faultBranchTypeSchema.options]);
  });

  it("removes the branch on request", () => {
    const onRemove = vi.fn();
    render(
      <FaultBranchRow
        branch={createBranchDraft()}
        index={2}
        buses={buses}
        onChange={vi.fn()}
        onRemove={onRemove}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Remove branch 3" }));
    expect(onRemove).toHaveBeenCalledTimes(1);
  });
});
