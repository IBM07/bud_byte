# BudByte

> Your buddy that remembers, nudges and does.

BudByte is an open-source AI companion for forgetful and busy people. Tell it things once and it remembers them. It notices the promises you make, nudges you at the right moment, and with your approval does tasks on your Windows PC. You can control all of it from Telegram while you're away.

**Status:** Phase 1 (foundations) of 8. Not usable yet. See the [roadmap](#roadmap).

## Architecture
```
Telegram ─┐                    ┌─ Redis (queues, rate limits, scheduler)   [Northflank addon]
Web app ──┼─► FastAPI api ─────┤
Desktop ──┘   (Northflank)     └─ Postgres + pgvector (memory, checkpoints) [Neon]
                  │
                  └─► worker: LangGraph agents · LLM gateway (free multi-provider fallback)
```
Design decisions live in [`docs/adr/`](docs/adr). Everything runs on free tiers that need no credit card.

## Repository layout
| Path | What |
|---|---|
| `services/api` | Python 3.12 · FastAPI api, worker, cron entrypoints, Alembic migrations |
| `apps/web` | Next.js 16 web app (Vercel) |
| `packages/api-client` | Typed TS client generated from the OpenAPI schema |
| `infra/` | Dockerfile, local compose stack, fallback Render blueprint |
| `docs/` | ADRs, runbooks, spikes, retros, agent conventions |
| `.scratch/` | Specs and tickets (local markdown tracker) |

## Develop
Prerequisites: Python 3.12, [uv](https://docs.astral.sh/uv/), Node 22 + pnpm, [just](https://just.systems). Docker is optional; it's used for the local Postgres and Redis.

```bash
just setup        # install Python + JS deps
cp .env.example .env
just check        # lint, types, unit tests, web build, codegen drift
just e2e          # Playwright smoke test
docker compose -f infra/compose.yml up -d db redis   # optional: real deps (background)
just dev-api      # http://localhost:8000/docs
just dev-worker
just dev-web      # http://localhost:3000
```

Deploying: [`docs/runbooks/deploy.md`](docs/runbooks/deploy.md).

## Roadmap
1. **Foundations**: scaffold, CI, deploy skeleton (in progress)
2. Auth (Telegram + magic link), LLM gateway, chat
3. Memory + "Where was I?"
4. Commitments and adaptive nudges
5. Design system and app UI
6. Windows desktop daemon (approved actions)
7. Self-improving loop and hardening
8. Beta and launch

## Privacy
Your data is stored on our servers, and some free LLM providers we use may train on prompts. A full `PRIVACY.md` ships before launch.

## License
[MIT](LICENSE)
