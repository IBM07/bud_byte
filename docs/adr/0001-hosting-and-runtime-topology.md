# 1. Hosting and runtime topology

Date: 2026-11-15 · Status: accepted

## Context
The whole system has to run on free tiers with no credit card, stay always reachable for Telegram and the desktop daemon, and be production-ready from day one. In November 2026 these options were verified as unsuitable:
- Koyeb, Fly.io, Railway and Cloud Run end up needing a card.
- Hugging Face Docker Spaces are paid.
- Render's free Postgres is deleted after 30 days.
- Cloudflare Workers have a 10 ms CPU limit, which rules out Python agents.

## Decision
| Piece | Host |
|---|---|
| `api` + `worker` (same Docker image) | Northflank Sandbox, 2 services, always on |
| `cron-nightly`, `cron-maint` | Northflank, 2 cron jobs (same image) |
| Redis (queues, rate limits, locks, cache) | Northflank addon (the single database slot) |
| Postgres 17 + pgvector | Neon Free |
| Web (Next.js) | Vercel Hobby. `/api/*` is rewritten to the api so cookies stay first-party. |

There is **no Cloudflare Worker**. The always-on api receives the Telegram webhook directly, so a second runtime would only add a deploy and a place for secrets.

## Consequences
- **Fewer moving parts:** one image, one config schema (`BUDBYTE_*` env).
- **Neon budget:** 100 CU-h/month and scale-to-zero, so nothing may poll Postgres. Scheduling uses Redis, and connections are short-lived (`pool_recycle=300`).
- **Fallback:** Render free (`infra/render.yaml`). The worker would run in-process behind a flag, and crons would move to GitHub Actions. **Status:** that flag (`BUDBYTE_INPROCESS_WORKER`) is planned for Phase 2 and not built yet, so a Render deploy today runs the API with no worker: Telegram updates are queued but never processed. Do not use the fallback until the flag ships.
- **Vercel Hobby is non-commercial.** We move the web app before monetising.
