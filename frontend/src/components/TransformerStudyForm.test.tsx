// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { TransformerStudyForm } from "./TransformerStudyForm";

afterEach(() => {
  cleanup();
});

function group(name: string): HTMLElement {
  return screen.getByRole("group", { name });
}

function type(scope: HTMLElement, label: string, value: string): void {
  fireEvent.change(within(scope).getByLabelText(label), { target: { value } });
}

function ratingInputs(): HTMLElement[] {
  return within(group("Unit ratings")).getAllByRole("textbox");
}

function fillStudy(): void {
  type(group("Study definition"), "Study code", "TR-001");
  type(group("Study definition"), "Study name", "Main Transformer");
  type(group("Demand"), "Demand power (kW)", "800");
  type(group("Demand"), "Power factor", "0.80");
  type(group("Unit ratings"), "Unit rating 1", "1000");
}

function submit(): void {
  fireEvent.click(screen.getByRole("button", { name: "Calculate transformer size" }));
}

describe("TransformerStudyForm", () => {
  it("starts with one rating entry that cannot be removed", () => {
    render(<TransformerStudyForm onSubmit={vi.fn()} />);

    expect(ratingInputs()).toHaveLength(1);
    expect(
      within(group("Unit ratings")).queryByRole("button", { name: "Remove rating 1" }),
    ).not.toBeInTheDocument();
    expect(document.querySelector("[data-ratings-hint]")).toHaveTextContent(
      "in ascending order",
    );
    expect(document.querySelector("[data-not-established-hint]")).toHaveTextContent(
      "Engineering review required",
    );
    expect(within(group("Study definition")).getByLabelText("Jurisdiction profile")).toHaveValue(
      "IN",
    );
  });

  it("adds a rating entry, makes both removable, and moves the cursor to it", () => {
    render(<TransformerStudyForm onSubmit={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: "Add rating" }));

    expect(ratingInputs()).toHaveLength(2);
    expect(
      within(group("Unit ratings")).getByRole("button", { name: "Remove rating 1" }),
    ).toBeInTheDocument();
    expect(within(group("Unit ratings")).getByLabelText("Unit rating 2")).toHaveFocus();
  });

  it("removes the entry the button names and hides Remove at one entry", () => {
    render(<TransformerStudyForm onSubmit={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Add rating" }));
    type(group("Unit ratings"), "Unit rating 1", "FIRST");
    type(group("Unit ratings"), "Unit rating 2", "SECOND");

    fireEvent.click(screen.getByRole("button", { name: "Remove rating 1" }));

    expect(ratingInputs()).toHaveLength(1);
    expect(within(group("Unit ratings")).getByLabelText("Unit rating 1")).toHaveValue("SECOND");
    expect(
      within(group("Unit ratings")).queryByRole("button", { name: "Remove rating 1" }),
    ).not.toBeInTheDocument();
  });

  it("names the missing study field and calculates nothing", () => {
    const onSubmit = vi.fn();
    render(<TransformerStudyForm onSubmit={onSubmit} />);

    submit();

    expect(screen.getByRole("alert")).toHaveTextContent("Study code is required.");
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("names the power factor when it is left out", () => {
    const onSubmit = vi.fn();
    render(<TransformerStudyForm onSubmit={onSubmit} />);
    fillStudy();
    type(group("Demand"), "Power factor", "");

    submit();

    expect(screen.getByRole("alert")).toHaveTextContent("Power factor is required.");
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("names a blank rating entry by its position on screen", () => {
    const onSubmit = vi.fn();
    render(<TransformerStudyForm onSubmit={onSubmit} />);
    fillStudy();
    fireEvent.click(screen.getByRole("button", { name: "Add rating" }));
    fireEvent.click(screen.getByRole("button", { name: "Add rating" }));
    type(group("Unit ratings"), "Unit rating 3", "1250");

    submit();

    // Entry 2 was left blank; the message names 2, not 3.
    expect(screen.getByRole("alert")).toHaveTextContent("Unit rating 2 is required.");
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("derives the standby count from the redundancy mode", () => {
    render(<TransformerStudyForm onSubmit={vi.fn()} />);
    const units = group("Units and redundancy");

    expect(within(units).getByLabelText("Standby units")).toHaveValue("0");
    expect(document.querySelector("[data-standby-hint]")).toHaveTextContent("None");

    type(units, "Redundancy mode", "N_PLUS_1");
    expect(within(units).getByLabelText("Standby units")).toHaveValue("1");
    expect(document.querySelector("[data-standby-hint]")).toHaveTextContent("N+1");

    type(units, "Redundancy mode", "TWO_N");
    expect(within(units).getByLabelText("Standby units")).toHaveValue("1");
    expect(document.querySelector("[data-standby-hint]")).toHaveTextContent(
      "2N: equal to duty units.",
    );
  });

  it("follows the duty units while 2N is chosen", () => {
    render(<TransformerStudyForm onSubmit={vi.fn()} />);
    const units = group("Units and redundancy");

    type(units, "Redundancy mode", "TWO_N");
    type(units, "Duty units", "3");

    expect(within(units).getByLabelText("Standby units")).toHaveValue("3");
  });

  it("does not let the engineer type the standby count", () => {
    render(<TransformerStudyForm onSubmit={vi.fn()} />);

    // The backend refuses any other combination, so the form shows the rule
    // instead of asking for it.
    expect(within(group("Units and redundancy")).getByLabelText("Standby units")).toHaveAttribute(
      "readonly",
    );
  });

  it("sends a complete study without the blank factors and without a project", () => {
    const onSubmit = vi.fn();
    render(<TransformerStudyForm onSubmit={onSubmit} />);
    fillStudy();
    type(group("Factors"), "Design margin factor", "1.10");
    fireEvent.click(screen.getByRole("button", { name: "Add rating" }));
    type(group("Unit ratings"), "Unit rating 2", "1250");
    type(group("Units and redundancy"), "Redundancy mode", "N_PLUS_1");

    submit();

    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(onSubmit).toHaveBeenCalledTimes(1);

    const payload = onSubmit.mock.calls[0][0];
    const study = payload.study;
    expect(study.code).toBe("TR-001");
    expect(study.demand_power_factor).toBe("0.80");
    expect(study.design_margin_factor).toBe("1.10");
    expect(study.available_unit_ratings_kva).toEqual(["1000", "1250"]);
    expect(study.duty_units).toBe(1);
    expect(study.standby_units).toBe(1);
    expect(study.redundancy_mode).toBe("N_PLUS_1");
    expect(study.jurisdiction_profile).toBe("IN");

    // A16 (a): a blank factor is absent, not "1".
    for (const key of [
      "future_growth_factor",
      "ambient_derating_factor",
      "altitude_derating_factor",
      "harmonic_derating_factor",
    ]) {
      expect(Object.keys(study)).not.toContain(key);
    }
    // The page adds the project revision when it calls the API.
    expect(Object.keys(payload)).not.toContain("project_revision_id");
  });

  it("clears an earlier message once the study is complete", () => {
    render(<TransformerStudyForm onSubmit={vi.fn()} />);

    submit();
    expect(screen.getByRole("alert")).toBeInTheDocument();

    fillStudy();
    submit();

    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("is fully disabled while a calculation is running", () => {
    render(<TransformerStudyForm disabled onSubmit={vi.fn()} />);

    expect(
      screen.getByRole("button", { name: "Calculate transformer size" }),
    ).toBeDisabled();
    expect(within(group("Study definition")).getByLabelText("Study code")).toBeDisabled();
    expect(within(group("Demand")).getByLabelText("Power factor")).toBeDisabled();
    expect(within(group("Unit ratings")).getByLabelText("Unit rating 1")).toBeDisabled();
    expect(screen.getByRole("button", { name: "Add rating" })).toBeDisabled();
  });
});
