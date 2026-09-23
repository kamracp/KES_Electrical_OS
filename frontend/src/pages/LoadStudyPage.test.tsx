// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import type { PropsWithChildren } from "react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  ProjectContext,
  type ProjectContextValue,
  type ProjectState,
} from "../app/projectContext";

import type {
  LoadGroupResponse,
  LoadRunCreateRequest,
  LoadRunResponse,
} from "../services/loadDemand";
import { LoadStudyPage } from "./LoadStudyPage";

type CreateLoadRun = (
  payload: LoadRunCreateRequest,
  signal?: AbortSignal,
  projectRevisionId?: string,
) => Promise<LoadRunResponse>;

const createLoadRunMock = vi.hoisted(() => vi.fn<CreateLoadRun>());

// Partial mock: keep the real schemas, replace only the network call.
vi.mock("../services/loadDemand", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../services/loadDemand")>();
  return { ...actual, createLoadRun: createLoadRunMock };
});

// The full form is covered by LoadStudyForm.test.tsx; here it is replaced by a
// single button so the page wiring (submit -> hook -> panels) is what gets tested.
const fixtureRequest = {
  study: { code: "LOAD-001", name: "Fixture" },
} as unknown as LoadRunCreateRequest;

vi.mock("../components/LoadStudyForm", () => ({
  LoadStudyForm: ({
    disabled,
    onSubmit,
  }: {
    disabled?: boolean;
    onSubmit: (payload: LoadRunCreateRequest) => void | Promise<void>;
  }) => (
    <button type="button" disabled={disabled} onClick={() => void onSubmit(fixtureRequest)}>
      Submit fixture
    </button>
  ),
}));

// A schedule whose coincidence factor was not established: the state the page
// must be able to show end to end (Master Prompt A15 (a)).
const response: LoadGroupResponse = {
  group_code: "LOAD-001",
  group_name: "Process Pump Loads",
  coincidence_factor: "1",
  connected_power_kw: "32.6087",
  pre_coincidence_demand_kw: "23.4783",
  demand_power_kw: "23.4783",
  apparent_power_kva: "27.6215",
  reactive_power_kvar: "14.5505",
  load_results: [
    {
      load_code: "MTR-001",
      load_name: "Process Water Pump",
      scenario: "NORMAL",
      phase_system: "THREE_PHASE",
      connected_power_kw: "32.6087",
      utilized_power_kw: "26.0870",
      demand_power_kw: "23.4783",
      apparent_power_kva: "27.6215",
      reactive_power_kvar: "14.5505",
      design_current_a: "38.4272",
      status: "VALID",
      warnings: [],
    },
  ],
  status: "REVIEW_REQUIRED",
  warnings: [
    {
      code: "COINCIDENCE_FACTOR_NOT_ESTABLISHED",
      message:
        "Group coincidence factor is not established; the calculation used 1. " +
        "The engineer must establish this factor.",
    },
  ],
  assumptions: ["The group coincidence factor is applied equally to active and reactive demand."],
  jurisdiction_profile: "IN",
};

const sampleRun: LoadRunResponse["run"] = {
  id: "48a782d0-4331-4aa2-bcd0-f24f5016334a",
  module_code: "EOS-02",
  project_revision_id: null,
  project: null,
  calculation_type: "LOAD_DEMAND",
  calculation_key: "LOAD-001",
  revision_number: 1,
  run_status: "COMPLETED",
  approval_status: "NOT_SUBMITTED",
  engine_version: "load-engine 0.1.0",
  design_check_status: "REVIEW_REQUIRED",
  jurisdiction_profile: "IN",
  reference_verification_status: "UNVERIFIED",
  content_hash: "e2805d5d7ba2e2805d5d7ba2e2805d5d7ba2e2805d5d7ba2e2805d5d7ba2e280",
  calculated_by: null,
  calculated_at: "2026-09-23T12:00:00+00:00",
  created_at: "2026-09-23T12:00:00+00:00",
  is_immutable: false,
  supersedes_run_id: null,
  notes: null,
};

