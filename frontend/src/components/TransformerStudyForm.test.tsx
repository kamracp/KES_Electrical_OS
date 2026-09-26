// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import type { PropsWithChildren } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AuthContext, type AuthContextValue } from "../app/authContext";
import type { Session } from "../services/auth";
import { transformerRedundancyModeSchema } from "../services/transformerSizingContract";
import {
  REDUNDANCY_HINTS,
  REDUNDANCY_LABELS,
  TransformerStudyForm,
} from "./TransformerStudyForm";
import { createRatingId } from "./transformerStudyDraft";

const USER_ID = "7d1f3a52-4a8e-4f0b-9c61-2b0f8e4d5a10";
const DRAFT_KEY = `keos:draft:v1:${USER_ID}:transformer-sizing`;

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
  return render(<TransformerStudyForm onSubmit={vi.fn()} />, { wrapper: SignedIn });
}

function restoreNotice(): HTMLElement | null {
  return screen.queryByText("Draft restored from this session.");
}

function storedDraft(): Record<string, unknown> | null {
  return JSON.parse(window.sessionStorage.getItem(DRAFT_KEY) ?? "null");
}

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

describe("the TransformerStudyForm redundancy maps", () => {
  it("name and explain every redundancy mode the contract can carry", () => {
    // Drift guard: a mode the backend adds must get an option label and a hint
    // here, not fall through as a blank option or an empty line.
    expect(Object.keys(REDUNDANCY_LABELS).sort()).toEqual(
      [...transformerRedundancyModeSchema.options].sort(),
    );
    expect(Object.keys(REDUNDANCY_HINTS).sort()).toEqual(
      [...transformerRedundancyModeSchema.options].sort(),
    );
  });
});

describe("the TransformerStudyForm draft", () => {
  it("comes back after the page is left and opened again, and says so", () => {
    const first = renderSignedIn();
    fillStudy();
    first.unmount();

    renderSignedIn();

    expect(within(group("Study definition")).getByLabelText("Study code")).toHaveValue("TR-001");
    expect(within(group("Demand")).getByLabelText("Power factor")).toHaveValue("0.80");
    expect(within(group("Unit ratings")).getByLabelText("Unit rating 1")).toHaveValue("1000");
    expect(restoreNotice()).toHaveAttribute("role", "status");
  });

  it("drops the notice at the first edit", () => {
    const first = renderSignedIn();
    fillStudy();
    first.unmount();
    renderSignedIn();

    type(group("Demand"), "Demand power (kW)", "900");

    expect(restoreNotice()).not.toBeInTheDocument();
    expect(storedDraft()).toMatchObject({ demandPowerKw: "900" });
  });

  it("empties the form and forgets the draft on Clear form", () => {
    renderSignedIn();
    fillStudy();
    expect(storedDraft()).not.toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "Clear form" }));

    expect(within(group("Study definition")).getByLabelText("Study code")).toHaveValue("");
    expect(ratingInputs()).toHaveLength(1);
    expect(within(group("Unit ratings")).getByLabelText("Unit rating 1")).toHaveValue("");
    expect(window.sessionStorage.getItem(DRAFT_KEY)).toBeNull();
  });

  it("ignores a stored draft of another shape", () => {
    window.sessionStorage.setItem(DRAFT_KEY, JSON.stringify({ code: "OLD", ratings: "1000" }));

    renderSignedIn();

    expect(within(group("Study definition")).getByLabelText("Study code")).toHaveValue("");
    expect(restoreNotice()).not.toBeInTheDocument();
    expect(window.sessionStorage.getItem(DRAFT_KEY)).toBeNull();
  });

  it("gives a rating added after a restore an id no restored entry has", () => {
    // The ids the counter would hand out next are exactly the ones the stored draft uses.
    const next = Number(createRatingId().replace("rating-", "")) + 1;
    const restoredIds = [0, 1, 2].map((offset) => `rating-${next + offset}`);
    window.sessionStorage.setItem(DRAFT_KEY, JSON.stringify(storedDraftOf(restoredIds)));
    renderSignedIn();

    fireEvent.click(screen.getByRole("button", { name: "Add rating" }));

    const ids = [...document.querySelectorAll("[data-rating-entry]")].map((entry) =>
      entry.getAttribute("data-rating-entry"),
    );
    expect(ids).toHaveLength(4);
    expect(new Set(ids).size).toBe(4);
    expect(restoredIds).not.toContain(ids[3]);
  });

  it("stores nothing while nobody is signed in", () => {
    render(<TransformerStudyForm onSubmit={vi.fn()} />);

    fillStudy();

    expect(window.sessionStorage.length).toBe(0);
  });

  it("is disabled like the rest of the form while a calculation is running", () => {
    render(<TransformerStudyForm disabled onSubmit={vi.fn()} />, { wrapper: SignedIn });

    expect(screen.getByRole("button", { name: "Clear form" })).toBeDisabled();
  });
});

function storedDraftOf(ratingIds: string[]) {
  return {
    code: "TR-001",
    name: "Main Transformer",
    demandPowerKw: "800",
    demandPowerFactor: "0.80",
    futureGrowthFactor: "",
    designMarginFactor: "",
    ambientDeratingFactor: "",
    altitudeDeratingFactor: "",
    harmonicDeratingFactor: "",
    dutyUnits: "1",
    standbyUnits: "0",
    redundancyMode: "NONE",
    scenario: "NORMAL",
    jurisdictionProfile: "IN",
    notes: "",
    unitRatings: ratingIds.map((id, index) => ({ id, value: String(1000 + index) })),
  };
}
