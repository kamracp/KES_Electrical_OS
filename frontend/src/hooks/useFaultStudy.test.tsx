// @vitest-environment jsdom

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, cleanup, renderHook, waitFor } from "@testing-library/react";
import type { PropsWithChildren } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ShortCircuitStudyRequest, ShortCircuitStudyResponse } from "../services/fault";
import { useFaultStudy } from "./useFaultStudy";

const calculateFaultStudyMock = vi.hoisted(() =>
  vi.fn<(payload: ShortCircuitStudyRequest, signal?: AbortSignal) => Promise<ShortCircuitStudyResponse>>(),
);

vi.mock("../services/fault", () => ({
  calculateFaultStudy: calculateFaultStudyMock,
}));

const request = {
  code: "SC-001",
  name: "Main switchboard three-phase fault",
} as unknown as ShortCircuitStudyRequest;

const response = {
  study_code: "SC-001",
  study_name: "Main switchboard three-phase fault",
  calculation_case: "MAXIMUM",
  fault_bus_code: "MSB-01",
  fault_type: "THREE_PHASE",
  nominal_voltage_v: "415",
  frequency_hz: "50",
  status: "CALCULATED",
  initial_symmetrical_short_circuit_current_ka: "25.40",
  sequence_results: [],
  source_contributions: [],
  warnings: [],
  standard_reference: "IEC 60909-0",
  earth_current_reference: "IEC 60909-0",
  reference_source: "PROFILE",
  jurisdiction_profile: "IN",
  reference_verification_status: "UNVERIFIED",
  operating_state_code: null,
  notes: null,
} as unknown as ShortCircuitStudyResponse;

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

describe("useFaultStudy", () => {
  it("returns the service result unchanged on success", async () => {
    calculateFaultStudyMock.mockResolvedValue(response);
    const { result } = renderHook(() => useFaultStudy(), { wrapper: createWrapper() });

    expect(result.current.result).toBeNull();
    expect(result.current.isPending).toBe(false);

    await act(async () => {
      await result.current.calculate(request);
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.result).toEqual(response);
    expect(result.current.error).toBeNull();
    expect(calculateFaultStudyMock).toHaveBeenCalledTimes(1);
    expect(calculateFaultStudyMock.mock.calls[0]?.[0]).toBe(request);
    expect(calculateFaultStudyMock.mock.calls[0]?.[1]).toBeInstanceOf(AbortSignal);
  });

  it("exposes a service error without transforming it", async () => {
    calculateFaultStudyMock.mockRejectedValue(new Error("body.fault.bus_code: Input should be a valid string"));
    const { result } = renderHook(() => useFaultStudy(), { wrapper: createWrapper() });

    await act(async () => {
      await result.current.calculate(request).catch(() => undefined);
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error?.message).toBe(
      "body.fault.bus_code: Input should be a valid string",
    );
    expect(result.current.result).toBeNull();
  });

  it("aborts the previous request when a new one is submitted", async () => {
    const signals: AbortSignal[] = [];
    calculateFaultStudyMock.mockImplementation((_payload, signal) => {
      if (signal) signals.push(signal);
      return new Promise<ShortCircuitStudyResponse>((resolve, reject) => {
        signal?.addEventListener("abort", () => reject(signal.reason), { once: true });
        setTimeout(() => resolve(response), 5);
      });
    });
    const { result } = renderHook(() => useFaultStudy(), { wrapper: createWrapper() });

    let first: Promise<ShortCircuitStudyResponse> | undefined;
    act(() => {
      first = result.current.calculate(request).catch(() => response);
    });
    await act(async () => {
      await result.current.calculate(request);
    });
    await first;

    expect(signals).toHaveLength(2);
    expect(signals[0]?.aborted).toBe(true);
    expect(signals[1]?.aborted).toBe(false);
  });

  it("aborts the in-flight request on unmount", async () => {
    let captured: AbortSignal | undefined;
    calculateFaultStudyMock.mockImplementation(
      (_payload, signal) =>
        new Promise<ShortCircuitStudyResponse>((_resolve, reject) => {
          captured = signal;
          signal?.addEventListener("abort", () => reject(signal.reason), { once: true });
        }),
    );
    const { result, unmount } = renderHook(() => useFaultStudy(), { wrapper: createWrapper() });

    act(() => {
      void result.current.calculate(request).catch(() => undefined);
    });
    await waitFor(() => expect(calculateFaultStudyMock).toHaveBeenCalledTimes(1));
    expect(captured?.aborted).toBe(false);

    unmount();

    expect(captured?.aborted).toBe(true);
  });

  it("clears result and error on reset", async () => {
    calculateFaultStudyMock.mockResolvedValue(response);
    const { result } = renderHook(() => useFaultStudy(), { wrapper: createWrapper() });

    await act(async () => {
      await result.current.calculate(request);
    });
    await waitFor(() => expect(result.current.result).toEqual(response));

    act(() => {
      result.current.reset();
    });

    await waitFor(() => expect(result.current.result).toBeNull());
    expect(result.current.isSuccess).toBe(false);
    expect(result.current.error).toBeNull();
  });
});
