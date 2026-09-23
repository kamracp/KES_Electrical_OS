// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { LoadStudyForm } from "./LoadStudyForm";

afterEach(() => {
  cleanup();
});

function studyFieldset(): HTMLElement {
  return screen.getByRole("group", { name: "Study definition" });
}

function loadRow(number: number): HTMLElement {
  return screen.getByRole("group", { name: `Load ${number}` });
}

function rows(): HTMLElement[] {
  return screen.getAllByRole("group", { name: /^Load \d+$/ });
}

function type(scope: HTMLElement, label: string, value: string): void {
  fireEvent.change(within(scope).getByLabelText(label), { target: { value } });
}

function fillStudy(): void {
  type(studyFieldset(), "Study code", "LOAD-001");
  type(studyFieldset(), "Study name", "Process Pump Loads");
}

function fillThreePhaseRow(number: number, code: string, withFactors: boolean): void {
  const row = loadRow(number);
  type(row, "Load code", code);
  type(row, "Load name", "Process Water Pump");
  type(row, "Quantity", "2");
  type(row, "Rated power (kW)", "15");
  type(row, "Phase system", "THREE_PHASE");
  type(row, "Voltage (V)", "415");
  if (withFactors) {
    type(row, "Power factor", "0.85");
    type(row, "Efficiency", "0.92");
    type(row, "Utilization factor", "0.80");
    type(row, "Demand factor", "0.90");
  }
}

function fillDcRow(number: number, code: string): void {
  const row = loadRow(number);
  type(row, "Load code", code);
  type(row, "Load name", "DC Control Load");
  type(row, "Quantity", "1");
  type(row, "Rated power (kW)", "2.4");
  type(row, "Phase system", "DC");
  type(row, "Voltage (V)", "48");
}

function submit(): void {
  fireEvent.click(screen.getByRole("button", { name: "Calculate load study" }));
}

