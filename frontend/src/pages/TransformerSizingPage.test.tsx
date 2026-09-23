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
  TransformerSizingResponse,
  TransformerRunCreateRequest,
  TransformerRunResponse,
} from "../services/transformerSizing";
import { TransformerSizingPage } from "./TransformerSizingPage";

type CreateTransformerRun = (
  payload: TransformerRunCreateRequest,
  signal?: AbortSignal,
  projectRevisionId?: string,
) => Promise<TransformerRunResponse>;

const createTransformerRunMock = vi.hoisted(() => vi.fn<CreateTransformerRun>());

// Partial mock: keep the real schemas, replace only the network call.
vi.mock("../services/transformerSizing", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../services/transformerSizing")>();
  return { ...actual, createTransformerRun: createTransformerRunMock };
});

// The full form is covered by TransformerStudyForm.test.tsx; here it is replaced by a
// single button so the page wiring (submit -> hook -> panels) is what gets tested.
const fixtureRequest = {
  study: {
    code: "TR-001",
    name: "Main Transformer",
    demand_power_kw: "800",
    demand_power_factor: "0.80",
    available_unit_ratings_kva: ["1000", "1250"],
  },
} as unknown as TransformerRunCreateRequest;

vi.mock("../components/TransformerStudyForm", () => ({
  TransformerStudyForm: ({
    disabled,
    onSubmit,
  }: {
    disabled?: boolean;
    onSubmit: (payload: TransformerRunCreateRequest) => void | Promise<void>;
  }) => (
    <button type="button" disabled={disabled} onClick={() => void onSubmit(fixtureRequest)}>
      Submit fixture
    </button>
  ),
}));

// A sizing whose design margin was not established: the state the page must be
// able to show end to end (Master Prompt A16 (a)).
const response: TransformerSizingResponse = {
  code: "TR-001",
  name: "Main Transformer",
  scenario: "NORMAL",
  redundancy_mode: "NONE",
  demand_power_kw: "800",
  demand_power_factor: "1",
  base_demand_kva: "800.0000",
  future_growth_factor: "1",
  future_demand_kva: "800.0000",
  design_margin_factor: "1",
  design_required_kva: "800.0000",
  combined_derating_factor: "1.0000",
  required_nameplate_capacity_kva: "800.0000",
  duty_units: 1,
  standby_units: 0,
  total_units: 1,
  required_unit_rating_kva: "800.0000",
  selected_unit_rating_kva: "1000",
  installed_nameplate_capacity_kva: "1000.0000",
  derated_duty_capacity_kva: "1000.0000",
  spare_derated_capacity_kva: "200.0000",
  loading_percent: "80.0000",
  status: "REVIEW_REQUIRED",
  warnings: [
    {
      code: "DESIGN_MARGIN_NOT_ESTABLISHED",
      message:
        "Design margin factor is not established; the calculation used 1. " +
        "The engineer must establish this factor.",
    },
  ],
  jurisdiction_profile: "IN",
};

// No rating in the schedule is big enough: still a run, still a result.
const noSolution: TransformerSizingResponse = {
  ...response,
  selected_unit_rating_kva: null,
  installed_nameplate_capacity_kva: null,
  derated_duty_capacity_kva: null,
  spare_derated_capacity_kva: null,
  loading_percent: null,
  status: "NO_SOLUTION",
  warnings: [
    {
      code: "NO_STANDARD_RATING_AVAILABLE",
      message: "No available transformer unit rating satisfies the requirement.",
    },
  ],
};

