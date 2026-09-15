// @vitest-environment node

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { calculateCableSizing, type CableSizingRequest } from "./cable";

const validRequest: CableSizingRequest = {
  code: "CBL-001",
  name: "Feeder to MCC-1",
  circuit: {
    design_current_a: "250",
    nominal_voltage_v: "415",
    route_length_m: "120",
    system: "THREE_PHASE_FOUR_WIRE",
    power_factor: "0.85",
    allowable_voltage_drop_percent: "3",
    fault_current_ka: "25",
    fault_duration_s: "0.5",
  },
  cable: {
    conductor_material: "COPPER",
    insulation_material: "XLPE",
    construction: "MULTICORE",
    arrangement: "MULTICORE",
    number_of_loaded_conductors: 3,
    parallel_runs: 1,
    neutral_required: true,
    protective_conductor_type: "METALLIC_ARMOUR",
    armoured: true,
  },
  installation: {
    method: "CABLE_TRAY",
    ambient_temperature_c: "40",
    ambient_derating_factor: "0.91",
    grouping_derating_factor: "0.8",
    grouped_circuits: 3,
  },
  size_schedule: {
    phase_sizes_mm2: ["70", "95", "120", "150", "185", "240"],
    neutral_sizes_mm2: ["35", "50", "70", "95", "120", "150"],
    protective_sizes_mm2: ["35", "50", "70", "95", "120"],
  },
  notes: "Feeder route via cable tray CT-01.",
};

const validResponse = {
  study_code: "CBL-001",
  status: "DESIGN_CHECK_PASSED",
  conductor: {
    phase_area_mm2: "150",
    neutral_area_mm2: "95",
    protective_area_mm2: "95",
    parallel_runs: 1,
    phase_conductors_per_run: 3,
    neutral_status: "PASS",
    protective_status: "PASS",
  },
  ampacity: {
    tabulated_ampacity_a_per_run: "380",
    combined_derating_factor: "0.728",
    derated_ampacity_a_per_run: "276.64",
    parallel_runs: 1,
    total_installed_ampacity_a: "276.64",
    design_current_a: "250",
    required_tabulated_ampacity_a_per_run: "343.41",
    utilization_ratio: "0.904",
    status: "PASS",
  },
  voltage_drop: {
    resistance_ohm_per_km: "0.159",
    reactance_ohm_per_km: "0.077",
    voltage_drop_v: "9.35",
    voltage_drop_percent: "2.25",
    allowable_voltage_drop_percent: "3",
    status: "PASS",
  },
  short_circuit: {
    fault_current_ka: "25",
    fault_duration_s: "0.5",
    material_constant_k: "143",
    required_area_mm2: "123.63",
    selected_area_mm2: "150",
    withstand_current_ka: "30.33",
    status: "PASS",
  },
  warnings: [
    {
      code: "HIGH_TOTAL_DERATING",
      message: "Combined derating factor 0.728 is below 0.75.",
      field_name: "installation",
    },
  ],
  standard_reference: "IEC 60364-5-52",
  ampacity_reference: "IEC 60287",
  notes: "Feeder route via cable tray CT-01.",
};

const fetchMock = vi.fn<typeof fetch>();

function mockPendingRequest() {
  fetchMock.mockImplementation(
    (_input, init) =>
      new Promise<Response>((_resolve, reject) => {
        const signal = init?.signal;

        if (!signal) {
          reject(new Error("Cable request must support cancellation."));
          return;
        }

        const rejectOnAbort = () => reject(signal.reason);

        if (signal.aborted) {
          rejectOnAbort();
        } else {
          signal.addEventListener("abort", rejectOnAbort, { once: true });
        }
      }),
  );
}

beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

