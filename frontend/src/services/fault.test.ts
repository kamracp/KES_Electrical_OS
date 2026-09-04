// @vitest-environment node

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { calculateFaultStudy, type ShortCircuitStudyRequest } from "./fault";

const validRequest: ShortCircuitStudyRequest = {
  code: "FAULT-001",
  name: "Main LV Bus Fault Study",
  calculation_case: "MAXIMUM",
  fault: {
    bus_code: "BUS-1",
    fault_type: "THREE_PHASE",
    fault_resistance_ohm: "0",
    fault_reactance_ohm: "0",
  },
  buses: [
    {
      code: "BUS-1",
      name: "Main LV Bus",
      nominal_voltage_v: "415",
      voltage_factor_max: "1.10",
      voltage_factor_min: "0.95",
      neutral_earthing_mode: "SOLIDLY_EARTHED",
    },
  ],
  sources: [
    {
      code: "GRID-1",
      name: "Utility Grid",
      bus_code: "BUS-1",
      source_type: "UTILITY_GRID",
      representation: "VOLTAGE_BEHIND_IMPEDANCE",
      positive_sequence_impedance: {
        resistance_ohm: "0.01",
        reactance_ohm: "0.02",
      },
    },
  ],
};

const validResponse = {
  study_code: "FAULT-001",
  study_name: "Main LV Bus Fault Study",
  calculation_case: "MAXIMUM",
  fault_bus_code: "BUS-1",
  fault_type: "THREE_PHASE",
  nominal_voltage_v: "415",
  frequency_hz: "50",
  status: "CALCULATED",
  initial_symmetrical_short_circuit_current_ka: "10.5",
  peak_short_circuit_current_ka: null,
  symmetrical_breaking_current_ka: null,
  steady_state_short_circuit_current_ka: null,
  thermal_equivalent_short_circuit_current_ka: null,
  earth_fault_current_ka: null,
  kappa_factor: null,
  x_r_ratio: null,
  clearing_time_s: null,
  sequence_results: [],
  source_contributions: [],
  warnings: [],
  standard_reference: "IEC 60909-0:2026",
  earth_current_reference: "IEC 60909-3:2009",
  operating_state_code: null,
  notes: null,
};

const fetchMock = vi.fn<typeof fetch>();

function mockPendingRequest() {
  fetchMock.mockImplementation(
    (_input, init) =>
      new Promise<Response>((_resolve, reject) => {
        const signal = init?.signal;

        if (!signal) {
          reject(new Error("Fault request must support cancellation."));
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

describe("calculateFaultStudy", () => {
  it("posts exact-decimal payload and returns a validated response", async () => {
    fetchMock.mockResolvedValue(Response.json(validResponse));

    await expect(calculateFaultStudy(validRequest)).resolves.toEqual(validResponse);
    expect(fetchMock).toHaveBeenCalledTimes(1);

    const [url, init] = fetchMock.mock.calls[0] ?? [];
    expect(url).toBe("/api/v1/electrical/fault/calculate");
    expect(init?.method).toBe("POST");
    expect(init?.headers).toEqual({
      Accept: "application/json",
      "Content-Type": "application/json",
    });
    expect(init?.cache).toBe("no-store");
    expect(init?.signal).toBeInstanceOf(AbortSignal);
    expect(JSON.parse(String(init?.body))).toEqual(validRequest);
  });

  it("rejects an invalid request before calling the API", async () => {
    const invalidRequest = {
      ...validRequest,
      buses: [],
    } as ShortCircuitStudyRequest;

    await expect(calculateFaultStudy(invalidRequest)).rejects.toThrow();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("surfaces a backend 422 validation detail", async () => {
    fetchMock.mockResolvedValue(
      Response.json(
        {
          detail: [
            {
              loc: ["body", "sources", 0, "current_contribution_ka"],
              msg: "Input should be greater than 0",
              type: "greater_than",
            },
          ],
        },
        { status: 422 },
      ),
    );

    await expect(calculateFaultStudy(validRequest)).rejects.toThrow(
      "body.sources.0.current_contribution_ka: Input should be greater than 0",
    );
  });

  it("rejects a malformed successful response", async () => {
    fetchMock.mockResolvedValue(
      Response.json({
        ...validResponse,
        status: "NOT_A_VALID_STATUS",
      }),
    );

    await expect(calculateFaultStudy(validRequest)).rejects.toThrow(
      "Unexpected response from the KES Electrical OS fault API.",
    );
  });

  it("cancels an in-flight request when the caller aborts", async () => {
    mockPendingRequest();
    const controller = new AbortController();
    const request = calculateFaultStudy(validRequest, controller.signal);
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

    const request = calculateFaultStudy(validRequest);
    const rejection = expect(request).rejects.toMatchObject({ name: "TimeoutError" });

    await vi.advanceTimersByTimeAsync(29_999);
    expect(fetchMock.mock.calls[0]?.[1]?.signal?.aborted).toBe(false);

    await vi.advanceTimersByTimeAsync(1);
    await rejection;
    expect(fetchMock.mock.calls[0]?.[1]?.signal?.aborted).toBe(true);
  });
});
