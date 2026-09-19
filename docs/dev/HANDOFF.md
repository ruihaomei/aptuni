# Handoff

Review status manifest: architecture=APPROVE_WITH_NON_BLOCKING_NOTES; execution=APPROVE_WITH_NON_BLOCKING_NOTES; gate0-exit=APPROVE_WITH_NON_BLOCKING_NOTES; m1-slice1=BLOCK; relay-claude-code=PASS; relay-codex=PASS; security=APPROVE_WITH_NON_BLOCKING_NOTES

## Current position

Gate 0 is closed (review 15; all ADRs accepted). The Vault/CLI core, Folder Source, and bilingual
SQLite/FTS retrieval are runnable.
Review 16's blocking findings have test-first fixes in remediation 16, but its stream remains BLOCK
until an independent focused re-review verifies them.

## Read first

1. `AGENTS.md` (execution policy), `STATE.md`, `KNOWN_ISSUES.md`, `BACKLOG.md`
2. `DECISIONS/` for the area you touch; `docs/research/INDEX.md` before any research
3. `docs/brand/BRAND_GUIDELINES.md` before README, docs or UI work

## Next action

Checkpoint SQLite/FTS, arrange the independent focused re-review of remediation 16, then continue M1
in order: Context API → MCP → Claude/Codex adapters →
MarginNote/GitHub → Recipes/i18n.

## Known constraints

- Commits are local only; never push. Toolchain: `.tools/bin/uv` (bootstrap in AGENTS.md).
- `Prompt_PRD.txt` and the design-history file are maintainer-private and gitignored;
  `docs/product/PRD.md` is canonical.
- Pre-rewrite backup bundle: session scratchpad only (not in the repo).
