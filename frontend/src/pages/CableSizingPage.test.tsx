// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import type { PropsWithChildren } from "react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../services/http";

import {
  ProjectContext,
  type ProjectContextValue,
  type ProjectState,
} from "../app/projectContext";

import type { CableRunResponse, CableSizingRequest, CableSizingResponse } from "../services/cable";
import { CableSizingPage } from "./CableSizingPage";

const createCableRunMock = vi.hoisted(() =>
  vi.fn<
    (
      payload: CableSizingRequest,
      signal?: AbortSignal,
      projectRevisionId?: string,
    ) => Promise<CableRunResponse>
  >(),
);

// Partial mock: the form still needs the real cableSizingRequestSchema export.
vi.mock("../services/cable", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../services/cable")>();
  return { ...actual, createCableRun: createCableRunMock };
});

const response: CableSizingResponse = {
  study_code: "CBL-001",
  status: "DESIGN_CHECK_PASSED",
  conductor: {
    phase_area_mm2: "95.00",
    neutral_area_mm2: "50.00",
    protective_area_mm2: null,
    parallel_runs: 1,
    phase_conductors_per_run: 3,
    neutral_status: "PASS",
    protective_status: "NOT_APPLICABLE",
  },
  ampacity: null,
  voltage_drop: null,
  short_circuit: null,
  warnings: [
    {
      code: "HIGH_TOTAL_DERATING",
      message: "Combined derating factor is below 0.70.",
      field_name: null,
    },
  ],
  standard_reference: "IEC 60364-5-52 (UNVERIFIED)",
  ampacity_reference: "IEC 60287 (UNVERIFIED)",
  reference_source: "PROFILE",
  jurisdiction_profile: "IN",
  reference_verification_status: "UNVERIFIED",
  notes: null,
};

const sampleRun = {
  id: "48a782d0-4331-4aa2-bcd0-f24f5016334a",
  module_code: "EOS-06",
  project_revision_id: null,
  project: null,
  calculation_type: "CABLE_SIZING",
  calculation_key: "CBL-001",
  revision_number: 1,
  run_status: "COMPLETED",
  approval_status: "NOT_SUBMITTED",
  engine_version: "cable-engine 0.1.0",
  design_check_status: "DESIGN_CHECK_PASSED",
  jurisdiction_profile: "IN",
  reference_verification_status: "UNVERIFIED",
  content_hash: "e2805d5d7ba2e2805d5d7ba2e2805d5d7ba2e2805d5d7ba2e2805d5d7ba2e280",
  calculated_by: null,
  calculated_at: "2026-09-17T12:00:00+00:00",
  created_at: "2026-09-17T12:00:00+00:00",
  is_immutable: false,
  supersedes_run_id: null,
  notes: null,
};

const runResponse: CableRunResponse = { run: sampleRun, result: response };

// The study pages and hooks read the chosen project from the provider; these tests run with
// no project unless they say otherwise, so every existing expectation is unchanged.
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

function renderPage() {
  return render(<CableSizingPage />, { wrapper: createWrapper() });
}

function change(label: string, value: string) {
  fireEvent.change(screen.getByLabelText(label), { target: { value } });
}

function fillMinimumValidDraft() {
  change("Study code", "CBL-001");
  change("Study name", "Feeder to MCC-1");
  change("Design current (A)", "250");
  change("Nominal voltage (V)", "415");
  change("Route length (m)", "120.0");
  change("System", "THREE_PHASE_FOUR_WIRE");
  change("Conductor material", "COPPER");
  change("Insulation", "XLPE");
  change("Construction", "MULTICORE");
  change("Arrangement", "MULTICORE");
  change("Loaded conductors", "3");
  change("Installation method", "CABLE_TRAY");
  change("Ambient temperature (°C)", "40");
  change("Phase sizes", "70, 95, 120, 150");
}

function submit() {
  fireEvent.click(screen.getByRole("button", { name: "Calculate cable sizing" }));
}

function calculationState(): string | null | undefined {
  return document.querySelector("[data-calculation-state]")?.getAttribute("data-calculation-state");
}

// True when `first` comes before `second` in document order.
function precedes(first: Node, second: Node): boolean {
  return (first.compareDocumentPosition(second) & Node.DOCUMENT_POSITION_FOLLOWING) !== 0;
}

beforeEach(() => {
  createCableRunMock.mockReset();
});

afterEach(() => {
  cleanup();
});

