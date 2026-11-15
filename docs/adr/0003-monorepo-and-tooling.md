# 3. Monorepo layout and tooling

Date: 2026-11-15 · Status: accepted

## Decision
- **One repo, two languages.**
  - Python: a uv workspace (`services/api`, later `services/daemon` and `packages/protocol`).
  - TypeScript: a pnpm workspace (`apps/web`, `packages/api-client`, later `apps/desktop` and `packages/ui`).
  - A root `justfile` is the single entry point (`just check`, `just gen`, `just e2e`).
  - No Turborepo: there are too few TS packages to justify it.
- **Python:** `src/` layout, package `budbyte_api`.
  - Tooling: ruff (lint and format), pyright strict, pytest + pytest-asyncio.
  - Real Postgres and Redis integration tests run in CI service containers; they auto-skip locally without `BUDBYTE_TEST_*` env.
  - Alembic migrations ship inside the package and run at api startup under a Postgres advisory lock.
- **Contracts:** FastAPI's OpenAPI schema generates `@budbyte/api-client` (openapi-typescript + openapi-fetch). CI fails if the generated files drift.
- **Web:** Next.js 16 with Cache Components. Uncached data reads sit in `<Suspense>`. Server-side calls use `API_BASE_URL`; browser calls use `/api/*` rewrites.
- **Quality gates:** CI runs lint, types, unit and integration tests, Playwright smoke, codegen drift, gitleaks and the Docker build. CodeRabbit reviews every PR. `/code-review` and `/security-review` run locally before each PR.

## Consequences
- Generated code (`packages/api-client/src/schema.d.ts`, `openapi.json`) is committed and excluded from review noise.
- New Python services join the uv workspace and reuse the same lint and type settings from the root `pyproject.toml`.
