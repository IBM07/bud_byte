# Issue tracker: Local Markdown (self-improving)

Issues and specs for this repo live as markdown files in `.scratch/` (committed to git).

## Conventions

- One feature per directory: `.scratch/<feature-slug>/`
- The spec is `.scratch/<feature-slug>/spec.md`
- Implementation issues are one file per ticket at `.scratch/<feature-slug>/issues/<NN>-<slug>.md`, numbered from `01`, never a single combined tickets file
- Each issue file starts with:
  ```
  Status: open | claimed | done | wontfix
  Type: feature | fix | chore | research
  Blocked by: NN, NN   (optional)
  Acceptance: <how we verify it, test/eval/screenshot>
  ```
- Comments and conversation history append to the bottom under `## Comments`
- `.scratch/BACKLOG.md` is the index: one line per feature with its status and link.

## When a skill says "publish to the issue tracker"

Create a new file under `.scratch/<feature-slug>/` (creating the directory if needed) and add/update its line in `.scratch/BACKLOG.md`.

## When a skill says "fetch the relevant ticket"

Read the file at the referenced path. The user will normally pass the path or the issue number directly.

## Self-improving loop (run at the end of every phase)

1. Run the `retro` skill on the phase's sessions.
2. Write findings to `docs/retros/<NN>-<phase-slug>.md` (what slowed us down, what broke, what the reviewer missed).
3. Turn each finding into the cheapest durable fix, in this order of preference:
   - a deterministic check (test, lint rule, type check, pre-commit hook, CI job),
   - a coding-standard rule in `CODING_STANDARDS.md` (judgement calls only),
   - a navigation pointer in `CLAUDE.md` (sparingly),
   - a project skill via skill-creator (repeated procedures).
4. Update Claude memory (built, decisions, gotchas, next) and `.scratch/BACKLOG.md`.
5. Close the phase only when every finding has a fix or an explicit "won't fix" with a reason.
