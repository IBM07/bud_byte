import createClient from "openapi-fetch";

import type { components, paths } from "./schema";

export type { components, paths };
export type Health = components["schemas"]["Health"];
export type Readiness = components["schemas"]["Readiness"];

/** Typed client for the BudByte API. Generated types come from `just gen`. */
export function createApiClient(baseUrl: string, init?: { fetch?: typeof fetch }) {
  return createClient<paths>({ baseUrl: baseUrl.replace(/\/$/, ""), fetch: init?.fetch });
}

export type ApiClient = ReturnType<typeof createApiClient>;
