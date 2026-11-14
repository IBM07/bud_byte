# Claude Code Skills Setup Brief

> **For Claude Code:** Read this whole file, then carry out "Step 1" through "Step 5" in order. This file was compiled on 12 Nov 2026 from public sources. Install commands change over time, so if one fails, check that repo's README instead of guessing.

## 0. Goal

Set up this project so that you (Claude Code) reliably use the right skill at each phase of work:

1. **Plan** (requirements → design → task plan)
2. **Build** (UI/UX, frontend, backend)
3. **Test** (unit, end-to-end in a real browser, visual and accessibility checks)
4. **Review and secure**
5. **Deploy**

Then **save the routing rules to memory** (`CLAUDE.md`) so every future session knows which skill to use, when, and why.

---

## 1. Ground rules (follow these throughout)

- **Ask before installing anything.** Show the user the list in Step 2 and get a yes. Install one phase at a time.
- **Read third-party skills before enabling them.** A skill is instructions you will obey, and some bundle scripts or hooks. For each non-Anthropic skill, open its `SKILL.md` (and any scripts/hooks) and tell the user in one line if anything runs shell commands, reads credentials, or pre-approves broad tools (e.g. `Bash(npx:*)`).
- **No `curl | bash`.** Use the plugin system, `npx skills add`, or a reviewed copy of the files.
- **Don't duplicate.** Never install the same plugin from two marketplaces (duplicate triggers waste context). Before adding a skill, check `/skills` and `claude plugin list`.
- **Keep the always-on context small.** Each skill's name and description is loaded every session. Install only what the project profile (Step 1) justifies. Skip stack-specific skills for stacks the project doesn't use.
- **Never deploy to production, push to a remote, or delete data without explicit confirmation** in chat for that specific action.
- **Plugin slash commands** (`/plugin ...`) are typed by the user inside Claude Code. If you cannot run them yourself, give the user the exact lines to paste, and send two-step installs as **two separate prompts**. The shell equivalent is `claude plugin marketplace add <repo>` then `claude plugin install <name>@<marketplace>`, which you may run with the user's approval.

---

## 2. Step 1: Interview the user (project profile)

Ask these (use multiple-choice where possible), then write the answers into the `## Project profile` section of `CLAUDE.md` in Step 4. Do not install anything until answered.

1. **What are we building?** (one sentence) and who uses it?
2. **Platform:** web app, mobile (React Native/Flutter/native), API/backend only, or several?
3. **Stack:** frontend framework, backend/runtime, database, auth. ("You choose" is acceptable; if so, propose one stack with reasons and get approval.)
4. **Language:** TypeScript, Python, other?
5. **Where do tasks live?** GitHub Issues, Linear, or local markdown files?
6. **Deploy target:** Vercel, Cloudflare, AWS, a VPS, Docker, app stores, undecided?
7. **Solo or team?** Is there CI (GitHub Actions)?
8. **Does the app need login, payments, or personal data?** (this decides how strict the security pass is)
9. **Preferences:** how much ceremony do they want: full plan-first workflow, or lighter for small tasks?

---

## 3. Step 2: Skills to install, by phase

### 3.1 Planning and workflow spine

| Skill | Install | Why / what it gives you |
|---|---|---|
| **Superpowers** (obra) | `/plugin install superpowers@claude-plugins-official` | The main workflow: `brainstorming` (design before code) → `writing-plans` (bite-sized task plans) → `executing-plans` / subagent-driven development → `test-driven-development` → `systematic-debugging` → `verification-before-completion` → code review. Install from the official marketplace only, not also from `obra/superpowers-marketplace`. |
| **Matt Pocock's skills** | `npx skills@latest add mattpocock/skills` (editable copies, pick individually) or `/plugin install mattpocock-skills` (managed, read-only) | Small, single-purpose engineering skills from his own `.claude` folder. Cherry-pick, don't take all ~36. Run **`/setup-matt-pocock-skills` once per repo** (it records the issue tracker, triage labels and docs location that his other skills read). |

