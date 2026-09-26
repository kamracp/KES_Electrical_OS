// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import type { PropsWithChildren } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AuthContext, type AuthContextValue } from "../app/authContext";
import type { Session } from "../services/auth";
import { LoadStudyForm } from "./LoadStudyForm";
import { createLoadRowDraft, createRowId } from "./loadStudyDraft";

const USER_ID = "7d1f3a52-4a8e-4f0b-9c61-2b0f8e4d5a10";
const DRAFT_KEY = `keos:draft:v1:${USER_ID}:load-demand`;

afterEach(() => {
  cleanup();
  window.sessionStorage.clear();
});

// A signed-in user, so the form keeps its draft in the tab's storage.
function SignedIn({ children }: PropsWithChildren) {
  const session = {
    user: {
      id: USER_ID,
      email: "engineer@example.com",
      full_name: "Test Engineer",
      must_change_password: false,
    },
    organization: { id: "c1b7f1de-32a4-4c0b-8a4e-3f1f2a9d5b22", code: "KES", name: "KES Works" },
    role: "ENGINEER",
    session_expires_at: "2026-09-27T10:00:00Z",
    idle_timeout_minutes: 720,
  } as Session;
  const auth: AuthContextValue = {
    state: { status: "signed-in", session },
    signIn: vi.fn(),
    signOut: vi.fn(),
    refresh: vi.fn(),
  };
  return <AuthContext.Provider value={auth}>{children}</AuthContext.Provider>;
}

function renderSignedIn() {
  return render(<LoadStudyForm onSubmit={vi.fn()} />, { wrapper: SignedIn });
}

function restoreNotice(): HTMLElement | null {
  return screen.queryByText("Draft restored from this session.");
}

function storedDraft(): Record<string, unknown> | null {
  return JSON.parse(window.sessionStorage.getItem(DRAFT_KEY) ?? "null");
}

function fillTwoLoads(): void {
  fillStudy();
  fillThreePhaseRow(1, "PUMP-01", true);
  fireEvent.click(screen.getByRole("button", { name: "Add load" }));
  fillDcRow(2, "DC-01");
}

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

describe("the LoadStudyForm draft", () => {
  it("comes back after the page is left and opened again, and says so", () => {
    const first = renderSignedIn();
    fillTwoLoads();
    first.unmount();

    renderSignedIn();

    expect(rows()).toHaveLength(2);
    expect(within(studyFieldset()).getByLabelText("Study code")).toHaveValue("LOAD-001");
    expect(within(loadRow(1)).getByLabelText("Load code")).toHaveValue("PUMP-01");
    expect(within(loadRow(1)).getByLabelText("Power factor")).toHaveValue("0.85");
    expect(within(loadRow(2)).getByLabelText("Load code")).toHaveValue("DC-01");
    expect(within(loadRow(2)).getByLabelText("Phase system")).toHaveValue("DC");
    // The DC row still has no power factor to type.
    expect(within(loadRow(2)).getByLabelText("Power factor")).toBeDisabled();
    expect(restoreNotice()).toHaveAttribute("role", "status");
  });

  it("drops the notice at the first edit", () => {
    const first = renderSignedIn();
    fillTwoLoads();
    first.unmount();
    renderSignedIn();

    type(studyFieldset(), "Coincidence factor", "0.9");

    expect(restoreNotice()).not.toBeInTheDocument();
    expect(storedDraft()).toMatchObject({ coincidenceFactor: "0.9" });
  });

  it("empties the form to one blank load and forgets the draft on Clear form", () => {
    renderSignedIn();
    fillTwoLoads();
    expect(storedDraft()).not.toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "Clear form" }));

    expect(rows()).toHaveLength(1);
    expect(within(studyFieldset()).getByLabelText("Study code")).toHaveValue("");
    expect(within(loadRow(1)).getByLabelText("Load code")).toHaveValue("");
    expect(window.sessionStorage.getItem(DRAFT_KEY)).toBeNull();
  });

  it("ignores a stored draft of another shape", () => {
    window.sessionStorage.setItem(DRAFT_KEY, JSON.stringify({ code: "OLD", loads: "PUMP-01" }));

    renderSignedIn();

    expect(within(studyFieldset()).getByLabelText("Study code")).toHaveValue("");
    expect(restoreNotice()).not.toBeInTheDocument();
    expect(window.sessionStorage.getItem(DRAFT_KEY)).toBeNull();
  });

  it("gives a load added after a restore an id no restored row has", () => {
    // The ids the counter would hand out next are exactly the ones the stored draft uses.
    const next = Number(createRowId("load").replace("load-", "")) + 1;
    const restoredIds = [`load-${next}`, `load-${next + 1}`];
    const stored = {
      code: "LOAD-001",
      name: "Process Pump Loads",
      jurisdictionProfile: "IN",
      coincidenceFactor: "",
      notes: "",
      loads: restoredIds.map((id) => ({ ...createLoadRowDraft(), id })),
    };
    window.sessionStorage.setItem(DRAFT_KEY, JSON.stringify(stored));
    renderSignedIn();

    fireEvent.click(screen.getByRole("button", { name: "Add load" }));

    const ids = [...document.querySelectorAll("[data-load-row]")].map((row) =>
      row.getAttribute("data-load-row"),
    );
    expect(ids).toHaveLength(3);
    expect(new Set(ids).size).toBe(3);
    expect(restoredIds).not.toContain(ids[2]);
    expect(within(loadRow(3)).getByLabelText("Load code")).toHaveFocus();
  });

  it("stores nothing while nobody is signed in", () => {
    render(<LoadStudyForm onSubmit={vi.fn()} />);

    fillTwoLoads();

    expect(window.sessionStorage.length).toBe(0);
  });

  it("is disabled like the rest of the form while a calculation is running", () => {
    render(<LoadStudyForm disabled onSubmit={vi.fn()} />, { wrapper: SignedIn });

    expect(screen.getByRole("button", { name: "Clear form" })).toBeDisabled();
  });
});
