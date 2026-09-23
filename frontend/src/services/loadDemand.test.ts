// @vitest-environment node

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "./http";
import { createLoadRun, loadGroupRequestSchema, type LoadGroupRequest } from "./loadDemand";
import { AC_POWER_FACTOR_REQUIRED } from "./loadDemandContract";

const motorLoad = {
  code: "MTR-001",
  name: "Process Water Pump",
  quantity: 2,
  rated_power_kw: "15",
  phase_system: "THREE_PHASE",
  voltage_v: "415",
  power_factor: "0.85",
  efficiency: "0.92",
  utilization_factor: "0.80",
  demand_factor: "0.90",
  power_basis: "MECHANICAL_OUTPUT",
} as const;

const validRequest: LoadGroupRequest = {
  code: "LOAD-001",
  name: "Process Pump Loads",
  loads: [{ ...motorLoad }],
  coincidence_factor: "0.90",
};

// The exact JSON the backend returns for this study, taken from
// LoadGroupCalculationResponse at commit 2a25a8b.
const validResult = {
  group_code: "LOAD-001",
  group_name: "Process Pump Loads",
  coincidence_factor: "0.90",
  connected_power_kw: "32.6087",
  pre_coincidence_demand_kw: "23.4783",
  demand_power_kw: "21.1304",
  apparent_power_kva: "24.8593",
  reactive_power_kvar: "13.0955",
  load_results: [
    {
      load_code: "MTR-001",
      load_name: "Process Water Pump",
      scenario: "NORMAL",
      phase_system: "THREE_PHASE",
      connected_power_kw: "32.6087",
      utilized_power_kw: "26.0870",
      demand_power_kw: "23.4783",
      apparent_power_kva: "27.6215",
      reactive_power_kvar: "14.5505",
      design_current_a: "38.4272",
      status: "VALID",
      warnings: [],
    },
  ],
  status: "VALID",
  warnings: [],
  assumptions: [
    "The group coincidence factor is applied equally to active and reactive demand.",
  ],
  jurisdiction_profile: "IN",
};

const validRun = {
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
  calculated_by: "Test Engineer (engineer@example.com)",
  calculated_at: "2026-09-23T12:00:00+00:00",
  created_at: "2026-09-23T12:00:00+00:00",
  is_immutable: false,
  supersedes_run_id: null,
  notes: null,
};

const validRunResponse = { run: validRun, result: validResult };

const fetchMock = vi.fn<typeof fetch>();

beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

describe("loadGroupRequestSchema", () => {
  it("accepts a study whose factors are all established", () => {
    expect(loadGroupRequestSchema.parse(validRequest)).toEqual(validRequest);
  });

  it("refuses an AC load without a power factor, in the backend's words", () => {
    const parsed = loadGroupRequestSchema.safeParse({
      ...validRequest,
      loads: [{ ...motorLoad, power_factor: undefined }],
    });

    expect(parsed.success).toBe(false);
    if (!parsed.success) {
      expect(parsed.error.issues.map((issue) => issue.message)).toContain(
        AC_POWER_FACTOR_REQUIRED,
      );
    }
  });

  it("accepts a DC load without a power factor", () => {
    const parsed = loadGroupRequestSchema.safeParse({
      ...validRequest,
      loads: [
        {
          code: "DC-001",
          name: "DC Control Load",
          quantity: 1,
          rated_power_kw: "2.4",
          phase_system: "DC",
          voltage_v: "48",
          utilization_factor: "0.50",
          demand_factor: "0.75",
        },
      ],
    });

    expect(parsed.success).toBe(true);
  });

  it("refuses a DC load whose power factor is not 1", () => {
    const parsed = loadGroupRequestSchema.safeParse({
      ...validRequest,
      loads: [
        {
          code: "DC-001",
          name: "DC Control Load",
          quantity: 1,
          rated_power_kw: "2.4",
          phase_system: "DC",
          voltage_v: "48",
          power_factor: "0.9",
        },
      ],
    });

    expect(parsed.success).toBe(false);
    if (!parsed.success) {
      expect(parsed.error.issues.map((issue) => issue.message)).toContain(
        "DC loads must use a power_factor of 1",
      );
    }
  });

  it("leaves a blank factor out of the payload instead of sending 1", () => {
    const parsed = loadGroupRequestSchema.parse({
      code: "LOAD-002",
      name: "Unestablished Factors",
      loads: [
        {
          code: "MTR-002",
          name: "Pump",
          quantity: 1,
          rated_power_kw: "15",
          phase_system: "THREE_PHASE",
          voltage_v: "415",
          power_factor: "0.85",
        },
      ],
    });

    // NOT ESTABLISHED must reach the engine as an absent field, never as "1".
    expect(Object.keys(parsed)).not.toContain("coincidence_factor");
    expect(Object.keys(parsed.loads[0])).not.toContain("utilization_factor");
    expect(Object.keys(parsed.loads[0])).not.toContain("demand_factor");
    expect(Object.keys(parsed.loads[0])).not.toContain("efficiency");
  });

  it("refuses a key the backend does not accept", () => {
    expect(
      loadGroupRequestSchema.safeParse({ ...validRequest, diversity_factor: "0.9" }).success,
    ).toBe(false);
    expect(
      loadGroupRequestSchema.safeParse({
        ...validRequest,
        loads: [{ ...motorLoad, load_factor: "0.9" }],
      }).success,
    ).toBe(false);
  });

  it("refuses a group without loads", () => {
    expect(loadGroupRequestSchema.safeParse({ ...validRequest, loads: [] }).success).toBe(false);
  });
});

