// @vitest-environment node

import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, describeApiError, requestJson } from "./http";

describe("describeApiError", () => {
  it("uses the server's own sentence when the detail is text", () => {
    expect(describeApiError({ detail: "Sign-in failed. Check the e-mail." }, 401, "Fallback")).toBe(
      "Sign-in failed. Check the e-mail.",
    );
  });

  it("joins validation messages and drops the validator prefix", () => {
    const data = {
      detail: [
        { loc: ["body", "email"], msg: "Value error, E-mail is required.", type: "value_error" },
        { loc: ["body", "password"], msg: "Field required", type: "missing" },
      ],
    };

    expect(describeApiError(data, 422, "Fallback")).toBe("E-mail is required. Field required");
  });

  it("falls back to a sentence with the status when the body is not an API error", () => {
    expect(describeApiError(null, 502, "Sign-in failed")).toBe("Sign-in failed (HTTP 502).");
    expect(describeApiError({ unexpected: true }, 500, "Sign-in failed")).toBe(
      "Sign-in failed (HTTP 500).",
    );
  });
});

describe("ApiError", () => {
  it("carries the HTTP status next to the message", () => {
    const error = new ApiError("Sign in to continue.", 401);

    expect(error).toBeInstanceOf(Error);
    expect(error.name).toBe("ApiError");
    expect(error.message).toBe("Sign in to continue.");
    expect(error.status).toBe(401);
  });
});

describe("requestJson", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("sends a same-origin JSON request and returns status and data", async () => {
    const fetchMock = vi.fn<typeof fetch>(async () => Response.json({ ok: 1 }, { status: 201 }));
    vi.stubGlobal("fetch", fetchMock);

    const response = await requestJson("/api/v1/thing", { method: "POST", body: { a: "b" } });

    expect(response).toEqual({ status: 201, ok: true, data: { ok: 1 } });
    const [url, init] = fetchMock.mock.calls[0] ?? [];
    expect(url).toBe("/api/v1/thing");
    expect(init?.method).toBe("POST");
    expect(init?.body).toBe('{"a":"b"}');
    expect(init?.credentials).toBe("same-origin");
    expect(init?.cache).toBe("no-store");
    expect(init?.headers).toEqual({
      Accept: "application/json",
      "Content-Type": "application/json",
    });
  });

  it("sends no body and no content type on a request without data", async () => {
    const fetchMock = vi.fn<typeof fetch>(async () => new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetchMock);

    const response = await requestJson("/api/v1/thing", { method: "GET" });

    expect(response).toEqual({ status: 204, ok: true, data: null });
    const [, init] = fetchMock.mock.calls[0] ?? [];
    expect(init?.body).toBeUndefined();
    expect(init?.headers).toEqual({ Accept: "application/json" });
  });
});
