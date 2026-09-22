// @vitest-environment jsdom

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, cleanup, renderHook, waitFor } from "@testing-library/react";
import type { PropsWithChildren } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  ProjectContext,
  type ProjectContextValue,
  type ProjectState,
} from "../app/projectContext";

import type { CableRunResponse, CableSizingRequest, CableSizingResponse } from "../services/cable";
import { useCableSizing } from "./useCableSizing";

const createCableRunMock = vi.hoisted(() =>
  vi.fn<(payload: CableSizingRequest, signal?: AbortSignal) => Promise<CableRunResponse>>(),
);

vi.mock("../services/cable", () => ({
  createCableRun: createCableRunMock,
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
  reference_source: "PROFILE",
  jurisdiction_profile: "IN",
  reference_verification_status: "UNVERIFIED",
  notes: null,
} as CableSizingResponse;

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

const runResponse = { run: sampleRun, result: response } as CableRunResponse;

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
        <ProjectContext.Provider value={project}>{children}</ProjectContext.Provider>
      </QueryClientProvider>
    );
  };
}

beforeEach(() => {
  createCableRunMock.mockReset();
});

afterEach(() => {
  cleanup();
});

describe("useCableSizing", () => {
  it("returns the service result unchanged on success", async () => {
    createCableRunMock.mockResolvedValue(runResponse);
    const { result } = renderHook(() => useCableSizing(), { wrapper: createWrapper() });

    expect(result.current.result).toBeNull();
    expect(result.current.isPending).toBe(false);

    await act(async () => {
      await result.current.calculate(request);
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.result).toEqual(response);
    expect(result.current.error).toBeNull();
    expect(createCableRunMock).toHaveBeenCalledTimes(1);
    expect(createCableRunMock.mock.calls[0]?.[0]).toBe(request);
    expect(createCableRunMock.mock.calls[0]?.[1]).toBeInstanceOf(AbortSignal);
  });

  it("exposes a service error without transforming it", async () => {
    createCableRunMock.mockRejectedValue(new Error("body.circuit.design_current_a: Input should be greater than 0"));
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
    createCableRunMock.mockImplementation((_payload, signal) => {
      if (signal) signals.push(signal);
      return new Promise<CableRunResponse>((resolve, reject) => {
        signal?.addEventListener("abort", () => reject(signal.reason), { once: true });
        setTimeout(() => resolve(runResponse), 5);
      });
    });
    const { result } = renderHook(() => useCableSizing(), { wrapper: createWrapper() });

    let first: Promise<CableRunResponse> | undefined;
    act(() => {
      first = result.current.calculate(request).catch(() => runResponse);
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
    createCableRunMock.mockImplementation(
      (_payload, signal) =>
        new Promise<CableRunResponse>((_resolve, reject) => {
          captured = signal;
          signal?.addEventListener("abort", () => reject(signal.reason), { once: true });
        }),
    );
    const { result, unmount } = renderHook(() => useCableSizing(), { wrapper: createWrapper() });

    act(() => {
      void result.current.calculate(request).catch(() => undefined);
    });
    await waitFor(() => expect(createCableRunMock).toHaveBeenCalledTimes(1));
    expect(captured?.aborted).toBe(false);

    unmount();

    expect(captured?.aborted).toBe(true);
  });

  it("clears result and error on reset", async () => {
    createCableRunMock.mockResolvedValue(runResponse);
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
