import "server-only";

import { createApiClient, type Health, type Readiness } from "@budbyte/api-client";

const TIMEOUT_MS = 3000;

function serverClient() {
  const baseUrl = process.env.API_BASE_URL ?? "http://localhost:8000";
  return createApiClient(baseUrl, {
    fetch: (input) =>
      fetch(input, { cache: "no-store", signal: AbortSignal.timeout(TIMEOUT_MS) }),
  });
}

export type ApiStatus =
  | { state: "up"; health: Health; readiness: Readiness; ready: boolean }
  | { state: "down"; reason: string };

function asReadiness(value: unknown): Readiness | undefined {
  if (typeof value !== "object" || value === null) return undefined;
  const v = value as Partial<Readiness>;
  const okStatus = v.status === "ok" || v.status === "degraded";
  const okChecks =
    typeof v.checks === "object" &&
    v.checks !== null &&
    Object.values(v.checks).every((c) => typeof c === "string");
  return okStatus && okChecks ? (v as Readiness) : undefined;
}

/** Fetch liveness + readiness. Never throws: an unreachable API is a state, not a crash. */
export async function getApiStatus(): Promise<ApiStatus> {
  const api = serverClient();
  try {
    const [health, ready] = await Promise.all([api.GET("/healthz"), api.GET("/readyz")]);
    if (!health.data) {
      return { state: "down", reason: `healthz returned ${health.response.status}` };
    }
    // /readyz answers 503 with the same body shape when a dependency is down. Anything else
    // (proxy error page, 500 text) is validated away rather than trusted.
    const readiness = asReadiness(ready.data ?? ready.error);
    if (!readiness) {
      return { state: "down", reason: `readyz returned ${ready.response.status}` };
    }
    return { state: "up", health: health.data, readiness, ready: ready.response.ok };
  } catch (err) {
    const reason = err instanceof Error ? err.name : "unknown error";
    return { state: "down", reason };
  }
}
