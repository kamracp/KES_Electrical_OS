// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import type { PropsWithChildren } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type {
  FaultRunResponse,
  ShortCircuitStudyRequest,
  ShortCircuitStudyResponse,
} from "../services/fault";
import { FaultStudyPage } from "./FaultStudyPage";

type CreateFaultRun = (
  payload: ShortCircuitStudyRequest,
  signal?: AbortSignal,
) => Promise<FaultRunResponse>;

const createFaultRunMock = vi.hoisted(() => vi.fn<CreateFaultRun>());

// Partial mock: keep the real schemas, replace only the network call.
vi.mock("../services/fault", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../services/fault")>();
  return { ...actual, createFaultRun: createFaultRunMock };
});

// The full network form is covered by FaultStudyForm.test.tsx; here it is replaced by a
// single button so the page wiring (submit -> hook -> panels) is what gets tested.
const fixtureRequest = { code: "SC-001", name: "Fixture" } as unknown as ShortCircuitStudyRequest;

vi.mock("../components/FaultStudyForm", () => ({
  FaultStudyForm: ({
    disabled,
    onSubmit,
  }: {
    disabled?: boolean;
    onSubmit: (payload: ShortCircuitStudyRequest) => void | Promise<void>;
  }) => (
    <button type="button" disabled={disabled} onClick={() => void onSubmit(fixtureRequest)}>
      Submit fixture
    </button>
  ),
}));

const response: ShortCircuitStudyResponse = {
  study_code: "SC-001",
  study_name: "Main switchboard three-phase fault",
  calculation_case: "MAXIMUM",
  fault_bus_code: "MSB-01",
  fault_type: "THREE_PHASE",
  nominal_voltage_v: "415",
  frequency_hz: "50",
  status: "WARNING",
  initial_symmetrical_short_circuit_current_ka: "25.40",
  peak_short_circuit_current_ka: null,
  symmetrical_breaking_current_ka: null,
  steady_state_short_circuit_current_ka: null,
  thermal_equivalent_short_circuit_current_ka: null,
  earth_fault_current_ka: null,
  kappa_factor: null,
  x_r_ratio: null,
  clearing_time_s: null,
  sequence_results: [],
  source_contributions: [],
  warnings: [
    {
      code: "PEAK_CURRENT_NOT_EVALUATED",
      severity: "WARNING",
      message: "X/R ratio unavailable; peak current not evaluated.",
      reference_code: null,
    },
  ],
  standard_reference: "IEC 60909-0 (UNVERIFIED)",
  earth_current_reference: "IEC 60909-0 (UNVERIFIED)",
  reference_source: "PROFILE",
  jurisdiction_profile: "IN",
  reference_verification_status: "UNVERIFIED",
  operating_state_code: null,
  notes: null,
};

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { mutations: { retry: false } },
  });
  return function Wrapper({ children }: PropsWithChildren) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

const sampleRun: FaultRunResponse["run"] = {
  id: "48a782d0-4331-4aa2-bcd0-f24f5016334a",
  module_code: "EOS-04",
  project_revision_id: null,
  project: null,
  calculation_type: "SHORT_CIRCUIT",
  calculation_key: "SC-001",
  revision_number: 1,
  run_status: "COMPLETED",
  approval_status: "NOT_SUBMITTED",
  engine_version: "fault-engine 0.1.0",
  design_check_status: "WARNING",
  jurisdiction_profile: "IN",
  reference_verification_status: "UNVERIFIED",
  content_hash: "e2805d5d7ba2e2805d5d7ba2e2805d5d7ba2e2805d5d7ba2e2805d5d7ba2e280",
  calculated_by: null,
  calculated_at: "2026-09-18T12:00:00+00:00",
  created_at: "2026-09-18T12:00:00+00:00",
  is_immutable: false,
  supersedes_run_id: null,
  notes: null,
};

const runResponse: FaultRunResponse = { run: sampleRun, result: response };

