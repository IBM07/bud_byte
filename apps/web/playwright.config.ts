import { defineConfig, devices } from "@playwright/test";

const PORT = Number(process.env.WEB_PORT ?? 3100);
const MOCK_API_PORT = Number(process.env.MOCK_API_PORT ?? 8765);

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI ? [["github"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: process.env.E2E_BASE_URL ?? `http://localhost:${PORT}`,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  // When E2E_BASE_URL is set (e.g. a Vercel preview) we test that instead of local servers.
  webServer: process.env.E2E_BASE_URL
    ? undefined
    : [
        {
          command: "node e2e/mock-api.mjs",
          url: `http://localhost:${MOCK_API_PORT}/healthz`,
          env: { MOCK_API_PORT: String(MOCK_API_PORT) },
          reuseExistingServer: !process.env.CI,
        },
        {
          command: `pnpm build && pnpm start --port ${PORT}`,
          url: `http://localhost:${PORT}`,
          env: { API_BASE_URL: `http://localhost:${MOCK_API_PORT}` },
          timeout: 180_000,
          reuseExistingServer: !process.env.CI,
        },
      ],
});
