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
  TransformerRunCreateRequest,
  TransformerRunResponse,
  TransformerSizingResponse,
} from "../services/transformerSizing";
import { useTransformerSizing } from "./useTransformerSizing";

const createTransformerRunMock = vi.hoisted(() =>
  vi.fn<
    (
      payload: TransformerRunCreateRequest,
      signal?: AbortSignal,
      projectRevisionId?: string,
    ) => Promise<TransformerRunResponse>
  >(),
);

vi.mock("../services/transformerSizing", () => ({
  createTransformerRun: createTransformerRunMock,
}));

const request = {
  study: {
    code: "TR-001",
    name: "Main Transformer",
    demand_power_kw: "800",
    demand_power_factor: "0.80",
    available_unit_ratings_kva: ["1000", "1250"],
  },
} as unknown as TransformerRunCreateRequest;

// The exact JSON the backend returns for this study, from commit 7853d51.
const response = {
  code: "TR-001",
  name: "Main Transformer",
  scenario: "NORMAL",
  redundancy_mode: "NONE",
  demand_power_kw: "800",
  demand_power_factor: "0.80",
  base_demand_kva: "1000.0000",
  future_growth_factor: "1",
  future_demand_kva: "1000.0000",
  design_margin_factor: "1.10",
  design_required_kva: "1100.0000",
  combined_derating_factor: "1.0000",
  required_nameplate_capacity_kva: "1100.0000",
  duty_units: 1,
  standby_units: 0,
  total_units: 1,
  required_unit_rating_kva: "1100.0000",
  selected_unit_rating_kva: "1250",
  installed_nameplate_capacity_kva: "1250.0000",
  derated_duty_capacity_kva: "1250.0000",
  spare_derated_capacity_kva: "150.0000",
  loading_percent: "88.0000",
  status: "VALID",
  warnings: [],
  jurisdiction_profile: "IN",
} as unknown as TransformerSizingResponse;

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

const runResponse: TransformerRunResponse = { run: sampleRun, result: response };

// The study pages and hooks read the chosen project from the provider; these tests run with
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
const REVISION_ID = "b6b3f4d2-8a1c-4a5e-9a3b-2f7c1d0e5a44";

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
  createTransformerRunMock.mockReset();
});

afterEach(() => {
  cleanup();
});

