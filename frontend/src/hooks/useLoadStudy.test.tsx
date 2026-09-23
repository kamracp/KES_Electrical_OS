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
  LoadGroupResponse,
  LoadRunCreateRequest,
  LoadRunResponse,
} from "../services/loadDemand";
import { useLoadStudy } from "./useLoadStudy";

const createLoadRunMock = vi.hoisted(() =>
  vi.fn<
    (
      payload: LoadRunCreateRequest,
      signal?: AbortSignal,
      projectRevisionId?: string,
    ) => Promise<LoadRunResponse>
  >(),
);

vi.mock("../services/loadDemand", () => ({
  createLoadRun: createLoadRunMock,
}));

const request = {
  study: {
    code: "LOAD-001",
    name: "Process Pump Loads",
    loads: [],
  },
} as unknown as LoadRunCreateRequest;

const response = {
  group_code: "LOAD-001",
  group_name: "Process Pump Loads",
  coincidence_factor: "0.90",
  connected_power_kw: "32.6087",
  pre_coincidence_demand_kw: "23.4783",
  demand_power_kw: "21.1304",
  apparent_power_kva: "24.8593",
  reactive_power_kvar: "13.0955",
  load_results: [],
  status: "VALID",
  warnings: [],
  assumptions: ["The group coincidence factor is applied equally to active and reactive demand."],
  jurisdiction_profile: "IN",
} as unknown as LoadGroupResponse;

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
  design_check_status: "VALID",
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

// The study pages and hooks read the chosen project from the provider; these tests run with
// no project unless they say otherwise, so every existing expectation is unchanged.
function workingIn(state: ProjectState): ProjectContextValue {
  return {
    state,
    select: vi.fn(),
    clear: vi.fn(),
    activeRevisionId: () =>
      state.status === "selected" || state.status === "read-only" ? state.revision.id : null,
  };
}

const NO_PROJECT = workingIn({ status: "none" });
const REVISION_ID = "b6b3f4d2-8a1c-4a5e-9a3b-2f7c1d0e5a44";

function projectRevision(status: "selected" | "read-only"): ProjectContextValue {
  const state = {
    status,
    project: { id: "p-1", code: "PRJ-001" },
    revision: { id: REVISION_ID, revision_number: 1 },
  } as unknown as ProjectState;
  return {
    ...workingIn(state),
    // The provider answers null in "read-only": that revision takes no more runs.
    activeRevisionId: () => (status === "selected" ? REVISION_ID : null),
  };
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
  createLoadRunMock.mockReset();
});

afterEach(() => {
  cleanup();
});

describe("useLoadStudy", () => {
  it("returns the service result unchanged on success", async () => {
    createLoadRunMock.mockResolvedValue(runResponse);
    const { result } = renderHook(() => useLoadStudy(), { wrapper: createWrapper() });

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
    expect(createLoadRunMock).toHaveBeenCalledTimes(1);
    expect(createLoadRunMock.mock.calls[0]?.[0]).toBe(request);
    expect(createLoadRunMock.mock.calls[0]?.[1]).toBeInstanceOf(AbortSignal);
  });

  it("sends no project revision when the workspace is in no project", async () => {
    createLoadRunMock.mockResolvedValue(runResponse);
    const { result } = renderHook(() => useLoadStudy(), { wrapper: createWrapper() });

    await act(async () => {
      await result.current.calculate(request);
    });

    expect(createLoadRunMock.mock.calls[0]?.[2]).toBeUndefined();
  });

  it("sends the chosen open revision so the run belongs to that project", async () => {
    createLoadRunMock.mockResolvedValue(runResponse);
    const { result } = renderHook(() => useLoadStudy(), {
      wrapper: createWrapper(projectRevision("selected")),
    });

    await act(async () => {
      await result.current.calculate(request);
    });

    expect(createLoadRunMock.mock.calls[0]?.[2]).toBe(REVISION_ID);
  });

  it("sends nothing when the chosen revision takes no more runs", async () => {
    createLoadRunMock.mockResolvedValue(runResponse);
    const { result } = renderHook(() => useLoadStudy(), {
      wrapper: createWrapper(projectRevision("read-only")),
    });

    await act(async () => {
      await result.current.calculate(request);
    });

    // A read-only revision would be refused by the server; the run is stored
    // without a project instead.
    expect(createLoadRunMock.mock.calls[0]?.[2]).toBeUndefined();
  });

  it("accepts the reused revision the backend answers with HTTP 200 (A11)", async () => {
    const reused: LoadRunResponse = { run: { ...sampleRun, revision_number: 1 }, result: response };
    createLoadRunMock.mockResolvedValue(reused);
    const { result } = renderHook(() => useLoadStudy(), { wrapper: createWrapper() });

    await act(async () => {
      await result.current.calculate(request);
    });

    // The service returns a parsed body for both 201 and 200; the hook does not
    // look at the status, so a reused run reaches the page like a new one.
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.run).toEqual(reused.run);
  });

  it("exposes a service error without transforming it", async () => {
    createLoadRunMock.mockRejectedValue(new Error("body.study.loads: Input should be a valid list"));
    const { result } = renderHook(() => useLoadStudy(), { wrapper: createWrapper() });

    await act(async () => {
      await result.current.calculate(request).catch(() => undefined);
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error?.message).toBe("body.study.loads: Input should be a valid list");
    expect(result.current.result).toBeNull();
    expect(result.current.run).toBeNull();
  });

  it("keeps an ApiError an ApiError, so the session guard still sees the status", async () => {
    createLoadRunMock.mockRejectedValue(new ApiError("Not authenticated", 401));
    const { result } = renderHook(() => useLoadStudy(), { wrapper: createWrapper() });

    await act(async () => {
      await result.current.calculate(request).catch(() => undefined);
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error).toBeInstanceOf(ApiError);
    expect((result.current.error as ApiError).status).toBe(401);
  });

  it("aborts the previous request when a new one is submitted", async () => {
    const signals: AbortSignal[] = [];
    createLoadRunMock.mockImplementation((_payload, signal) => {
      if (signal) signals.push(signal);
      return new Promise<LoadRunResponse>((resolve, reject) => {
        signal?.addEventListener("abort", () => reject(signal.reason), { once: true });
        setTimeout(() => resolve(runResponse), 5);
      });
    });
    const { result } = renderHook(() => useLoadStudy(), { wrapper: createWrapper() });

    let first: Promise<LoadRunResponse> | undefined;
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
    createLoadRunMock.mockImplementation(
      (_payload, signal) =>
        new Promise<LoadRunResponse>((_resolve, reject) => {
          captured = signal;
          signal?.addEventListener("abort", () => reject(signal.reason), { once: true });
        }),
    );
    const { result, unmount } = renderHook(() => useLoadStudy(), { wrapper: createWrapper() });

    act(() => {
      void result.current.calculate(request).catch(() => undefined);
    });
    await waitFor(() => expect(createLoadRunMock).toHaveBeenCalledTimes(1));
    expect(captured?.aborted).toBe(false);

    unmount();

    expect(captured?.aborted).toBe(true);
  });

  it("clears result and error on reset", async () => {
    createLoadRunMock.mockResolvedValue(runResponse);
    const { result } = renderHook(() => useLoadStudy(), { wrapper: createWrapper() });

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