const runResponse: LoadRunResponse = { run: sampleRun, result: response };

// The study pages read the chosen project from the provider; these tests run with
// no project unless they say otherwise.
function workingIn(state: ProjectState): ProjectContextValue {
  return {
    state,
    select: vi.fn(),
    clear: vi.fn(),
    activeRevisionId: () => (state.status === "selected" ? state.revision.id : null),
  };
}

const NO_PROJECT = workingIn({ status: "none" });

function createWrapper(project: ProjectContextValue = NO_PROJECT) {
  const queryClient = new QueryClient({
    defaultOptions: { mutations: { retry: false } },
  });
  return function Wrapper({ children }: PropsWithChildren) {
    return (
      <QueryClientProvider client={queryClient}>
        <ProjectContext.Provider value={project}>
          <MemoryRouter>{children}</MemoryRouter>
        </ProjectContext.Provider>
      </QueryClientProvider>
    );
  };
}

beforeEach(() => {
  createLoadRunMock.mockReset();
});

afterEach(() => {
  cleanup();
});

// True when `first` comes before `second` in document order.
function precedes(first: Node | null, second: Node | null): boolean {
  if (!first || !second) {
    return false;
  }
  return (first.compareDocumentPosition(second) & Node.DOCUMENT_POSITION_FOLLOWING) !== 0;
}

function successState(): Element | null {
  return document.querySelector('[data-calculation-state="success"]');
}