describe("LoadStudyForm", () => {
  it("starts with one load that cannot be removed", () => {
    render(<LoadStudyForm onSubmit={vi.fn()} />);

    expect(rows()).toHaveLength(1);
    expect(
      within(loadRow(1)).queryByRole("button", { name: "Remove load 1" }),
    ).not.toBeInTheDocument();
    expect(within(studyFieldset()).getByLabelText("Jurisdiction profile")).toHaveValue("IN");
    expect(document.querySelector("[data-coincidence-hint]")).toHaveTextContent(
      "Leave blank if not established",
    );
  });

  it("names the study notes apart from a load's own notes", () => {
    render(<LoadStudyForm onSubmit={vi.fn()} />);

    // Two fields called "Notes" would read alike to a screen reader and in a
    // validation message, so the study-level one carries its own words.
    expect(within(studyFieldset()).getByLabelText("Study notes")).toBeInTheDocument();
    expect(within(studyFieldset()).queryByLabelText("Notes")).not.toBeInTheDocument();
    expect(within(loadRow(1)).getByLabelText("Notes")).toBeInTheDocument();
    expect(screen.getAllByLabelText(/otes$/)).toHaveLength(2);
  });

  it("adds a load, makes both removable, and moves the cursor to the new row", () => {
    render(<LoadStudyForm onSubmit={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: "Add load" }));

    expect(rows()).toHaveLength(2);
    expect(within(loadRow(1)).getByRole("button", { name: "Remove load 1" })).toBeInTheDocument();
    expect(within(loadRow(2)).getByRole("button", { name: "Remove load 2" })).toBeInTheDocument();
    // The new row is below a long form, so the cursor goes there.
    expect(within(loadRow(2)).getByLabelText("Load code")).toHaveFocus();
  });

  it("hides the remove button again when one load is left", () => {
    render(<LoadStudyForm onSubmit={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Add load" }));

    fireEvent.click(within(loadRow(2)).getByRole("button", { name: "Remove load 2" }));

    expect(rows()).toHaveLength(1);
    expect(
      within(loadRow(1)).queryByRole("button", { name: "Remove load 1" }),
    ).not.toBeInTheDocument();
  });

  it("removes the row the button names, not the last one", () => {
    render(<LoadStudyForm onSubmit={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Add load" }));
    type(loadRow(1), "Load code", "FIRST");
    type(loadRow(2), "Load code", "SECOND");

    fireEvent.click(within(loadRow(1)).getByRole("button", { name: "Remove load 1" }));

    expect(rows()).toHaveLength(1);
    expect(within(loadRow(1)).getByLabelText("Load code")).toHaveValue("SECOND");
  });

  it("names the missing study field and calculates nothing", () => {
    const onSubmit = vi.fn();
    render(<LoadStudyForm onSubmit={onSubmit} />);

    submit();

    expect(screen.getByRole("alert")).toHaveTextContent("Study code is required.");
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("names the row and the field when an AC load has no power factor", () => {
    const onSubmit = vi.fn();
    render(<LoadStudyForm onSubmit={onSubmit} />);
    fillStudy();
    fillThreePhaseRow(1, "MTR-001", false);

    submit();

    expect(screen.getByRole("alert")).toHaveTextContent("Load 1 — Power factor is required.");
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("sends a two-row schedule without the blank factors and without a project", async () => {
    const onSubmit = vi.fn();
    render(<LoadStudyForm onSubmit={onSubmit} />);
    fillStudy();
    type(studyFieldset(), "Coincidence factor", "0.90");
    fillThreePhaseRow(1, "MTR-001", true);
    fireEvent.click(screen.getByRole("button", { name: "Add load" }));
    fillDcRow(2, "DC-001");

    submit();

    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(onSubmit).toHaveBeenCalledTimes(1);

    const payload = onSubmit.mock.calls[0][0];
    const study = payload.study;
    expect(study.code).toBe("LOAD-001");
    expect(study.coincidence_factor).toBe("0.90");
    expect(study.jurisdiction_profile).toBe("IN");
    expect(study.loads).toHaveLength(2);
    expect(study.loads[0].power_factor).toBe("0.85");
    expect(study.loads[0].quantity).toBe(2);

    // A15 (a): the DC row's blank factors are absent, not "1"; a DC load also
    // carries no power factor at all.
    for (const key of ["power_factor", "efficiency", "utilization_factor", "demand_factor"]) {
      expect(Object.keys(study.loads[1])).not.toContain(key);
    }
    // The page adds the project revision when it calls the API (commit 14).
    expect(Object.keys(payload)).not.toContain("project_revision_id");
  });

  it("leaves the coincidence factor out when it is not established", () => {
    const onSubmit = vi.fn();
    render(<LoadStudyForm onSubmit={onSubmit} />);
    fillStudy();
    fillThreePhaseRow(1, "MTR-001", true);

    submit();

    expect(onSubmit).toHaveBeenCalledTimes(1);
    expect(Object.keys(onSubmit.mock.calls[0][0].study)).not.toContain("coincidence_factor");
  });

  it("clears an earlier message once the study is complete", () => {
    const onSubmit = vi.fn();
    render(<LoadStudyForm onSubmit={onSubmit} />);

    submit();
    expect(screen.getByRole("alert")).toBeInTheDocument();

    fillStudy();
    fillThreePhaseRow(1, "MTR-001", true);
    submit();

    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("is fully disabled while a calculation is running", () => {
    render(<LoadStudyForm disabled onSubmit={vi.fn()} />);

    expect(screen.getByRole("button", { name: "Calculate load study" })).toBeDisabled();
    expect(within(studyFieldset()).getByLabelText("Study code")).toBeDisabled();
    expect(within(loadRow(1)).getByLabelText("Load code")).toBeDisabled();
    expect(screen.getByRole("button", { name: "Add load" })).toBeDisabled();
  });
});
