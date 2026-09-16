// @vitest-environment jsdom

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, cleanup, renderHook, waitFor } from "@testing-library/react";
import type { PropsWithChildren } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { CableSizingRequest, CableSizingResponse } from "../services/cable";
import { useCableSizing } from "./useCableSizing";

const calculateCableSizingMock = vi.hoisted(() =>
  vi.fn<(payload: CableSizingRequest, signal?: AbortSignal) => Promise<CableSizingResponse>>(),
);

vi.mock("../services/cable", () => ({
  calculateCableSizing: calculateCableSizingMock,
}));

const request = {
  code: "CBL-001",
  name: "Feeder to MCC-1",
} as unknown as CableSizingRequest;

const response = {
  study_code: "CBL-001",
  status: "DESIGN_CHECK_PASSED",
  conductor: null,
  ampacity: null,
  voltage_drop: null,
  short_circuit: null,
  warnings: [],
  standard_reference: "IEC 60364-5-52",
  ampacity_reference: "IEC 60287",
  jurisdiction_profile: "IN",
  reference_verification_status: "UNVERIFIED",
  notes: null,
} as CableSizingResponse;

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { mutations: { retry: false } },
  });
  return function Wrapper({ children }: PropsWithChildren) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

beforeEach(() => {
  calculateCableSizingMock.mockReset();
});

afterEach(() => {
  cleanup();
});

describe("useCableSizing", () => {
  it("returns the service result unchanged on success", async () => {
    calculateCableSizingMock.mockResolvedValue(response);
    const { result } = renderHook(() => useCableSizing(), { wrapper: createWrapper() });

    expect(result.current.result).toBeNull();
    expect(result.current.isPending).toBe(false);

    await act(async () => {
      await result.current.calculate(request);
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.result).toEqual(response);
    expect(result.current.error).toBeNull();
    expect(calculateCableSizingMock).toHaveBeenCalledTimes(1);
    expect(calculateCableSizingMock.mock.calls[0]?.[0]).toBe(request);
    expect(calculateCableSizingMock.mock.calls[0]?.[1]).toBeInstanceOf(AbortSignal);
  });

  it("exposes a service error without transforming it", async () => {
    calculateCableSizingMock.mockRejectedValue(new Error("body.circuit.design_current_a: Input should be greater than 0"));
    const { result } = renderHook(() => useCableSizing(), { wrapper: createWrapper() });

    await act(async () => {
      await result.current.calculate(request).catch(() => undefined);
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error?.message).toBe(
      "body.circuit.design_current_a: Input should be greater than 0",
    );
    expect(result.current.result).toBeNull();
  });

  it("aborts the previous request when a new one is submitted", async () => {
    const signals: AbortSignal[] = [];
    calculateCableSizingMock.mockImplementation((_payload, signal) => {
      if (signal) signals.push(signal);
      return new Promise<CableSizingResponse>((resolve, reject) => {
        signal?.addEventListener("abort", () => reject(signal.reason), { once: true });
        setTimeout(() => resolve(response), 5);
      });
    });
    const { result } = renderHook(() => useCableSizing(), { wrapper: createWrapper() });

    let first: Promise<CableSizingResponse> | undefined;
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
    calculateCableSizingMock.mockImplementation(
      (_payload, signal) =>
        new Promise<CableSizingResponse>((_resolve, reject) => {
          captured = signal;
          signal?.addEventListener("abort", () => reject(signal.reason), { once: true });
        }),
    );
    const { result, unmount } = renderHook(() => useCableSizing(), { wrapper: createWrapper() });

    act(() => {
      void result.current.calculate(request).catch(() => undefined);
    });
    await waitFor(() => expect(calculateCableSizingMock).toHaveBeenCalledTimes(1));
    expect(captured?.aborted).toBe(false);

    unmount();

    expect(captured?.aborted).toBe(true);
  });

  it("clears result and error on reset", async () => {
    calculateCableSizingMock.mockResolvedValue(response);
    const { result } = renderHook(() => useCableSizing(), { wrapper: createWrapper() });

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
