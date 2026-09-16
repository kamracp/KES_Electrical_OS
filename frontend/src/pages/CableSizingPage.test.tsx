// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { PropsWithChildren } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { CableSizingRequest, CableSizingResponse } from "../services/cable";
import { CableSizingPage } from "./CableSizingPage";

const calculateCableSizingMock = vi.hoisted(() =>
  vi.fn<(payload: CableSizingRequest, signal?: AbortSignal) => Promise<CableSizingResponse>>(),
);

// Partial mock: the form still needs the real cableSizingRequestSchema export.
vi.mock("../services/cable", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../services/cable")>();
  return { ...actual, calculateCableSizing: calculateCableSizingMock };
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

beforeEach(() => {
  calculateCableSizingMock.mockReset();
});

afterEach(() => {
  cleanup();
});

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
    let resolveCalculation: (value: CableSizingResponse) => void = () => undefined;
    calculateCableSizingMock.mockImplementation(
      () =>
        new Promise<CableSizingResponse>((resolve) => {
          resolveCalculation = resolve;
        }),
    );
    renderPage();

    fillMinimumValidDraft();
    submit();

    await waitFor(() => expect(calculationState()).toBe("pending"));
    expect(screen.getByRole("status")).toHaveTextContent("Calculating cable size");
    expect(screen.getByRole("button", { name: "Calculate cable sizing" })).toBeDisabled();
    expect(calculateCableSizingMock).toHaveBeenCalledTimes(1);
    expect(calculateCableSizingMock.mock.calls[0]?.[0]).toMatchObject({ code: "CBL-001" });

    resolveCalculation(response);

    await waitFor(() => expect(calculationState()).toBe("success"));
    expect(screen.getByRole("article", { name: "Cable sizing result" })).toBeInTheDocument();
    expect(screen.getByText("Design check passed")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Engineering warnings" })).toHaveTextContent(
      "High total derating",
    );
    expect(screen.getByRole("button", { name: "Calculate cable sizing" })).toBeEnabled();
  });

  it("clears the results back to the idle state", async () => {
    calculateCableSizingMock.mockResolvedValue(response);
    renderPage();

    fillMinimumValidDraft();
    submit();
    await waitFor(() => expect(calculationState()).toBe("success"));

    fireEvent.click(screen.getByRole("button", { name: "Clear results" }));

    await waitFor(() => expect(calculationState()).toBe("idle"));
    expect(screen.queryByRole("article", { name: "Cable sizing result" })).toBeNull();
  });

  it("shows the service error as an alert and re-enables the form", async () => {
    calculateCableSizingMock.mockRejectedValue(
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
});
