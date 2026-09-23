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

import { ApiError } from "../services/http";

import type {
  FaultRunResponse,
  ShortCircuitStudyRequest,
  ShortCircuitStudyResponse,
} from "../services/fault";
import { useFaultStudy } from "./useFaultStudy";

// The whole signature of createFaultRun, including the project revision it is
// given as the third argument; the tests below read that argument.
const createFaultRunMock = vi.hoisted(() =>
  vi.fn<
    (
      payload: ShortCircuitStudyRequest,
      signal?: AbortSignal,
      projectRevisionId?: string,
    ) => Promise<FaultRunResponse>
  >(),
);

vi.mock("../services/fault", () => ({
  createFaultRun: createFaultRunMock,
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
  design_check_status: "CALCULATED",
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
const REVISION_ID = "4b8e6d42-1c3f-4b5a-9e7d-8f9a0b1c2d3e";

// "selected" is the open revision a run may be attached to; "read-only" is a project still
// on screen whose revision takes no more runs, so the provider answers null.
function projectRevision(status: "selected" | "read-only"): ProjectContextValue {
  return workingIn({
    status,
    project: { id: "2a7d5c31-9b0e-4a21-8f6c-7d8e9f0a1b2c", code: "PRJ-001" },
    revision: { id: REVISION_ID, revision_number: 1 },
  } as unknown as ProjectState);
}

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
  createFaultRunMock.mockReset();
});

afterEach(() => {
  cleanup();
});

describe("useFaultStudy", () => {
  it("returns the service result unchanged on success", async () => {
    createFaultRunMock.mockResolvedValue(runResponse);
    const { result } = renderHook(() => useFaultStudy(), { wrapper: createWrapper() });

    expect(result.current.result).toBeNull();
    expect(result.current.isPending).toBe(false);
    expect(result.current.run).toBeNull();

    await act(async () => {
      await result.current.calculate(request);
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.result).toEqual(response);
    expect(result.current.run).toEqual(sampleRun);
    expect(result.current.error).toBeNull();
    expect(createFaultRunMock).toHaveBeenCalledTimes(1);
    expect(createFaultRunMock.mock.calls[0]?.[0]).toBe(request);
    expect(createFaultRunMock.mock.calls[0]?.[1]).toBeInstanceOf(AbortSignal);
  });

  it("sends no project revision when the workspace is in no project", async () => {
    createFaultRunMock.mockResolvedValue(runResponse);
    const { result } = renderHook(() => useFaultStudy(), { wrapper: createWrapper() });

    await act(async () => {
      await result.current.calculate(request);
    });

    expect(createFaultRunMock.mock.calls[0]?.[2]).toBeUndefined();
  });

  it("sends the chosen open revision so the run belongs to that project", async () => {
    createFaultRunMock.mockResolvedValue(runResponse);
    const { result } = renderHook(() => useFaultStudy(), {
      wrapper: createWrapper(projectRevision("selected")),
    });

    await act(async () => {
      await result.current.calculate(request);
    });

    expect(createFaultRunMock.mock.calls[0]?.[2]).toBe(REVISION_ID);
  });

  it("sends nothing when the chosen revision takes no more runs", async () => {
    createFaultRunMock.mockResolvedValue(runResponse);
    const { result } = renderHook(() => useFaultStudy(), {
      wrapper: createWrapper(projectRevision("read-only")),
    });

    await act(async () => {
      await result.current.calculate(request);
    });

    // A read-only revision would be refused by the server; the run is stored
    // without a project instead.
    expect(createFaultRunMock.mock.calls[0]?.[2]).toBeUndefined();
  });

  it("keeps an ApiError an ApiError, so the session guard still sees the status", async () => {
    createFaultRunMock.mockRejectedValue(new ApiError("Not authenticated", 401));
    const { result } = renderHook(() => useFaultStudy(), { wrapper: createWrapper() });

    await act(async () => {
      await result.current.calculate(request).catch(() => undefined);
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error).toBeInstanceOf(ApiError);
    expect((result.current.error as ApiError).status).toBe(401);
  });

  it("exposes a service error without transforming it", async () => {
    createFaultRunMock.mockRejectedValue(new Error("body.fault.bus_code: Input should be a valid string"));
    const { result } = renderHook(() => useFaultStudy(), { wrapper: createWrapper() });

    await act(async () => {
      await result.current.calculate(request).catch(() => undefined);
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error?.message).toBe(
      "body.fault.bus_code: Input should be a valid string",
    );
    expect(result.current.result).toBeNull();
    expect(result.current.run).toBeNull();
  });

  it("aborts the previous request when a new one is submitted", async () => {
    const signals: AbortSignal[] = [];
    createFaultRunMock.mockImplementation((_payload, signal) => {
      if (signal) signals.push(signal);
      return new Promise<FaultRunResponse>((resolve, reject) => {
        signal?.addEventListener("abort", () => reject(signal.reason), { once: true });
        setTimeout(() => resolve(runResponse), 5);
      });
    });
    const { result } = renderHook(() => useFaultStudy(), { wrapper: createWrapper() });

    let first: Promise<FaultRunResponse> | undefined;
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
    createFaultRunMock.mockImplementation(
      (_payload, signal) =>
        new Promise<FaultRunResponse>((_resolve, reject) => {
          captured = signal;
          signal?.addEventListener("abort", () => reject(signal.reason), { once: true });
        }),
    );
    const { result, unmount } = renderHook(() => useFaultStudy(), { wrapper: createWrapper() });

    act(() => {
      void result.current.calculate(request).catch(() => undefined);
    });
    await waitFor(() => expect(createFaultRunMock).toHaveBeenCalledTimes(1));
    expect(captured?.aborted).toBe(false);

    unmount();

    expect(captured?.aborted).toBe(true);
  });

  it("clears result and error on reset", async () => {
    createFaultRunMock.mockResolvedValue(runResponse);
    const { result } = renderHook(() => useFaultStudy(), { wrapper: createWrapper() });

    await act(async () => {
      await result.current.calculate(request);
    });
    await waitFor(() => expect(result.current.result).toEqual(response));

    act(() => {
      result.current.reset();
    });

    await waitFor(() => expect(result.current.result).toBeNull());
    expect(result.current.run).toBeNull();
    expect(result.current.isSuccess).toBe(false);
    expect(result.current.error).toBeNull();
  });
});
