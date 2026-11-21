# @budbyte/web

Next.js 16 web app for BudByte (landing page + app). See the root `README.md`.

- `pnpm dev`: local dev server (expects the API at `API_BASE_URL`, default `http://localhost:8000`). Set it in `apps/web/.env.local`: Next.js does not read the repo-root `.env`.
- `pnpm test:e2e`: Playwright smoke test (starts a mock API)

UI rules: `docs/agents/ui.md`. Phase 1 page is a placeholder; the design system lands in Phase 5.