describe("createLoadRun", () => {
  it("posts the study to the runs endpoint and returns the run with its result", async () => {
    fetchMock.mockResolvedValue(Response.json(validRunResponse, { status: 201 }));

    await expect(createLoadRun(validRequest)).resolves.toEqual(validRunResponse);
    expect(fetchMock).toHaveBeenCalledTimes(1);

    const [url, init] = fetchMock.mock.calls[0] ?? [];
    expect(url).toBe("/api/v1/electrical/load-demand/runs");
    expect(init?.method).toBe("POST");
    expect(init?.headers).toEqual({
      Accept: "application/json",
      "Content-Type": "application/json",
    });
    expect(init?.cache).toBe("no-store");
    expect(init?.signal).toBeInstanceOf(AbortSignal);
    expect(JSON.parse(String(init?.body))).toEqual({ study: validRequest });
  });

  it("accepts the reused revision the backend answers with HTTP 200 (A11)", async () => {
    fetchMock.mockResolvedValue(Response.json(validRunResponse, { status: 200 }));

    await expect(createLoadRun(validRequest)).resolves.toEqual(validRunResponse);
  });

  it("sends the chosen project revision with the study", async () => {
    const revisionId = "b6b3f4d2-8a1c-4a5e-9a3b-2f7c1d0e5a44";
    fetchMock.mockResolvedValue(Response.json(validRunResponse, { status: 201 }));

    await createLoadRun(validRequest, undefined, revisionId);

    const [, init] = fetchMock.mock.calls[0] ?? [];
    expect(JSON.parse(String(init?.body))).toEqual({
      study: validRequest,
      project_revision_id: revisionId,
    });
  });

  it("parses a REVIEW_REQUIRED result with its not-established warning", async () => {
    const reviewed = {
      run: { ...validRun, design_check_status: "REVIEW_REQUIRED" },
      result: {
        ...validResult,
        coincidence_factor: "1",
        status: "REVIEW_REQUIRED",
        warnings: [
          {
            code: "COINCIDENCE_FACTOR_NOT_ESTABLISHED",
            message:
              "Group coincidence factor is not established; the calculation used 1. " +
              "The engineer must establish this factor.",
          },
        ],
      },
    };
    fetchMock.mockResolvedValue(Response.json(reviewed, { status: 201 }));

    const answer = await createLoadRun(validRequest);

    expect(answer.result.status).toBe("REVIEW_REQUIRED");
    expect(answer.result.warnings[0]?.code).toBe("COINCIDENCE_FACTOR_NOT_ESTABLISHED");
    expect(answer.run.design_check_status).toBe("REVIEW_REQUIRED");
  });

  it("raises an ApiError that keeps the HTTP status when the session is gone", async () => {
    fetchMock.mockResolvedValue(
      Response.json({ detail: "Not authenticated" }, { status: 401 }),
    );

    await expect(createLoadRun(validRequest)).rejects.toMatchObject({
      message: "Not authenticated",
      status: 401,
    });
    await expect(createLoadRun(validRequest)).rejects.toBeInstanceOf(ApiError);
  });

  it("rejects an invalid request before calling the API", async () => {
    const invalid = {
      ...validRequest,
      loads: [{ ...motorLoad, power_factor: undefined }],
    } as unknown as LoadGroupRequest;

    await expect(createLoadRun(invalid)).rejects.toThrow();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("raises a plain error when the answer does not match the contract", async () => {
    fetchMock.mockResolvedValue(
      Response.json({ run: validRun, result: { ...validResult, status: "PASS" } }),
    );

    await expect(createLoadRun(validRequest)).rejects.toThrow(
      "Unexpected response from the KES Electrical OS load runs API.",
    );
  });
});
