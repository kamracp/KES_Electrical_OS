// @vitest-environment node

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { getHealth } from "./health";

const healthyResponse = {
  status: "healthy",
  application: "KES Electrical OS API",
};

const fetchMock = vi.fn<typeof fetch>();

function mockPendingRequest() {
  fetchMock.mockImplementation(
    (_input, init) =>
      new Promise<Response>((_resolve, reject) => {
        const signal = init?.signal;

        if (!signal) {
          reject(new Error("The health request must support cancellation."));
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

describe("getHealth", () => {
  it("returns validated API health using an uncached JSON request", async () => {
    fetchMock.mockResolvedValue(Response.json(healthyResponse));

    await expect(getHealth()).resolves.toEqual(healthyResponse);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith("/api/v1/health", {
      method: "GET",
      headers: { Accept: "application/json" },
      cache: "no-store",
      signal: expect.any(AbortSignal),
    });
  });

  it.each([401, 503])("rejects HTTP %s even with a healthy-looking body", async (status) => {
    fetchMock.mockResolvedValue(Response.json(healthyResponse, { status }));

    await expect(getHealth()).rejects.toThrow(`Health request failed (HTTP ${status}).`);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it.each([
    { label: "null response", body: null },
    { label: "missing application", body: { status: "healthy" } },
    {
      label: "unhealthy status",
      body: { ...healthyResponse, status: "unhealthy" },
    },
    {
      label: "another application",
      body: { ...healthyResponse, application: "Another API" },
    },
  ])("rejects $label", async ({ body }) => {
    fetchMock.mockResolvedValue(Response.json(body));

    await expect(getHealth()).rejects.toThrow(
      "Unexpected response from the KES Electrical OS health API.",
    );
  });

  it("rejects an HTML response instead of treating HTTP 200 as healthy", async () => {
    fetchMock.mockResolvedValue(
      new Response("<!doctype html><title>Frontend</title>", {
        headers: { "Content-Type": "text/html" },
      }),
    );

    await expect(getHealth()).rejects.toBeInstanceOf(SyntaxError);
  });

  it("propagates a network failure without retrying", async () => {
    const failure = new TypeError("Network unavailable");
    fetchMock.mockRejectedValue(failure);

    await expect(getHealth()).rejects.toBe(failure);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("cancels an in-flight request when the caller aborts", async () => {
    mockPendingRequest();
    const controller = new AbortController();
    const request = getHealth(controller.signal);
    const rejection = expect(request).rejects.toMatchObject({ name: "AbortError" });

    controller.abort();

    await rejection;
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("rejects when the caller signal was already aborted", async () => {
    mockPendingRequest();
    const controller = new AbortController();
    controller.abort();

    await expect(getHealth(controller.signal)).rejects.toMatchObject({
      name: "AbortError",
    });
  });

  it.each([false, true])(
    "times out after ten seconds (caller signal supplied: %s)",
    async (withCallerSignal) => {
      vi.useFakeTimers();
      // Native AbortSignal timers do not use Vitest's simulated clock.
      vi.spyOn(AbortSignal, "timeout").mockImplementation((milliseconds) => {
        const timeoutController = new AbortController();
        setTimeout(
          () => timeoutController.abort(new DOMException("Request timed out", "TimeoutError")),
          milliseconds,
        );
        return timeoutController.signal;
      });
      mockPendingRequest();
      const caller = new AbortController();
      const request = getHealth(withCallerSignal ? caller.signal : undefined);
      const rejection = expect(request).rejects.toMatchObject({ name: "TimeoutError" });
      const requestSignal = fetchMock.mock.calls[0]?.[1]?.signal;

      await vi.advanceTimersByTimeAsync(9_999);
      expect(requestSignal?.aborted).toBe(false);

      await vi.advanceTimersByTimeAsync(1);
      await rejection;
      expect(requestSignal?.aborted).toBe(true);
      expect(caller.signal.aborted).toBe(false);
      expect(fetchMock).toHaveBeenCalledTimes(1);
    },
  );
});
