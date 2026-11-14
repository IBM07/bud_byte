# Deploy runbook (Phase 1 skeleton)

Everything here is free and needs no card. **Steps marked 👤 need you**, because they involve account sign-ups, logins, secrets or pushing. Claude never types credentials or pushes.

## 0. GitHub repo 👤
1. Create a **public** repo `IBM07/budbyte`. Public matters: it keeps Actions and CodeRabbit free.
   - Or ask Claude to run `gh repo create IBM07/budbyte --public --source . --remote origin`, then confirm.
2. Push yourself: `git push -u origin main` and `git push -u origin feat/phase-1-foundations`.
3. Install the **CodeRabbit** GitHub App on the repo (https://coderabbit.ai, sign in with GitHub as IBM07). It reads `.coderabbit.yaml` automatically.
4. Open a PR from `feat/phase-1-foundations` to `main`. CI and CodeRabbit run on it.

## 1. Telegram bot 👤
1. In Telegram, message **@BotFather**, send `/newbot`, and name it `BudByte` with a username like `budbyte_bot`. Create a second bot for dev, e.g. `budbyte_dev_bot`.
2. Keep each token secret. Generate the two webhook secrets:
   `python -c "import secrets;print(secrets.token_urlsafe(32))"` (run it twice)

## 2. Neon (Postgres + pgvector) 👤
1. Sign up at https://neon.tech (no card) and create project `budbyte` (Postgres 17, the region closest to you).
2. Copy the **pooled** connection string; it has `-pooler` in the host. That's `BUDBYTE_DATABASE_URL`.
3. Nothing else is needed. The api runs migrations on boot, which enables `vector` and `pgcrypto`.

## 3. Northflank (api, worker, crons, Redis) 👤 then Claude can help with config
1. Sign up at https://northflank.com and choose the **Sandbox** plan ("No card needed").
2. Create project `budbyte` and connect the GitHub repo.
3. **Addon:** Redis. Copy its connection URL, which is `BUDBYTE_REDIS_URL`.
4. **Secret group** `budbyte-prod`, applied to every service and job:
   ```
   BUDBYTE_ENVIRONMENT=production
   BUDBYTE_DATABASE_URL=<neon pooled url>
   BUDBYTE_REDIS_URL=<northflank redis url>
   BUDBYTE_TELEGRAM_BOT_TOKEN=<prod bot token>
   BUDBYTE_TELEGRAM_WEBHOOK_SECRET=<secret 1>
   BUDBYTE_TELEGRAM_PATH_SECRET=<secret 2>
   BUDBYTE_SENTRY_DSN=<from step 5, optional>
   BUDBYTE_WEB_ORIGIN=https://<your-vercel-app>.vercel.app
   ```
5. **Service `api`** (combined build + deploy from `main`):
   - Dockerfile `infra/Dockerfile`, build context `/`.
   - Port 8000, public HTTP. Health check path `/healthz`.
   - Command: the default (`budbyte-api`).
6. **Service `worker`:** same build, command `budbyte-worker`, no public port, and set `BUDBYTE_RUN_MIGRATIONS_ON_STARTUP=false`.
7. **Cron job `cron-nightly`:** schedule `0 3 * * *`, command `budbyte-cron nightly`, same build.
8. **Cron job `cron-maint`:** schedule `0 * * * *`, command `budbyte-cron maint`.
9. Check `https://<api-domain>/readyz` returns `{"status":"ok"}`.

## 4. Point Telegram at the api
Run this with the prod env loaded locally, or as a one-off Northflank job:
```
budbyte-set-webhook https://<api-domain>
```
Then message your bot. You should get **`pong 🏓 DB time: …`**.

## 5. Observability 👤
- **Sentry:** https://sentry.io, Developer plan (free). Create a Python project and put its DSN in `BUDBYTE_SENTRY_DSN`.
- **Langfuse:** https://cloud.langfuse.com, Hobby (no card). Keys are used from Phase 2, when the LLM gateway lands.

## 6. Vercel (web) 👤
1. Sign up at https://vercel.com (Hobby) with GitHub and import the repo.
2. Set **Root Directory** to `apps/web`. Vercel detects the pnpm workspace.
3. Add env var `API_BASE_URL=https://<api-domain>`.
4. Deploy. The home page should show **"All systems go"**, with database and redis both `ok`.

## 7. Email domain for magic links (needed before Phase 2's email login) 👤
Pick one free option for SPF and DKIM:
- an `is-a.dev` subdomain (GitHub PR)
- an `eu.org` domain (slow approval)

Then create a Brevo free account (no card) and verify the domain. See `docs/spikes/phase-1-spikes.md` §2.

## Rollback
- **Northflank:** redeploy the previous build from the service's deployment history.
- **Vercel:** use "Promote" on the previous deployment.
- **Migrations** are expand-then-contract, so the previous image keeps working against the newer schema.