const sampleRun: TransformerRunResponse["run"] = {
  id: "48a782d0-4331-4aa2-bcd0-f24f5016334a",
  module_code: "EOS-03",
  project_revision_id: null,
  project: null,
  calculation_type: "TRANSFORMER_SIZING",
  calculation_key: "TR-001",
  revision_number: 1,
  run_status: "COMPLETED",
  approval_status: "NOT_SUBMITTED",
  engine_version: "transformer-engine 0.1.0",
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

const runResponse: TransformerRunResponse = { run: sampleRun, result: response };

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
  createTransformerRunMock.mockReset();
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

describe("TransformerSizingPage", () => {
  it("renders the EOS-03 workspace in the idle state", () => {
    render(<TransformerSizingPage />, { wrapper: createWrapper() });

    expect(
      screen.getByRole("heading", { level: 1, name: "Transformer sizing" }),
    ).toBeInTheDocument();
    expect(screen.getByText("EOS-03 · Transformer Sizing")).toBeInTheDocument();
    expect(document.querySelector("[data-transformer-sizing-page]")).not.toBeNull();
    expect(document.querySelector('[data-calculation-state="idle"]')).not.toBeNull();
    expect(screen.getByText(/not an automatic compliance declaration/i)).toBeInTheDocument();
    expect(screen.queryByRole("article")).toBeNull();
  });

  it("names the project a run would be saved in", () => {
    render(<TransformerSizingPage />, { wrapper: createWrapper() });

    expect(document.querySelector("[data-study-project]")).not.toBeNull();
  });

  it("runs the study, renders the result panels, and clears back to idle", async () => {
    createTransformerRunMock.mockResolvedValue(runResponse);
    render(<TransformerSizingPage />, { wrapper: createWrapper() });

    fireEvent.click(screen.getByRole("button", { name: "Submit fixture" }));

    await waitFor(() => expect(successState()).not.toBeNull());
    expect(createTransformerRunMock).toHaveBeenCalledTimes(1);
    expect(createTransformerRunMock.mock.calls[0]?.[0]).toBe(fixtureRequest);

    const article = screen.getByRole("article", { name: "Transformer sizing result" });
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
      document.querySelector('[data-warning-code="DESIGN_MARGIN_NOT_ESTABLISHED"]'),
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
    createTransformerRunMock.mockRejectedValue(
      new Error("The study's jurisdiction profile must match the project's."),
    );
    render(<TransformerSizingPage />, { wrapper: createWrapper() });

    fireEvent.click(screen.getByRole("button", { name: "Submit fixture" }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveAttribute("data-calculation-state", "error");
    expect(alert.textContent).toContain("jurisdiction profile must match");
    expect(screen.queryByRole("article")).toBeNull();
  });

  it("opens with the inputs expanded inside a collapsible block", () => {
    render(<TransformerSizingPage />, { wrapper: createWrapper() });

    const inputs = document.getElementById("transformer-study-inputs-heading")?.closest("details");
    expect(inputs).toHaveAttribute("data-study-inputs");
    expect(inputs).toHaveAttribute("open");
    expect(inputs).toContainElement(screen.getByRole("button", { name: "Submit fixture" }));
  });

  it("orders the result column as summary, warnings, traceability, then detail", async () => {
    createTransformerRunMock.mockResolvedValue(runResponse);
    render(<TransformerSizingPage />, { wrapper: createWrapper() });

    fireEvent.click(screen.getByRole("button", { name: "Submit fixture" }));

    await waitFor(() => expect(successState()).not.toBeNull());
    const summary = screen.getByRole("region", { name: "Result summary" });
    const warning = document.querySelector(
      '[data-warning-code="DESIGN_MARGIN_NOT_ESTABLISHED"]',
    );
    const traceability = screen.getByRole("region", { name: "Traceability" });
    const detail = screen.getByRole("article", { name: "Transformer sizing result" });

    expect(precedes(summary, warning)).toBe(true);
    expect(precedes(warning, traceability)).toBe(true);
    expect(precedes(traceability, detail)).toBe(true);
  });

  it("shows the persisted run in the traceability panel and exports it as JSON", async () => {
    createTransformerRunMock.mockResolvedValue(runResponse);
    render(<TransformerSizingPage />, { wrapper: createWrapper() });

    fireEvent.click(screen.getByRole("button", { name: "Submit fixture" }));

    await waitFor(() => expect(successState()).not.toBeNull());
    const traceability = screen.getByRole("region", { name: "Traceability" });
    expect(traceability).toHaveAttribute("data-run-id", sampleRun.id);
    expect(within(traceability).getByText(sampleRun.id)).toBeInTheDocument();
    expect(within(traceability).getByText("transformer-engine 0.1.0")).toBeInTheDocument();

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
    expect(downloads).toEqual(["TR-001-rev1.json"]);
    anchorClick.mockRestore();
    expect(successState()).not.toBeNull();
  });

  it("keeps the result tables in their own scroll containers", async () => {
    createTransformerRunMock.mockResolvedValue(runResponse);
    render(<TransformerSizingPage />, { wrapper: createWrapper() });

    fireEvent.click(screen.getByRole("button", { name: "Submit fixture" }));

    await waitFor(() => expect(successState()).not.toBeNull());
    const tables = document.querySelectorAll("table");
    expect(tables.length).toBe(2);
    for (const table of tables) {
      expect(table.closest("[data-table-scroll]")).not.toBeNull();
    }
  });

  it("shows a no-solution sizing as a result, not as an error", async () => {
    createTransformerRunMock.mockResolvedValue({
      run: { ...sampleRun, design_check_status: "NO_SOLUTION" },
      result: noSolution,
    });
    render(<TransformerSizingPage />, { wrapper: createWrapper() });

    fireEvent.click(screen.getByRole("button", { name: "Submit fixture" }));

    await waitFor(() => expect(successState()).not.toBeNull());
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    const summary = screen.getByRole("region", { name: "Result summary" });
    expect(summary).toHaveAttribute("data-summary-tone", "fail");
    expect(summary.querySelector("[data-summary-status]")).toHaveTextContent(
      "No standard rating fits",
    );
    expect(document.querySelector("[data-no-rating]")).toHaveTextContent(
      // Four significant figures of "800.0000" is "800.0".
      "No rating in the schedule covers 800.0 kVA.",
    );
    // The run is still there: "no rating fits" is engineering evidence too.
    expect(screen.getByRole("region", { name: "Traceability" })).toBeInTheDocument();
  });

  it("disables the form while the calculation is running", async () => {
    createTransformerRunMock.mockImplementation(() => new Promise<TransformerRunResponse>(() => {}));
    render(<TransformerSizingPage />, { wrapper: createWrapper() });

    fireEvent.click(screen.getByRole("button", { name: "Submit fixture" }));

    await waitFor(() =>
      expect(document.querySelector('[data-calculation-state="pending"]')).not.toBeNull(),
    );
    expect(screen.getByRole("button", { name: "Submit fixture" })).toBeDisabled();
  });
});