describe("calculateCableSizing", () => {
  it("posts exact-decimal payload and returns a validated response", async () => {
    fetchMock.mockResolvedValue(Response.json(validResponse));

    await expect(calculateCableSizing(validRequest)).resolves.toEqual(validResponse);
    expect(fetchMock).toHaveBeenCalledTimes(1);

    const [url, init] = fetchMock.mock.calls[0] ?? [];
    expect(url).toBe("/api/v1/electrical/cable/calculate");
    expect(init?.method).toBe("POST");
    expect(init?.headers).toEqual({
      Accept: "application/json",
      "Content-Type": "application/json",
    });
    expect(init?.cache).toBe("no-store");
    expect(init?.signal).toBeInstanceOf(AbortSignal);
    expect(JSON.parse(String(init?.body))).toEqual(validRequest);
  });

  it("preserves warnings and notes exactly as returned", async () => {
    fetchMock.mockResolvedValue(Response.json(validResponse));

    const result = await calculateCableSizing(validRequest);

    expect(result.warnings).toEqual(validResponse.warnings);
    expect(result.notes).toBe(validResponse.notes);
  });

  it("rejects an unordered size schedule before calling the API", async () => {
    const invalidRequest: CableSizingRequest = {
      ...validRequest,
      size_schedule: {
        ...validRequest.size_schedule,
        phase_sizes_mm2: ["95", "70", "120"],
      },
    };

    await expect(calculateCableSizing(invalidRequest)).rejects.toThrow();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("rejects a non-decimal design current before calling the API", async () => {
    const invalidRequest = {
      ...validRequest,
      circuit: { ...validRequest.circuit, design_current_a: "250A" },
    } as CableSizingRequest;

    await expect(calculateCableSizing(invalidRequest)).rejects.toThrow();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("surfaces a backend 422 validation detail list", async () => {
    fetchMock.mockResolvedValue(
      Response.json(
        {
          detail: [
            {
              loc: ["body", "circuit", "design_current_a"],
              msg: "Input should be greater than 0",
              type: "greater_than",
            },
          ],
        },
        { status: 422 },
      ),
    );

    await expect(calculateCableSizing(validRequest)).rejects.toThrow(
      "body.circuit.design_current_a: Input should be greater than 0",
    );
  });

  it("surfaces a backend string detail", async () => {
    fetchMock.mockResolvedValue(
      Response.json({ detail: "phase_sizes_mm2 must be in ascending order" }, { status: 422 }),
    );

    await expect(calculateCableSizing(validRequest)).rejects.toThrow(
      "phase_sizes_mm2 must be in ascending order",
    );
  });

  it("falls back to a status message when the error body is not JSON", async () => {
    fetchMock.mockResolvedValue(new Response("upstream failure", { status: 502 }));

    await expect(calculateCableSizing(validRequest)).rejects.toThrow(
      "Cable sizing failed (HTTP 502).",
    );
  });

  it("rejects a malformed successful response", async () => {
    fetchMock.mockResolvedValue(
      Response.json({
        ...validResponse,
        status: "NOT_A_VALID_STATUS",
      }),
    );

    await expect(calculateCableSizing(validRequest)).rejects.toThrow(
      "Unexpected response from the KES Electrical OS cable API.",
    );
  });

  it("accepts a failed design check with null result sections", async () => {
    const failedResponse = {
      ...validResponse,
      status: "NO_STANDARD_SIZE_AVAILABLE",
      conductor: null,
      ampacity: null,
      voltage_drop: null,
      short_circuit: null,
      warnings: [
        {
          code: "NO_STANDARD_SIZE_AVAILABLE",
          message: "No size in the schedule satisfies all checks.",
          field_name: null,
        },
      ],
    };
    fetchMock.mockResolvedValue(Response.json(failedResponse));

    await expect(calculateCableSizing(validRequest)).resolves.toEqual(failedResponse);
  });

  it("cancels an in-flight request when the caller aborts", async () => {
    mockPendingRequest();
    const controller = new AbortController();
    const request = calculateCableSizing(validRequest, controller.signal);
    const rejection = expect(request).rejects.toMatchObject({ name: "AbortError" });

    controller.abort();

    await rejection;
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("times out after thirty seconds", async () => {
    vi.useFakeTimers();
    vi.spyOn(AbortSignal, "timeout").mockImplementation((milliseconds) => {
      const timeoutController = new AbortController();
      setTimeout(
        () =>
          timeoutController.abort(
            new DOMException("Request timed out", "TimeoutError"),
          ),
        milliseconds,
      );
      return timeoutController.signal;
    });
    mockPendingRequest();

    const request = calculateCableSizing(validRequest);
    const rejection = expect(request).rejects.toMatchObject({ name: "TimeoutError" });

    await vi.advanceTimersByTimeAsync(29_999);
    expect(fetchMock.mock.calls[0]?.[1]?.signal?.aborted).toBe(false);

    await vi.advanceTimersByTimeAsync(1);
    await rejection;
  });
});