beforeEach(() => {
  createFaultRunMock.mockReset();
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

describe("FaultStudyPage", () => {
  it("renders the EOS-04 workspace in the idle state", () => {
    render(<FaultStudyPage />, { wrapper: createWrapper() });

    expect(screen.getByRole("heading", { level: 1, name: "Fault Study" })).toBeInTheDocument();
    expect(screen.getByText("EOS-04 · Short-Circuit & Earth-Fault")).toBeInTheDocument();
    expect(document.querySelector('[data-calculation-state="idle"]')).not.toBeNull();
    expect(screen.getByText(/not an automatic compliance declaration/i)).toBeInTheDocument();
    expect(screen.queryByRole("article")).toBeNull();
  });

  it("runs the study, renders result and warning panels, and clears back to idle", async () => {
    createFaultRunMock.mockResolvedValue(runResponse);
    render(<FaultStudyPage />, { wrapper: createWrapper() });

    fireEvent.click(screen.getByRole("button", { name: "Submit fixture" }));

    await waitFor(() =>
      expect(document.querySelector('[data-calculation-state="success"]')).not.toBeNull(),
    );
    expect(createFaultRunMock).toHaveBeenCalledTimes(1);
    expect(createFaultRunMock.mock.calls[0]?.[0]).toBe(fixtureRequest);
    expect(screen.getByRole("article", { name: "Fault study result" })).toBeInTheDocument();
    const article = screen.getByRole("article", { name: "Fault study result" });
    expect(within(article).getByText("Calculated with warnings")).toHaveAttribute(
      "data-result-status",
      "WARNING",
    );
    const summary = screen.getByRole("region", { name: "Result summary" });
    expect(within(summary).getByText("Calculated with warnings")).toHaveAttribute(
      "data-summary-status",
      "WARNING",
    );
    expect(document.querySelector('[data-warning-code="PEAK_CURRENT_NOT_EVALUATED"]')).not.toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "Clear results" }));

    await waitFor(() =>
      expect(document.querySelector('[data-calculation-state="idle"]')).not.toBeNull(),
    );
    expect(screen.queryByRole("article")).toBeNull();
  });

  it("surfaces a service error as an alert without a result panel", async () => {
    createFaultRunMock.mockRejectedValue(
      new Error("body.fault.bus_code: bus MSB-99 is not defined"),
    );
    render(<FaultStudyPage />, { wrapper: createWrapper() });

    fireEvent.click(screen.getByRole("button", { name: "Submit fixture" }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveAttribute("data-calculation-state", "error");
    expect(alert.textContent).toContain("bus MSB-99 is not defined");
    expect(screen.queryByRole("article")).toBeNull();
  });

  it("opens with the inputs expanded inside a collapsible block", () => {
    render(<FaultStudyPage />, { wrapper: createWrapper() });

    const inputs = document.getElementById("fault-study-inputs-heading")?.closest("details");
    expect(inputs).toHaveAttribute("data-study-inputs");
    expect(inputs).toHaveAttribute("open");
    expect(inputs).toContainElement(screen.getByRole("button", { name: "Submit fixture" }));
  });

  it("orders the result column as summary, warnings, traceability, then detail", async () => {
    createFaultRunMock.mockResolvedValue(runResponse);
    render(<FaultStudyPage />, { wrapper: createWrapper() });

    fireEvent.click(screen.getByRole("button", { name: "Submit fixture" }));

    await waitFor(() => expect(successState()).not.toBeNull());
    const summary = screen.getByRole("region", { name: "Result summary" });
    const warning = document.querySelector('[data-warning-code="PEAK_CURRENT_NOT_EVALUATED"]');
    const traceability = screen.getByRole("region", { name: "Traceability" });
    const detail = screen.getByRole("article", { name: "Fault study result" });

    expect(precedes(summary, warning)).toBe(true);
    expect(precedes(warning, traceability)).toBe(true);
    expect(precedes(traceability, detail)).toBe(true);
  });

  it("shows the persisted run in the traceability panel and exports it as JSON", async () => {
    createFaultRunMock.mockResolvedValue(runResponse);
    render(<FaultStudyPage />, { wrapper: createWrapper() });

    fireEvent.click(screen.getByRole("button", { name: "Submit fixture" }));

    await waitFor(() => expect(successState()).not.toBeNull());
    const traceability = screen.getByRole("region", { name: "Traceability" });
    expect(traceability).toHaveAttribute("data-run-id", sampleRun.id);
    expect(within(traceability).getByText(sampleRun.id)).toBeInTheDocument();
    expect(within(traceability).getByText(sampleRun.engine_version)).toBeInTheDocument();

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
    expect(downloads).toEqual(["SC-001-rev1.json"]);
    anchorClick.mockRestore();
    expect(successState()).not.toBeNull();
  });
});
