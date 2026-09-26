// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import type { PropsWithChildren } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AuthContext, type AuthContextValue } from "../app/authContext";
import type { Session } from "../services/auth";
import type { ShortCircuitStudyRequest } from "../services/fault";
import { FaultStudyForm } from "./FaultStudyForm";
import {
  createInitialFaultStudyDraft,
  createRowId,
  faultStudyDraftSchema,
} from "./faultStudyDraft";

const USER_ID = "7d1f3a52-4a8e-4f0b-9c61-2b0f8e4d5a10";
const DRAFT_KEY = `keos:draft:v1:${USER_ID}:fault-study`;

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
  return render(<FaultStudyForm onSubmit={vi.fn()} />, { wrapper: SignedIn });
}

function restoreNotice(): HTMLElement | null {
  return screen.queryByText("Draft restored from this session.");
}

function storedDraft(): Record<string, unknown> | null {
  return JSON.parse(window.sessionStorage.getItem(DRAFT_KEY) ?? "null");
}

// The text of the option a select shows, so a link is checked as the user sees it.
function shown(label: string, scope: HTMLElement = document.body): string | null {
  const select = within(scope).getByLabelText(label) as HTMLSelectElement;
  return select.selectedOptions[0]?.textContent ?? null;
}

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

// SC-NET-01: bus 1 with the source, a cable to bus 2, the fault at bus 2.
function fillTwoBusNetwork() {
  fillBaseStudy();
  change("Study code", "SC-NET-01");
  fillImpedanceSource();
  fireEvent.click(screen.getByRole("button", { name: "Add bus" }));
  change("Bus code", "DB-01", group("Bus 2"));
  change("Nominal voltage (V)", "415", group("Bus 2"));
  fireEvent.click(screen.getByRole("button", { name: "Add branch" }));
  const feeder = group("Branch 1");
  change("Branch code", "CBL-01", feeder);
  choose("From bus", "Bus 1 — BUS-1", feeder);
  choose("To bus", "Bus 2 — DB-01", feeder);
  change("Branch type", "CABLE", feeder);
  change("Positive-sequence resistance (Ω)", "0.0124", feeder);
  choose("Fault at bus", "Bus 2 — DB-01");
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

describe("the FaultStudyForm draft", () => {
  it("comes back with every row and every link after the page is left and opened again", () => {
    const first = renderSignedIn();
    fillTwoBusNetwork();
    first.unmount();

    renderSignedIn();

    expect(restoreNotice()).toHaveAttribute("role", "status");
    expect(screen.getByLabelText("Study code")).toHaveValue("SC-NET-01");
    expect(within(group("Bus 2")).getByLabelText("Bus code")).toHaveValue("DB-01");
    expect(shown("Connected bus", group("Source 1"))).toBe("Bus 1 — BUS-1");
    expect(shown("From bus", group("Branch 1"))).toBe("Bus 1 — BUS-1");
    expect(shown("To bus", group("Branch 1"))).toBe("Bus 2 — DB-01");
    expect(within(group("Branch 1")).getByLabelText("Positive-sequence resistance (Ω)")).toHaveValue(
      "0.0124",
    );
    expect(shown("Fault at bus")).toBe("Bus 2 — DB-01");
  });

  it("keeps the rules of the form after a restore", () => {
    const first = renderSignedIn();
    fillTwoBusNetwork();
    first.unmount();
    renderSignedIn();

    fireEvent.click(screen.getByRole("button", { name: "Remove bus 2" }));

    // The fault moves to the only bus left, and the last bus and source stay.
    expect(shown("Fault at bus")).toBe("Bus 1 — BUS-1");
    expect(screen.queryByRole("button", { name: /^Remove bus/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^Remove source/ })).not.toBeInTheDocument();
  });

  it("clears every link to a removed bus, so the draft stays valid and still comes back", () => {
    const first = renderSignedIn();
    fillTwoBusNetwork();
    fireEvent.click(screen.getByRole("button", { name: "Add bus" }));
    change("Bus code", "DB-02", group("Bus 3"));
    choose("Connected bus", "Bus 2 — DB-01", group("Source 1"));

    fireEvent.click(screen.getByRole("button", { name: "Remove bus 2" }));

    expect(within(group("Branch 1")).getByLabelText("To bus")).toHaveValue("");
    expect(within(group("Source 1")).getByLabelText("Connected bus")).toHaveValue("");
    expect(shown("From bus", group("Branch 1"))).toBe("Bus 1 — BUS-1");
    expect(faultStudyDraftSchema.safeParse(storedDraft()).success).toBe(true);

    first.unmount();
    renderSignedIn();

    expect(restoreNotice()).toBeInTheDocument();
    expect(screen.getByLabelText("Study code")).toHaveValue("SC-NET-01");
    expect(within(group("Branch 1")).getByLabelText("Branch code")).toHaveValue("CBL-01");
    expect(within(group("Branch 1")).getByLabelText("To bus")).toHaveValue("");
  });

  it("drops the notice at the first edit", () => {
    const first = renderSignedIn();
    fillTwoBusNetwork();
    first.unmount();
    renderSignedIn();

    change("Frequency (Hz)", "50");

    expect(restoreNotice()).not.toBeInTheDocument();
    expect(storedDraft()).toMatchObject({ frequencyHz: "50" });
  });

  it("goes back to the single-bus study and forgets the draft on Clear form", () => {
    renderSignedIn();
    fillTwoBusNetwork();
    expect(storedDraft()).not.toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "Clear form" }));

    expect(screen.getByLabelText("Study code")).toHaveValue("");
    expect(group("Bus 1")).toBeInTheDocument();
    expect(screen.queryByRole("group", { name: "Bus 2" })).not.toBeInTheDocument();
    expect(screen.queryByRole("group", { name: "Branch 1" })).not.toBeInTheDocument();
    expect(screen.getByLabelText("Connected bus")).toHaveValue(
      (screen.getByLabelText("Fault at bus") as HTMLSelectElement).value,
    );
    expect(window.sessionStorage.getItem(DRAFT_KEY)).toBeNull();
  });

  it("ignores a stored draft of another shape", () => {
    window.sessionStorage.setItem(DRAFT_KEY, JSON.stringify({ studyCode: "OLD", buses: "BUS-1" }));

    renderSignedIn();

    expect(screen.getByLabelText("Study code")).toHaveValue("");
    expect(restoreNotice()).not.toBeInTheDocument();
    expect(window.sessionStorage.getItem(DRAFT_KEY)).toBeNull();
  });

  it("ignores a stored draft whose source points at a bus it does not have", () => {
    const draft = createInitialFaultStudyDraft();
    const broken = {
      ...draft,
      studyCode: "BROKEN",
      sources: [{ ...draft.sources[0]!, busId: "bus-999999" }],
    };
    window.sessionStorage.setItem(DRAFT_KEY, JSON.stringify(broken));

    renderSignedIn();

    expect(screen.getByLabelText("Study code")).toHaveValue("");
    expect(restoreNotice()).not.toBeInTheDocument();
  });

  it("gives rows added after a restore ids no restored row has", () => {
    // The ids the counter would hand out next are exactly the ones the stored draft uses.
    const next = Number(createRowId("bus").replace("bus-", "")) + 1;
    const draft = createInitialFaultStudyDraft();
    const busId = `bus-${next}`;
    const stored = {
      ...draft,
      faultBusId: busId,
      buses: [{ ...draft.buses[0]!, id: busId }],
      sources: [{ ...draft.sources[0]!, id: `source-${next + 1}`, busId }],
    };
    window.sessionStorage.setItem(DRAFT_KEY, JSON.stringify(stored));
    renderSignedIn();

    fireEvent.click(screen.getByRole("button", { name: "Add bus" }));
    fireEvent.click(screen.getByRole("button", { name: "Add source" }));
    fireEvent.click(screen.getByRole("button", { name: "Add branch" }));

    const saved = storedDraft() as {
      buses: { id: string }[];
      sources: { id: string }[];
      branches: { id: string }[];
    };
    const ids = [...saved.buses, ...saved.sources, ...saved.branches].map((row) => row.id);
    expect(ids).toHaveLength(5);
    expect(new Set(ids).size).toBe(5);
  });

  it("stores nothing while nobody is signed in", () => {
    render(<FaultStudyForm onSubmit={vi.fn()} />);

    fillTwoBusNetwork();

    expect(window.sessionStorage.length).toBe(0);
  });

  it("is disabled like the rest of the form while a calculation is running", () => {
    render(<FaultStudyForm disabled onSubmit={vi.fn()} />, { wrapper: SignedIn });

    expect(screen.getByRole("button", { name: "Clear form" })).toBeDisabled();
  });
});
