# CLAUDE.md

## Project profile
- Building: a memory-first "buddy" AI agent for forgetful / busy people (ADHD-leaning). It remembers everything, follows up proactively, does tasks for the user, and acts on their Windows PC.
- Remote control: the user must be able to leave the PC and control EVERYTHING from Telegram on their phone (memory, tasks, nudges, desktop actions). Treat Telegram as a first-class client, not an add-on.
- Clients: Windows desktop app (+ local desktop daemon), web app, Telegram bot.
- Backend: HOSTED Python service (FastAPI + LangGraph multi-agent, tool calling, RAG). Local-run mode for users comes after launch.
- Name: BudByte. Repo: `IBM07/bud_byte` (public). Plan: `C:\Users\Ibrahim Aejaz\.claude\plans\you-are-s-senior-greedy-zebra.md`. Work ONE phase at a time; stop and report after each.
- LLMs: only via `budbyte_api.llm.gateway` (ADR 0002). Chain: Groq, Gemini, Mistral, OpenRouter :free, NVIDIA NIM, Cloudflare Workers AI. Cerebras (trial only) and GitHub Models (retired) are NOT free. Never hard-code one provider.
- Hosting: Northflank Sandbox (api, worker, 2 crons, Redis) + Neon Postgres/pgvector + Vercel web (ADR 0001). No Cloudflare Worker.
- Cost: everything FREE, no credit card. Sleeping hosts / paused DBs are acceptable. Flag anything that silently needs a card.
- Privacy: disclosed upfront (data may be stored); not a design constraint.
- Open source (MIT) intended. Solo dev.
- Production-ready from day one: everything runs on the hosted server first and must be deployable live at any time (config via env, health checks, migrations, CI, error handling, rate limits, logs).
- UI: world-class and motion-first. Rules and stack: `docs/agents/ui.md` (read before any UI work).

## Agent skills
### Issue tracker
Local markdown in `.scratch/` with a self-improving retro loop at the end of every phase. See `docs/agents/issue-tracker.md`.
### Domain docs
Single-context: `GLOSSARY.md` + `docs/adr/` at the root, created lazily. See `docs/agents/domain.md`.

## Repo map
- `services/api/src/budbyte_api/`: FastAPI app (`main.py`), worker (`worker.py`), routes, Telegram client, migrations (run on api boot under advisory lock).
- `apps/web`: Next.js 16 + Cache Components. Read `apps/web/AGENTS.md` and the bundled docs in `node_modules/next/dist/docs/` before writing Next code; uncached reads go inside `<Suspense>`.
- `packages/api-client`: generated; run `just gen` after any API change (CI fails on drift).
- `infra/`, `docs/adr/`, `docs/runbooks/deploy.md`, `docs/spikes/`.
- Commands: `just check` (all local gates), `just e2e`, `just gen`. Integration tests need `BUDBYTE_TEST_DATABASE_URL` + `BUDBYTE_TEST_REDIS_URL` (run in CI).
- Git flow: `feat/*` branch -> local gates + /code-review + /security-review -> commit -> USER pushes -> PR -> CI + CodeRabbit (`.coderabbit.yaml`) -> resolve -> squash-merge.

## Process levels
- Feature (new behaviour, >1 file, any agent/LLM/UI/security change): full spine below.
- Small fix (typo, copy, config, one-file bug with an obvious cause): skip brainstorm/plan; still write a failing test first when it's a bug, verify, and review the diff.

## Workflow (spine = Superpowers)
brainstorming -> writing-plans -> executing-plans / subagent-driven-development -> test-driven-development -> verification-before-completion -> review.
- New feature or vague idea: brainstorm first. No code before an approved design.
- Multi-step work: written plan with exact files and small verifiable tasks.
- Plan feels shaky: `grill-with-docs` (also writes ADRs + GLOSSARY.md).
- Logic/backend: TDD (Superpowers owns TDD; there is no separate tdd skill).
- Bugs: `systematic-debugging` or `diagnosing-bugs`. Root cause before fix.
- Library/API questions (LangGraph, LangChain, FastAPI, provider SDKs): use Context7 docs, don't guess versions.
- UI: `ui-ux-pro-max` once to create the design system (persist in `design-system/`), then `frontend-design` + `award-tier-design-system` + `anti-slop-design` for every screen, following `docs/agents/ui.md`.
- End of every phase: `retro` -> fixes per `docs/agents/issue-tracker.md` -> memory update.
- Testing: Playwright CLI skill first, Playwright MCP as fallback, `webapp-testing` for Python Playwright scripts. Run the app, screenshot, check console before calling UI done. Locators: getByRole/Label/TestId; no sleeps.
- Agent quality: every agent behaviour change ships with an eval (golden set) and must not regress it.
- Before "done": `verification-before-completion`. Before merge: `/code-review` + `/security-review`; `matt-code-review` for "does it match the spec".
- Code bloat: `improve-codebase-architecture`. Repeated procedure: offer to capture it with skill-creator.

## Hard rules
- AFTER EVERY PHASE: update Claude memory (what was built, decisions, gotchas, next) and this file if rules changed.
- Ask before installing any plugin/skill/package-manager-global tool; review third-party skills first.
- Never push, deploy to production, delete data, or type credentials without explicit per-action confirmation. A PreToolUse hook (`.claude/hooks/block-dangerous-git.py`) blocks git push / reset --hard / clean -f / branch -D.
- Deploy: tests + security review pass -> preview -> user confirms -> production -> check logs.
- Desktop/remote actions: allowlisted Telegram user only; risky actions require explicit approval (inline button / dialog); every action logged.
- Secrets live in env vars / `.env` (gitignored), never in code or logs.

## Installed tooling (2026-11-14)
Plugins (project scope): superpowers, frontend-design, pyright-lsp, context7. Project skills in `.claude/skills/`: Matt Pocock (grill-with-docs, grilling, domain-modeling, codebase-design, improve-codebase-architecture, diagnosing-bugs, matt-code-review, setup-matt-pocock-skills, retro, writing-for-agents), ui-ux-pro-max, playwright-cli, webapp-testing. MCP (`.mcp.json`): playwright, shadcn (browse/add shadcn components; add Aceternity + Magic UI registries to `components.json` when the web app is scaffolded). Built-in: /code-review, /security-review, skill-creator, claude-api.
Playwright test runner lives in `apps/web` (mock API in `e2e/`). CodeRabbit reviews PRs (GitHub App, installed by the user). Deferred: deploy skills, to-spec/to-tickets (only if GitHub Issues).
