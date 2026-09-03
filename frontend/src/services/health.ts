import { z } from "zod";

const healthResponseSchema = z.object({
  status: z.literal("healthy"),
  application: z.literal("KES Electrical OS API"),
});

export type HealthResponse = z.infer<typeof healthResponseSchema>;

/** Check API availability; this endpoint does not verify database health. */
export async function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const timeoutSignal = AbortSignal.timeout(10_000);
  const requestSignal = signal
    ? AbortSignal.any([signal, timeoutSignal])
    : timeoutSignal;

  const response = await fetch("/api/v1/health", {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
    signal: requestSignal,
  });

  if (!response.ok) {
    throw new Error(`Health request failed (HTTP ${response.status}).`);
  }

  const data: unknown = await response.json();
  const parsed = healthResponseSchema.safeParse(data);

  if (!parsed.success) {
    throw new Error("Unexpected response from the KES Electrical OS health API.");
  }

  return parsed.data;
}