describe("LoadStudyPage", () => {
  it("renders the EOS-02 workspace in the idle state", () => {
    render(<LoadStudyPage />, { wrapper: createWrapper() });

    expect(
      screen.getByRole("heading", { level: 1, name: "Load and demand" }),
    ).toBeInTheDocument();
    expect(screen.getByText("EOS-02 · Load & Demand")).toBeInTheDocument();
    expect(document.querySelector("[data-load-study-page]")).not.toBeNull();
    expect(document.querySelector('[data-calculation-state="idle"]')).not.toBeNull();
    expect(screen.getByText(/not an automatic compliance declaration/i)).toBeInTheDocument();
    expect(screen.queryByRole("article")).toBeNull();
  });

  it("names the project a run would be saved in", () => {
    render(<LoadStudyPage />, { wrapper: createWrapper() });

    expect(document.querySelector("[data-study-project]")).not.toBeNull();
  });

  it("runs the study, renders the result panels, and clears back to idle", async () => {
    createLoadRunMock.mockResolvedValue(runResponse);
    render(<LoadStudyPage />, { wrapper: createWrapper() });

    fireEvent.click(screen.getByRole("button", { name: "Submit fixture" }));

    await waitFor(() => expect(successState()).not.toBeNull());
    expect(createLoadRunMock).toHaveBeenCalledTimes(1);
    expect(createLoadRunMock.mock.calls[0]?.[0]).toBe(fixtureRequest);

    const article = screen.getByRole("article", { name: "Load study result" });
    expect(within(article).getByText("Engineering review required")).toHaveAttribute(
      "data-result-status",
      "REVIEW_REQUIRED",
    );
    const summary = screen.getByRole("region", { name: "Result summary" });
    expect(within(summary).getByText("Engineering review required")).toHaveAttribute(
      "data-summary-status",
      "REVIEW_REQUIRED",
    );
    expect(
      document.querySelector('[data-warning-code="COINCIDENCE_FACTOR_NOT_ESTABLISHED"]'),
    ).not.toBeNull();
    // The unestablished factor is readable on the page, not only in the code.
    expect(within(article).getByText(/1 \(not established\)/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Clear results" }));

    await waitFor(() =>
      expect(document.querySelector('[data-calculation-state="idle"]')).not.toBeNull(),
    );
    expect(screen.queryByRole("article")).toBeNull();
  });

  it("surfaces a service error as an alert without a result panel", async () => {
    createLoadRunMock.mockRejectedValue(
      new Error("The study's jurisdiction profile must match the project's."),
    );
    render(<LoadStudyPage />, { wrapper: createWrapper() });

    fireEvent.click(screen.getByRole("button", { name: "Submit fixture" }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveAttribute("data-calculation-state", "error");
    expect(alert.textContent).toContain("jurisdiction profile must match");
    expect(screen.queryByRole("article")).toBeNull();
  });

  it("opens with the inputs expanded inside a collapsible block", () => {
    render(<LoadStudyPage />, { wrapper: createWrapper() });

    const inputs = document.getElementById("load-study-inputs-heading")?.closest("details");
    expect(inputs).toHaveAttribute("data-study-inputs");
    expect(inputs).toHaveAttribute("open");
    expect(inputs).toContainElement(screen.getByRole("button", { name: "Submit fixture" }));
  });

  it("orders the result column as summary, warnings, traceability, then detail", async () => {
    createLoadRunMock.mockResolvedValue(runResponse);
    render(<LoadStudyPage />, { wrapper: createWrapper() });

    fireEvent.click(screen.getByRole("button", { name: "Submit fixture" }));

    await waitFor(() => expect(successState()).not.toBeNull());
    const summary = screen.getByRole("region", { name: "Result summary" });
    const warning = document.querySelector(
      '[data-warning-code="COINCIDENCE_FACTOR_NOT_ESTABLISHED"]',
    );
    const traceability = screen.getByRole("region", { name: "Traceability" });
    const detail = screen.getByRole("article", { name: "Load study result" });

    expect(precedes(summary, warning)).toBe(true);
    expect(precedes(warning, traceability)).toBe(true);
    expect(precedes(traceability, detail)).toBe(true);
  });

  it("shows the persisted run in the traceability panel and exports it as JSON", async () => {
    createLoadRunMock.mockResolvedValue(runResponse);
    render(<LoadStudyPage />, { wrapper: createWrapper() });

    fireEvent.click(screen.getByRole("button", { name: "Submit fixture" }));

    await waitFor(() => expect(successState()).not.toBeNull());
    const traceability = screen.getByRole("region", { name: "Traceability" });
    expect(traceability).toHaveAttribute("data-run-id", sampleRun.id);
    expect(within(traceability).getByText(sampleRun.id)).toBeInTheDocument();
    expect(within(traceability).getByText("load-engine 0.1.0")).toBeInTheDocument();

    // Intercept the generated download link: proves the export fired, records the
    // file name and keeps jsdom from attempting a real navigation.
    const downloads: string[] = [];
    const anchorClick = vi
      .spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(function (this: HTMLAnchorElement) {
        downloads.push(this.download);
      });
    fireEvent.click(within(traceability).getByRole("button", { name: "Download run JSON" }));
    expect(anchorClick).toHaveBeenCalledTimes(1);
    expect(downloads).toEqual(["LOAD-001-rev1.json"]);
    anchorClick.mockRestore();
    expect(successState()).not.toBeNull();
  });

  it("keeps the wide per-load table in its own scroll container", async () => {
    createLoadRunMock.mockResolvedValue(runResponse);
    render(<LoadStudyPage />, { wrapper: createWrapper() });

    fireEvent.click(screen.getByRole("button", { name: "Submit fixture" }));

    await waitFor(() => expect(successState()).not.toBeNull());
    const loads = screen.getByRole("region", { name: "Loads" });
    expect(loads.querySelector("[data-table-scroll] table")).not.toBeNull();
  });

  it("disables the form while the calculation is running", async () => {
    createLoadRunMock.mockImplementation(() => new Promise<LoadRunResponse>(() => {}));
    render(<LoadStudyPage />, { wrapper: createWrapper() });

    fireEvent.click(screen.getByRole("button", { name: "Submit fixture" }));

    await waitFor(() =>
      expect(document.querySelector('[data-calculation-state="pending"]')).not.toBeNull(),
    );
    expect(screen.getByRole("button", { name: "Submit fixture" })).toBeDisabled();
  });
});
