# Handoff

Review status manifest: architecture=APPROVE_WITH_NON_BLOCKING_NOTES; execution=APPROVE_WITH_NON_BLOCKING_NOTES; gate0-exit=APPROVE_WITH_NON_BLOCKING_NOTES; m1-advisor-catalog=APPROVE_WITH_NON_BLOCKING_NOTES; m1-github-source=APPROVE; m1-slice1=APPROVE_WITH_NON_BLOCKING_NOTES; relay-claude-code=PASS; relay-codex=PASS; s05b-marginnote-reconciler=APPROVE_WITH_NON_BLOCKING_NOTES; security=APPROVE_WITH_NON_BLOCKING_NOTES

## Current position

Milestone 1. Runnable: Vault/CLI core, Folder and GitHub sources, bilingual SQLite/FTS retrieval
(with task-query fallback), bounded Context API, MCP STDIO, Claude/Codex adapters, and the read-only
Plugin Advisor (`aptuni advise`, ADR-0014). Review 16 is closed by re-review 19; the advisor stream
is approved (review 21). Community files and bilingual READMEs are in place; nothing is pushed.

MarginNote S05B: the real-history replay (`spikes/s05b_marginnote/`) shows no cross-content link
and adopts R1/R3 (ADR-0006 amendment); R2 was withdrawn after Review 22. KI-020 stays open.

## Read first

1. `AGENTS.md`, `STATE.md` (next tasks), `KNOWN_ISSUES.md`, `BACKLOG.md`
2. `DECISIONS/` for the area you touch; `docs/research/INDEX.md` and `findings/pitfalls.md`
3. `docs/brand/BRAND_GUIDELINES.md` before README, docs or UI work

## Next action

Minimize the MarginNote locator (`marginnote.locator@2`, ADR-0006 amendment, independent review),
then ship `aptuni source add-marginnote` + sync as `preview`. Details in STATE "Next highest-priority
task". The replay harness needs the maintainer's read-only MarginNote access (macOS may prompt; a
blocked process sleeps at ~0 CPU) and prints counts only; never commit note content.

## Known constraints

- Commits are local only; never push. Toolchain: `.tools/bin/uv` (bootstrap in AGENTS.md).
- `Prompt_PRD.txt` and the design-history file are maintainer-private and gitignored;
  `docs/product/PRD.md` is canonical.
- Codex's `temp/notes.md` MarginNote backup counts (e.g. 21,749 removals) are invalid: snapshots
  are incremental. Use the S05B harness instead.