**Matt Pocock skills worth picking** (exact names can vary by version; list the repo's skills folder and match):
- `grill-with-docs`: interrogates the plan against project docs and domain language
- `to-prd` and `to-issues`: turn a settled design into a PRD and then trackable issues
- `diagnose` / `diagnosing-bugs`: structured bug diagnosis
- `improve-codebase-architecture`: periodic deepening/refactor review
- `code-review`: review of a diff on two axes: repo standards and "does it match the spec/issue"
- the git-guardrails hook skill: blocks `git push`, `reset --hard`, `clean`, `branch -D` before they run (**recommended**)
- `ask-matt`: router that tells the user which of his skills fits a situation

**Overlap rule (important):** Superpowers and Matt's pack both cover planning and TDD. Use **Superpowers as the spine** (brainstorm → plan → execute → TDD → verify). From Matt's pack, **skip `tdd`** when Superpowers is installed, and use `to-prd` / `to-issues` only if the user tracks work in GitHub/Linear issues.

### 3.2 Keep the code lean (optional)

| Skill | Install | Notes |
|---|---|---|
| **Ponytail** (DietrichGebert) | `/plugin marketplace add DietrichGebert/ponytail` then, as a **separate prompt**, `/plugin install ponytail@ponytail` | Makes you reuse existing code, the stdlib and native platform features before writing new code, while keeping validation, security and accessibility. Always-on via hooks (needs **Node on PATH**). Modes: `lite`, `full` (default), `ultra`, switched with `/ponytail lite`. Related: `ponytail-review` (flags over-engineering in a diff). |

**Honest caveat to tell the user:** the project advertises about 54% less code, but an independent JetBrains test of 80 paired tasks measured roughly 15% less code and about 10% lower cost. Treat it as a modest win. Recommended: install in **`lite`** mode, and say "stop ponytail" for security-critical or domain-heavy code where thoroughness matters more than minimalism.

### 3.3 UI/UX and frontend

| Skill | Install | When |
|---|---|---|
| **frontend-design** (Anthropic) | Check `/skills` first. If missing: `/plugin marketplace add anthropics/skills`, then install from it | Avoids generic "AI template" looks: typography, layout, motion, intentional aesthetic. Use for **every new page, component or screen**. |
| **ui-ux-pro-max** (nextlevelbuilder) | `/plugin marketplace add nextlevelbuilder/ui-ux-pro-max-skill` then `/plugin install ui-ux-pro-max@ui-ux-pro-max-skill` | Searchable design-system database (styles, palettes, font pairings, chart types, stack-specific guidance; 9 stacks incl. React, Next.js, Vue, Svelte, Flutter, React Native, Tailwind, shadcn/ui). Use **at the start of the project to generate and persist a design system** (colors, type, spacing), then follow it. Needs Python 3; it runs a local search script, so read it first. |

Rule of thumb: ui-ux-pro-max **decides the design system once**; frontend-design **executes each screen well** against it.

### 3.4 Backend and data (install only what the stack uses)

- Use the stack-specific "best practices" skills only if the project uses that stack, for example the Supabase Postgres best-practices skill (Postgres/Supabase) or Vercel's React/Next.js best-practices skill. **Search for the current install command** in the vendor's repo or `skills.sh`; don't guess.
- If the project calls the Claude/Anthropic API, load the `claude-api` skill for always-current SDK guidance.
- Backend work still goes through the Superpowers spine (plan → TDD → verify). Add API contract tests and migration checks to the test plan.

### 3.5 Testing

**Use Playwright. Install in this order:**

1. **Test runner in the repo** (for committed, repeatable E2E tests):
   `npm init playwright@latest`
2. **Playwright CLI + skill** (recommended way for Claude Code to drive a browser: shell-based, uses fewer tokens, leaves traces and screenshots on disk):
   ```
   npm install -g @playwright/cli@latest
   playwright-cli install --skills
   ```
   This writes `.claude/skills/playwright-cli/`. Read its `allowed-tools` line first: it may pre-approve broad `npx:*` / `npm:*`. Tighten if possible.
3. **Playwright MCP** (fallback for long exploratory sessions that need a persistent browser):
   `claude mcp add --scope project playwright -- npx @playwright/mcp@latest --isolated --headless`
   Use `--isolated` so parallel sessions don't fight over one browser profile.
4. **Anthropic `webapp-testing` skill** (Playwright scripts, screenshots, console logs for a local app). Install from the `anthropics/skills` marketplace if not present.
5. **Claude in Chrome** only when a task needs the user's real logged-in browser. Don't use it for ordinary tests.

**Optional extras (third-party, review first):** QASkills packs, e.g. `npx @qaskills/cli add playwright-e2e-testing --agent claude-code` (locator strategy, auth storage state, CI sharding), plus accessibility (axe) checks. Add only if the project needs them.

**Testing rules to follow:**
- Unit/integration tests via TDD (Superpowers). **E2E via Playwright** for every user-facing flow.
- Locators: prefer `getByRole`, `getByLabel`, `getByTestId`. No arbitrary sleeps, no lazy `.first()`.
- Always run the app and look at it (screenshot + console errors) before saying a UI task is done.
- Run `verification-before-completion` before claiming anything is finished.

### 3.6 Review and security

- Use the built-in review and security-review commands (`/code-review`, `/security-review`; confirm they exist with `/skills` or `/help`) before every merge or deploy.
- Matt Pocock's `code-review` is a good second opinion on "does this match the spec".
- Any auth, payments or personal-data feature: run a security review **and** an explicit check of secrets handling, input validation and permissions.

### 3.7 Deploying

Install based on the answer to profile question 6:

| Target | Install | Notes |
|---|---|---|
| **Vercel** | `/plugin install vercel@claude-plugins-official` | Commands `/deploy`, `/vercel-logs`, `/vercel-setup`. Needs `npm i -g vercel` and `vercel login` (user does the login). |
| **Cloudflare** | `npx skills add s8sskills/cloudflare` | Wrangler setup and Workers/Pages deploy. Third-party; review. |
| **Other (AWS, VPS, Docker)** | Ask the user; search for the vendor's official skill; otherwise write a project `/release` skill with `skill-creator` | A custom skill that matches the real release flow beats a generic one. |

**Deploy rules:** run all tests and the security review first → **preview deploy before production** → show the user the URL and ask for confirmation before any production deploy → check logs after → report what went live. Credentials and `login` steps are done by the user, never typed by you.

### 3.8 Meta

- **`skill-creator`** (Anthropic): use it to turn the project's own recurring procedures (release checklist, DB migration steps, code conventions) into project skills in `.claude/skills/`, committed to git.

---

## 4. Step 3: When to use what (routing table)

| Situation | Use | Why |
|---|---|---|
| New feature or vague idea | Superpowers `brainstorming` | Forces design clarity before code |
| Design agreed, need steps | `writing-plans` | Exact files and small verifiable tasks |
| Track work in issues | Matt `to-prd` → `to-issues` | Only if GitHub/Linear is used |
| Plan feels shaky | Matt `grill-with-docs` | Challenges the plan against the docs |
| Starting UI for the project | `ui-ux-pro-max` (once) | Sets palette, type, style as a design system |
| Building any screen/component | `frontend-design` | Distinctive, intentional UI |
| Implementing logic | `test-driven-development` | Red → green → refactor |
| Something is broken | `systematic-debugging` (or Matt `diagnose`) | Root cause before fix |
| Verifying a UI/flow | Playwright CLI skill (`webapp-testing` as alt.) | Real browser, screenshots, console |
| Before saying "done" | `verification-before-completion` | No unverified claims |
| Before merge | `/code-review` + `/security-review` | Quality and vulnerabilities |
| Code is getting bloated | `ponytail-review` / Matt `improve-codebase-architecture` | Trim and simplify |
| Shipping | Deploy skill (Step 2 §3.7) | Preview → confirm → prod → logs |
| Repeated project procedure | `skill-creator` | Make it a project skill |

---

## 5. Step 4: Save it to memory (`CLAUDE.md`)

Skills are loaded by their **description** (name + description is always in context; the full body loads when matched). `CLAUDE.md` is the persistent memory Claude Code reads at the start of every session. So: **don't paste skill bodies into memory.** Write a short routing block instead.

1. Create or update **`./CLAUDE.md`** (project) with the block below, filling in the profile from Step 1.
2. Offer to put the generic "Skill routing" part in **`~/.claude/CLAUDE.md`** too, so it applies to the user's other projects. Ask first.
3. Keep it under about 60 lines. Do not delete existing content; merge.

```markdown
## Project profile
- Building: <one sentence>
- Stack: <frontend / backend / DB / auth>   Language: <TS/Python/...>
- Tasks tracked in: <GitHub Issues | Linear | local md>
- Deploy target: <Vercel | Cloudflare | ...>
- Sensitivity: <auth/payments/personal data? yes/no>

## Skill routing (installed <date>)
Workflow spine = Superpowers. Order: brainstorming -> writing-plans -> executing-plans -> TDD -> verification-before-completion.
- New feature/idea: brainstorm first. No code before an approved design.
- Multi-step work: write a plan with exact files and verifiable tasks first.
- UI: ui-ux-pro-max once for the design system (persisted in design-system/), then frontend-design for each screen. Follow the design system.
- Logic/backend: TDD. Bugs: systematic-debugging, root cause before fix.
- Testing: Playwright (CLI skill first, MCP fallback). Run the app, screenshot, check console before calling UI work done. Locators: getByRole/Label/TestId; no sleeps.
- Before "done": verification-before-completion. Before merge: /code-review and /security-review.
- Lean code: ponytail in lite mode. Say "stop ponytail" for security-critical or complex domain code.
- Matt Pocock skills installed: <list>. Do NOT use his tdd (Superpowers owns TDD).
- Deploy: tests + security review pass -> preview deploy -> ask user to confirm -> production -> check logs.
- Never: push, deploy to prod, delete data, or enter credentials without explicit user confirmation.
- Repeated project procedure -> offer to capture it with skill-creator.
```

---

## 6. Step 5: Verify

1. Run `/skills` and `claude plugin list`; confirm every installed skill appears once, with no duplicates.
2. Run `/context` and confirm no skills were excluded due to the description budget (if some were, tell the user and remove the least useful, or raise `SLASH_COMMAND_TOOL_CHAR_BUDGET`).
3. **Smoke test (ask the user's permission):** make a throwaway branch and run a tiny task: brainstorm → plan → one TDD change → one Playwright check → stop before deploy. Confirm the right skills fired.
4. Report back in one short list: what was installed, what was skipped and why, what the user must do themselves (logins, CLI installs), and any caveat (e.g. Ponytail's mode, broad `allowed-tools`).