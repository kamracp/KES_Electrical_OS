// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { PropsWithChildren } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ShortCircuitStudyRequest, ShortCircuitStudyResponse } from "../services/fault";
import { FaultStudyPage } from "./FaultStudyPage";

type CalculateFault = (
  payload: ShortCircuitStudyRequest,
  signal?: AbortSignal,
) => Promise<ShortCircuitStudyResponse>;

const calculateFaultStudyMock = vi.hoisted(() => vi.fn<CalculateFault>());

// Partial mock: keep the real schemas, replace only the network call.
vi.mock("../services/fault", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../services/fault")>();
  return { ...actual, calculateFaultStudy: calculateFaultStudyMock };
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

beforeEach(() => {
  calculateFaultStudyMock.mockReset();
});

afterEach(() => {
  cleanup();
});

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
    calculateFaultStudyMock.mockResolvedValue(response);
    render(<FaultStudyPage />, { wrapper: createWrapper() });

    fireEvent.click(screen.getByRole("button", { name: "Submit fixture" }));

    await waitFor(() =>
      expect(document.querySelector('[data-calculation-state="success"]')).not.toBeNull(),
    );
    expect(calculateFaultStudyMock).toHaveBeenCalledTimes(1);
    expect(calculateFaultStudyMock.mock.calls[0]?.[0]).toBe(fixtureRequest);
    expect(screen.getByRole("article", { name: "Fault study result" })).toBeInTheDocument();
    expect(screen.getByText("Calculated with warnings")).toHaveAttribute(
      "data-result-status",
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
    calculateFaultStudyMock.mockRejectedValue(
      new Error("body.fault.bus_code: bus MSB-99 is not defined"),
    );
    render(<FaultStudyPage />, { wrapper: createWrapper() });

    fireEvent.click(screen.getByRole("button", { name: "Submit fixture" }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveAttribute("data-calculation-state", "error");
    expect(alert.textContent).toContain("bus MSB-99 is not defined");
    expect(screen.queryByRole("article")).toBeNull();
  });
});