const PROJECT_FIXTURE = {
  id: "2a7d5c31-9b0e-4a21-8f6c-7d8e9f0a1b2c",
  site_id: "6f1c9f1e-6a2b-4f5c-9b3d-1e2f3a4b5c6d",
  code: "PRJ-001",
  name: "Pump House",
  client_name: null,
  jurisdiction_profile: "IN",
  status: "ACTIVE",
  description: null,
  created_at: "2026-09-22T09:00:00Z",
  updated_at: "2026-09-22T09:00:00Z",
} as const;

const REVISION_FIXTURE = {
  id: "4b8e6d42-1c3f-4b5a-9e7d-8f9a0b1c2d3e",
  project_id: PROJECT_FIXTURE.id,
  revision_number: 2,
  label: "Rev 2",
  status: "OPEN",
  created_by: null,
  issued_by: null,
  issued_at: null,
  notes: null,
  created_at: "2026-09-22T09:00:00Z",
} as const;

describe("CableSizingPage", () => {
  it("renders the EOS-06 workspace, the input form, and the idle results state", () => {
    renderPage();

    expect(screen.getByRole("heading", { level: 1, name: "Cable Sizing" })).toBeInTheDocument();
    expect(screen.getByRole("form", { name: "Cable sizing inputs" })).toBeInTheDocument();
    expect(calculationState()).toBe("idle");
    expect(screen.getByRole("heading", { name: "Engineering review required" })).toBeInTheDocument();
    expect(screen.queryByRole("article", { name: "Cable sizing result" })).toBeNull();
  });

  it("locks the form while the calculation is pending, then renders result and warning panels", async () => {
    let resolveCalculation: (value: CableRunResponse) => void = () => undefined;
    createCableRunMock.mockImplementation(
      () =>
        new Promise<CableRunResponse>((resolve) => {
          resolveCalculation = resolve;
        }),
    );
    renderPage();

    fillMinimumValidDraft();
    submit();

    await waitFor(() => expect(calculationState()).toBe("pending"));
    expect(screen.getByRole("status")).toHaveTextContent("Calculating cable size");
    expect(screen.getByRole("button", { name: "Calculate cable sizing" })).toBeDisabled();
    expect(createCableRunMock).toHaveBeenCalledTimes(1);
    expect(createCableRunMock.mock.calls[0]?.[0]).toMatchObject({ code: "CBL-001" });

    resolveCalculation(runResponse);

    await waitFor(() => expect(calculationState()).toBe("success"));
    expect(screen.getByRole("article", { name: "Cable sizing result" })).toBeInTheDocument();
    const summary = screen.getByRole("region", { name: "Result summary" });
    expect(within(summary).getByText("Design check passed")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Engineering warnings" })).toHaveTextContent(
      "High total derating",
    );
    expect(screen.getByRole("button", { name: "Calculate cable sizing" })).toBeEnabled();
  });

  it("clears the results back to the idle state", async () => {
    createCableRunMock.mockResolvedValue(runResponse);
    renderPage();

    fillMinimumValidDraft();
    submit();
    await waitFor(() => expect(calculationState()).toBe("success"));

    fireEvent.click(screen.getByRole("button", { name: "Clear results" }));

    await waitFor(() => expect(calculationState()).toBe("idle"));
    expect(screen.queryByRole("article", { name: "Cable sizing result" })).toBeNull();
  });

  it("shows the service error as an alert and re-enables the form", async () => {
    createCableRunMock.mockRejectedValue(
      new Error("body.circuit.design_current_a: Input should be greater than 0"),
    );
    renderPage();

    fillMinimumValidDraft();
    submit();

    await waitFor(() => expect(calculationState()).toBe("error"));
    expect(screen.getByRole("alert")).toHaveTextContent(
      "body.circuit.design_current_a: Input should be greater than 0",
    );
    expect(screen.queryByRole("article", { name: "Cable sizing result" })).toBeNull();
    expect(screen.getByRole("button", { name: "Calculate cable sizing" })).toBeEnabled();
  });

  it("opens with the inputs expanded inside a collapsible block", () => {
    renderPage();

    const inputs = document.getElementById("cable-sizing-inputs-heading")?.closest("details");
    expect(inputs).toHaveAttribute("data-study-inputs");
    expect(inputs).toHaveAttribute("open");
    expect(inputs).toContainElement(screen.getByRole("form", { name: "Cable sizing inputs" }));
  });

  it("orders the result column as summary, warnings, traceability, then detail", async () => {
    createCableRunMock.mockResolvedValue(runResponse);
    renderPage();

    fillMinimumValidDraft();
    submit();

    await waitFor(() => expect(calculationState()).toBe("success"));
    const summary = screen.getByRole("region", { name: "Result summary" });
    const warnings = screen.getByRole("region", { name: "Engineering warnings" });
    const traceability = screen.getByRole("region", { name: "Traceability" });
    const detail = screen.getByRole("article", { name: "Cable sizing result" });

    expect(precedes(summary, warnings)).toBe(true);
    expect(precedes(warnings, traceability)).toBe(true);
    expect(precedes(traceability, detail)).toBe(true);
  });

  it("shows the persisted run in the traceability panel with a JSON export action", async () => {
    createCableRunMock.mockResolvedValue(runResponse);
    renderPage();

    fillMinimumValidDraft();
    submit();

    await waitFor(() => expect(calculationState()).toBe("success"));
    const traceability = screen.getByRole("region", { name: "Traceability" });
    expect(traceability).toHaveAttribute("data-run-id", sampleRun.id);
    expect(within(traceability).getByText(sampleRun.id)).toBeInTheDocument();
    expect(within(traceability).getByText(sampleRun.engine_version)).toBeInTheDocument();

    const exportButton = within(traceability).getByRole("button", { name: "Download run JSON" });
    expect(exportButton).toBeEnabled();
    // Intercept the generated download link: proves the export fired and keeps
    // jsdom from attempting a real navigation.
    const anchorClick = vi
      .spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(() => undefined);
    fireEvent.click(exportButton);
    expect(anchorClick).toHaveBeenCalledTimes(1);
    anchorClick.mockRestore();
    expect(calculationState()).toBe("success");
  });

  // -- the project a run is saved in (EOS-01 b) --------------------------------------------

  it("sends the chosen revision and shows the project with the result", async () => {
    const revisionId = "4b8e6d42-1c3f-4b5a-9e7d-8f9a0b1c2d3e";
    const summary = {
      revision_id: revisionId,
      revision_number: 2,
      revision_label: "Rev 2",
      project_id: "2a7d5c31-9b0e-4a21-8f6c-7d8e9f0a1b2c",
      project_code: "PRJ-001",
      project_name: "Pump House",
    };
    createCableRunMock.mockResolvedValue({
      ...runResponse,
      run: { ...runResponse.run, project_revision_id: revisionId, project: summary },
    });
    render(<CableSizingPage />, {
      wrapper: createWrapper(
        workingIn({
          status: "selected",
          project: PROJECT_FIXTURE,
          revision: REVISION_FIXTURE,
        }),
      ),
    });

    expect(screen.getByText(/Project PRJ-001 — Pump House · Rev 2 \(Open\)/)).toBeInTheDocument();

    fillMinimumValidDraft();
    submit();

    await waitFor(() => expect(calculationState()).toBe("success"));
    expect(createCableRunMock.mock.calls[0]?.[2]).toBe(revisionId);
    expect(document.querySelector('[data-field="project"]')?.textContent).toBe(
      "PRJ-001 — Pump House · Rev 2 (revision 2)",
    );
  });

  it("sends no revision and reports an unassigned run when no project is chosen", async () => {
    createCableRunMock.mockResolvedValue(runResponse);
    render(<CableSizingPage />, { wrapper: createWrapper() });

    expect(screen.getByText(/No project — this run will be unassigned/)).toBeInTheDocument();

    fillMinimumValidDraft();
    submit();

    await waitFor(() => expect(calculationState()).toBe("success"));
    expect(createCableRunMock.mock.calls[0]?.[2]).toBeUndefined();
    expect(document.querySelector('[data-field="project"]')?.textContent).toBe("Unassigned");
  });

  it("sends no revision from a project that has no open revision", async () => {
    createCableRunMock.mockResolvedValue(runResponse);
    render(<CableSizingPage />, {
      wrapper: createWrapper(
        workingIn({
          status: "read-only",
          project: PROJECT_FIXTURE,
          revision: { ...REVISION_FIXTURE, status: "ISSUED" },
        }),
      ),
    });

    expect(
      screen.getByText(/No open revision — this run will not be linked to this project/),
    ).toBeInTheDocument();

    fillMinimumValidDraft();
    submit();

    await waitFor(() => expect(calculationState()).toBe("success"));
    expect(createCableRunMock.mock.calls[0]?.[2]).toBeUndefined();
  });

  it("shows the server's own refusal when the revision takes no run", async () => {
    createCableRunMock.mockRejectedValue(
      new ApiError("Runs can only be added to the open revision.", 409),
    );
    render(<CableSizingPage />, { wrapper: createWrapper() });

    fillMinimumValidDraft();
    submit();

    await waitFor(() => expect(calculationState()).toBe("error"));
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Runs can only be added to the open revision.",
    );
  });

});
