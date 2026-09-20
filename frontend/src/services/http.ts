import { z } from "zod";

// Shared HTTP helpers for the API services.
//
// ApiError keeps the HTTP status next to the readable message, so callers can tell
// "not signed in" (401) and "not allowed" (403) from an ordinary failure without parsing text.

export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

const errorDetailSchema = z.union([
  z.string(),
  z.array(
    z
      .object({
        loc: z.array(z.union([z.string(), z.number()])),
        msg: z.string(),
      })
      .passthrough(),
  ),
]);

const errorResponseSchema = z.object({ detail: errorDetailSchema });

// pydantic prefixes messages raised by validators; the prefix says nothing to a user.
const VALIDATOR_PREFIX = /^Value error, /;

/** The server's own message when there is one, otherwise the fallback with the status. */
export function describeApiError(data: unknown, status: number, fallback: string): string {
  const parsed = errorResponseSchema.safeParse(data);

  if (!parsed.success) {
    return `${fallback} (HTTP ${status}).`;
  }

  if (typeof parsed.data.detail === "string") {
    return parsed.data.detail;
  }

  return parsed.data.detail.map((item) => item.msg.replace(VALIDATOR_PREFIX, "")).join(" ");
}

type JsonRequest = {
  method: "GET" | "POST" | "PATCH";
  body?: unknown;
  signal?: AbortSignal | undefined;
  timeoutMs?: number;
};

export type JsonResponse = {
  status: number;
  ok: boolean;
  data: unknown;
};

/** One same-origin JSON request; the session cookie travels with it automatically. */
export async function requestJson(url: string, request: JsonRequest): Promise<JsonResponse> {
  const timeoutSignal = AbortSignal.timeout(request.timeoutMs ?? 30_000);
  const signal = request.signal ? AbortSignal.any([request.signal, timeoutSignal]) : timeoutSignal;
  const hasBody = request.body !== undefined;

  const response = await fetch(url, {
    method: request.method,
    headers: hasBody
      ? { Accept: "application/json", "Content-Type": "application/json" }
      : { Accept: "application/json" },
    ...(hasBody ? { body: JSON.stringify(request.body) } : {}),
    cache: "no-store",
    credentials: "same-origin",
    signal,
  });

  const data: unknown = await response.json().catch(() => null);

  return { status: response.status, ok: response.ok, data };
}
