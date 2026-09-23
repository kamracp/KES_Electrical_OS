// @vitest-environment node

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "./http";
import {
  createTransformerRun,
  transformerRunCreateRequestSchema,
  type TransformerRunCreateRequest,
  type TransformerSizingRequest,
} from "./transformerSizing";

const validStudy: TransformerSizingRequest = {
  code: "TR-001",
  name: "Main Transformer",
  demand_power_kw: "800",
  demand_power_factor: "0.80",
  available_unit_ratings_kva: ["1000", "1250", "1600"],
  future_growth_factor: "1",
  design_margin_factor: "1.10",
  ambient_derating_factor: "1",
  altitude_derating_factor: "1",
  harmonic_derating_factor: "1",
};

const validRunRequest: TransformerRunCreateRequest = { study: validStudy };

// The exact JSON the backend returns for this study, taken from
// TransformerSizingResponse at commit 7853d51.
const validResult = {
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
};

const validRun = {
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

describe("transformerRunCreateRequestSchema", () => {
  it("accepts a study whose factors are all established", () => {
    expect(transformerRunCreateRequestSchema.parse(validRunRequest)).toEqual(validRunRequest);
  });

  it("refuses a study without a demand power factor", () => {
    const parsed = transformerRunCreateRequestSchema.safeParse({
      study: { ...validStudy, demand_power_factor: undefined },
    });

    expect(parsed.success).toBe(false);
    if (!parsed.success) {
      const issue = parsed.error.issues[0];
      expect(issue.path).toEqual(["study", "demand_power_factor"]);
      // Reported as a missing value, so a form reads it as "... is required."
      expect(issue.code).toBe("invalid_type");
    }
  });

  it("leaves a blank factor out of the payload instead of sending 1", () => {
    const parsed = transformerRunCreateRequestSchema.parse({
      study: {
        code: "TR-002",
        name: "Unestablished Factors",
        demand_power_kw: "800",
        demand_power_factor: "0.80",
        available_unit_ratings_kva: ["1000"],
      },
    });

    // NOT ESTABLISHED must reach the engine as an absent field, never as "1".
    for (const key of [
      "future_growth_factor",
      "design_margin_factor",
      "ambient_derating_factor",
      "altitude_derating_factor",
      "harmonic_derating_factor",
    ]) {
      expect(Object.keys(parsed.study)).not.toContain(key);
    }
  });

  it("refuses a study with no available ratings", () => {
    expect(
      transformerRunCreateRequestSchema.safeParse({
        study: { ...validStudy, available_unit_ratings_kva: [] },
      }).success,
    ).toBe(false);
  });

  it("refuses a key the backend does not accept", () => {
    expect(
      transformerRunCreateRequestSchema.safeParse({
        study: { ...validStudy, loading_limit_percent: "90" },
      }).success,
    ).toBe(false);
    expect(
      transformerRunCreateRequestSchema.safeParse({
        study: validStudy,
        revision_id: "48a782d0-4331-4aa2-bcd0-f24f5016334a",
      }).success,
    ).toBe(false);
  });
});

describe("createTransformerRun", () => {
  it("posts the run request and returns the run with its result", async () => {
    fetchMock.mockResolvedValue(Response.json(validRunResponse, { status: 201 }));

    await expect(createTransformerRun(validRunRequest)).resolves.toEqual(validRunResponse);
    expect(fetchMock).toHaveBeenCalledTimes(1);

    const [url, init] = fetchMock.mock.calls[0] ?? [];
    expect(url).toBe("/api/v1/electrical/transformer-sizing/runs");
    expect(init?.method).toBe("POST");
    expect(init?.headers).toEqual({
      Accept: "application/json",
      "Content-Type": "application/json",
    });
    expect(init?.cache).toBe("no-store");
    expect(init?.signal).toBeInstanceOf(AbortSignal);
    expect(JSON.parse(String(init?.body))).toEqual({ study: validStudy });
    expect(Object.keys(JSON.parse(String(init?.body)))).not.toContain("project_revision_id");
  });

  it("carries the run's own notes, which the study itself has no field for", async () => {
    fetchMock.mockResolvedValue(Response.json(validRunResponse, { status: 201 }));

    await createTransformerRun({ study: validStudy, notes: "Preliminary sizing." });

    const [, init] = fetchMock.mock.calls[0] ?? [];
    expect(JSON.parse(String(init?.body))).toEqual({
      study: validStudy,
      notes: "Preliminary sizing.",
    });
  });

  it("accepts the reused revision the backend answers with HTTP 200 (A11)", async () => {
    fetchMock.mockResolvedValue(Response.json(validRunResponse, { status: 200 }));

    await expect(createTransformerRun(validRunRequest)).resolves.toEqual(validRunResponse);
  });

  it("sends the chosen project revision with the study", async () => {
    const revisionId = "b6b3f4d2-8a1c-4a5e-9a3b-2f7c1d0e5a44";
    fetchMock.mockResolvedValue(Response.json(validRunResponse, { status: 201 }));

    await createTransformerRun(validRunRequest, undefined, revisionId);

    const [, init] = fetchMock.mock.calls[0] ?? [];
    expect(JSON.parse(String(init?.body))).toEqual({
      study: validStudy,
      project_revision_id: revisionId,
    });
  });

  it("parses a REVIEW_REQUIRED result with its not-established warning", async () => {
    const reviewed = {
      run: { ...validRun, design_check_status: "REVIEW_REQUIRED" },
      result: {
        ...validResult,
        design_margin_factor: "1",
        design_required_kva: "1000.0000",
        status: "REVIEW_REQUIRED",
        warnings: [
          {
            code: "DESIGN_MARGIN_NOT_ESTABLISHED",
            message:
              "Design margin factor is not established; the calculation used 1. " +
              "The engineer must establish this factor.",
          },
        ],
      },
    };
    fetchMock.mockResolvedValue(Response.json(reviewed, { status: 201 }));

    const answer = await createTransformerRun(validRunRequest);

    expect(answer.result.status).toBe("REVIEW_REQUIRED");
    expect(answer.result.warnings[0]?.code).toBe("DESIGN_MARGIN_NOT_ESTABLISHED");
    expect(answer.result.design_margin_factor).toBe("1");
  });

  it("parses a NO_SOLUTION result whose capacity fields are null", async () => {
    const noSolution = {
      run: { ...validRun, design_check_status: "NO_SOLUTION" },
      result: {
        ...validResult,
        selected_unit_rating_kva: null,
        installed_nameplate_capacity_kva: null,
        derated_duty_capacity_kva: null,
        spare_derated_capacity_kva: null,
        loading_percent: null,
        status: "NO_SOLUTION",
        warnings: [
          {
            code: "NO_STANDARD_RATING_AVAILABLE",
            message: "No available transformer unit rating satisfies the requirement.",
          },
        ],
      },
    };
    fetchMock.mockResolvedValue(Response.json(noSolution, { status: 201 }));

    const answer = await createTransformerRun(validRunRequest);

    expect(answer.result.status).toBe("NO_SOLUTION");
    expect(answer.result.selected_unit_rating_kva).toBeNull();
    expect(answer.result.loading_percent).toBeNull();
  });

  it("raises an ApiError that keeps the HTTP status when the session is gone", async () => {
    fetchMock.mockResolvedValue(
      Response.json({ detail: "Not authenticated" }, { status: 401 }),
    );

    await expect(createTransformerRun(validRunRequest)).rejects.toMatchObject({
      message: "Not authenticated",
      status: 401,
    });
    await expect(createTransformerRun(validRunRequest)).rejects.toBeInstanceOf(ApiError);
  });

  it("rejects an invalid request before calling the API", async () => {
    const invalid = {
      study: { ...validStudy, demand_power_factor: undefined },
    } as unknown as TransformerRunCreateRequest;

    await expect(createTransformerRun(invalid)).rejects.toThrow();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("raises a plain error when the answer does not match the contract", async () => {
    fetchMock.mockResolvedValue(
      Response.json({ run: validRun, result: { ...validResult, status: "PASS" } }),
    );

    await expect(createTransformerRun(validRunRequest)).rejects.toThrow(
      "Unexpected response from the KES Electrical OS transformer runs API.",
    );
  });
});
