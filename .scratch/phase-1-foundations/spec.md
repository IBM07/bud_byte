# Phase 1: Foundations

Status: claimed
Plan: `C:\Users\Ibrahim Aejaz\.claude\plans\you-are-s-senior-greedy-zebra.md` (approved 2026-11-15), §1, §2 and §10.

## Goal
Get a deployable end-to-end skeleton working before any features: Telegram → api → Redis → worker → Postgres → Telegram reply, plus a web page showing api health, green CI, and a Playwright smoke test.

## In scope
- Monorepo scaffold: uv workspace (Python), pnpm workspace (TS), root `justfile`, MIT license, README, `.editorconfig`.
- `services/api`:
  - FastAPI app factory with typed settings and structured JSON logging.
  - Sentry hook, active only when a DSN is set.
  - `/healthz` (liveness) and `/readyz` (Postgres + Redis).
  - `POST /tg/webhook/{path_secret}` checks the secret header, de-duplicates `update_id` and enqueues the job.
  - Worker entrypoint: Redis queue consumer that replies `pong + DB time`.
  - Cron entrypoints (`nightly`, `maint`) as logged no-ops.
  - Alembic baseline with the `vector` and `pgcrypto` extensions, run at startup under an advisory lock.
- `apps/web`: Next.js page showing api health through the `/api/*` rewrite.
- `packages/api-client`: generated from OpenAPI (`just gen`), with a CI freshness check.
- `infra/`:
  - Multi-stage `Dockerfile` (uv).
  - `compose.yml` with pgvector and Redis.
  - `.env.example`.
  - Northflank setup notes and a Render fallback blueprint.
- CI (`.github/workflows/ci.yml`):
  - Python: ruff, pyright, pytest with Postgres and Redis service containers.
  - Web: lint, typecheck, build, Playwright smoke.
  - Codegen freshness, gitleaks and Docker build.
- `.coderabbit.yaml`.
- ADRs: hosting/architecture, LLM gateway, monorepo tooling.
- `CLAUDE.md` provider fix and layout pointers.
- Spikes, each recorded in `docs/spikes/`:
  - fastembed RAM
  - free magic-link email path
  - Northflank Redis addon and pgvector
  - Tauri + Python sidecar feasibility

## Out of scope
Auth, the LLM gateway, agents, memory, UI design system, and the desktop daemon. Those are Phases 2–6.

## Exit criteria
1. `just check` is green locally: ruff, pyright, the unit tests, and the web lint, typecheck and build.
2. CI is green on the branch.
3. Integration tests (real Postgres and Redis) pass in CI.
4. Playwright smoke passes: the page renders and shows the api status.
5. **Deployed check:** a Telegram message to the bot gets "pong + DB time", and the Vercel page shows api health. This is blocked on the user creating the accounts and tokens; see `docs/runbooks/deploy.md`.

## User-gated steps
Only the user can do these:
- Create the accounts: Northflank, Neon, Vercel, Sentry and Langfuse.
- Create the Telegram bot with BotFather.
- Install the CodeRabbit GitHub App.
- Push the branch and open the PR.
- Enter secrets into Northflank and Vercel.