describe("useTransformerSizing", () => {
  it("returns the service result unchanged on success", async () => {
    createTransformerRunMock.mockResolvedValue(runResponse);
    const { result } = renderHook(() => useTransformerSizing(), { wrapper: createWrapper() });

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
    expect(createTransformerRunMock).toHaveBeenCalledTimes(1);
    expect(createTransformerRunMock.mock.calls[0]?.[0]).toBe(request);
    expect(createTransformerRunMock.mock.calls[0]?.[1]).toBeInstanceOf(AbortSignal);
  });

  it("sends no project revision when the workspace is in no project", async () => {
    createTransformerRunMock.mockResolvedValue(runResponse);
    const { result } = renderHook(() => useTransformerSizing(), { wrapper: createWrapper() });

    await act(async () => {
      await result.current.calculate(request);
    });

    expect(createTransformerRunMock.mock.calls[0]?.[2]).toBeUndefined();
  });

  it("sends the chosen open revision so the run belongs to that project", async () => {
    createTransformerRunMock.mockResolvedValue(runResponse);
    const { result } = renderHook(() => useTransformerSizing(), {
      wrapper: createWrapper(projectRevision("selected")),
    });

    await act(async () => {
      await result.current.calculate(request);
    });

    expect(createTransformerRunMock.mock.calls[0]?.[2]).toBe(REVISION_ID);
  });

  it("sends nothing when the chosen revision takes no more runs", async () => {
    createTransformerRunMock.mockResolvedValue(runResponse);
    const { result } = renderHook(() => useTransformerSizing(), {
      wrapper: createWrapper(projectRevision("read-only")),
    });

    await act(async () => {
      await result.current.calculate(request);
    });

    // A read-only revision would be refused by the server; the run is stored
    // without a project instead.
    expect(createTransformerRunMock.mock.calls[0]?.[2]).toBeUndefined();
  });

  it("passes the study notes through to the service", async () => {
    createTransformerRunMock.mockResolvedValue(runResponse);
    const withNotes = { ...request, notes: "Preliminary sizing." };
    const { result } = renderHook(() => useTransformerSizing(), { wrapper: createWrapper() });

    await act(async () => {
      await result.current.calculate(withNotes);
    });

    expect(createTransformerRunMock.mock.calls[0]?.[0]).toBe(withNotes);
  });

  it("accepts the reused revision the backend answers with HTTP 200 (A11)", async () => {
    const reused: TransformerRunResponse = {
      run: { ...sampleRun, revision_number: 1 },
      result: response,
    };
    createTransformerRunMock.mockResolvedValue(reused);
    const { result } = renderHook(() => useTransformerSizing(), { wrapper: createWrapper() });

    await act(async () => {
      await result.current.calculate(request);
    });

    // The service returns a parsed body for both 201 and 200; the hook does not
    // look at the status, so a reused run reaches the page like a new one.
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.run).toEqual(reused.run);
  });

  it("shows a no-solution result like any other: it is evidence too", async () => {
    const noSolution: TransformerRunResponse = {
      run: { ...sampleRun, design_check_status: "NO_SOLUTION" },
      result: {
        ...response,
        selected_unit_rating_kva: null,
        installed_nameplate_capacity_kva: null,
        derated_duty_capacity_kva: null,
        spare_derated_capacity_kva: null,
        loading_percent: null,
        status: "NO_SOLUTION",
      } as unknown as TransformerSizingResponse,
    };
    createTransformerRunMock.mockResolvedValue(noSolution);
    const { result } = renderHook(() => useTransformerSizing(), { wrapper: createWrapper() });

    await act(async () => {
      await result.current.calculate(request);
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.result?.status).toBe("NO_SOLUTION");
    expect(result.current.result?.selected_unit_rating_kva).toBeNull();
    expect(result.current.run).toEqual(noSolution.run);
    expect(result.current.isError).toBe(false);
  });

  it("exposes a service error without transforming it", async () => {
    createTransformerRunMock.mockRejectedValue(
      new Error("body.study.available_unit_ratings_kva: must be in ascending order"),
    );
    const { result } = renderHook(() => useTransformerSizing(), { wrapper: createWrapper() });

    await act(async () => {
      await result.current.calculate(request).catch(() => undefined);
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error?.message).toBe(
      "body.study.available_unit_ratings_kva: must be in ascending order",
    );
    expect(result.current.result).toBeNull();
    expect(result.current.run).toBeNull();
  });

  it("keeps an ApiError an ApiError, so the session guard still sees the status", async () => {
    createTransformerRunMock.mockRejectedValue(new ApiError("Not authenticated", 401));
    const { result } = renderHook(() => useTransformerSizing(), { wrapper: createWrapper() });

    await act(async () => {
      await result.current.calculate(request).catch(() => undefined);
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error).toBeInstanceOf(ApiError);
    expect((result.current.error as ApiError).status).toBe(401);
  });

  it("aborts the previous request when a new one is submitted", async () => {
    const signals: AbortSignal[] = [];
    createTransformerRunMock.mockImplementation((_payload, signal) => {
      if (signal) signals.push(signal);
      return new Promise<TransformerRunResponse>((resolve, reject) => {
        signal?.addEventListener("abort", () => reject(signal.reason), { once: true });
        setTimeout(() => resolve(runResponse), 5);
      });
    });
    const { result } = renderHook(() => useTransformerSizing(), { wrapper: createWrapper() });

    let first: Promise<TransformerRunResponse> | undefined;
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
    createTransformerRunMock.mockImplementation(
      (_payload, signal) =>
        new Promise<TransformerRunResponse>((_resolve, reject) => {
          captured = signal;
          signal?.addEventListener("abort", () => reject(signal.reason), { once: true });
        }),
    );
    const { result, unmount } = renderHook(() => useTransformerSizing(), {
      wrapper: createWrapper(),
    });

    act(() => {
      void result.current.calculate(request).catch(() => undefined);
    });
    await waitFor(() => expect(createTransformerRunMock).toHaveBeenCalledTimes(1));
    expect(captured?.aborted).toBe(false);

    unmount();

    expect(captured?.aborted).toBe(true);
  });

  it("clears result and error on reset", async () => {
    createTransformerRunMock.mockResolvedValue(runResponse);
    const { result } = renderHook(() => useTransformerSizing(), { wrapper: createWrapper() });

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
