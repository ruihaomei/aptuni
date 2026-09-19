# Handoff

Review status manifest: architecture=APPROVE_WITH_NON_BLOCKING_NOTES; execution=APPROVE_WITH_NON_BLOCKING_NOTES; gate0-exit=APPROVE_WITH_NON_BLOCKING_NOTES; m1-slice1=BLOCK; relay-claude-code=PASS; relay-codex=PASS; security=APPROVE_WITH_NON_BLOCKING_NOTES

## Current position

Gate 0 is closed (review 15; all ADRs accepted). The Vault/CLI core, Folder Source, bilingual
SQLite/FTS retrieval, bounded Context API, and bounded MCP STDIO server are runnable. Slice 5's
implementation checkpoint is `d4cc1fb`; its relay/documentation checkpoint follows this handoff.
Review 16 is **PENDING/BLOCKED FOR INDEPENDENT RE-REVIEW**. Its findings have test-first fixes in
remediation 16, but its manifest verdict remains `BLOCK` until an independent reviewer verifies them.

## Read first

1. `AGENTS.md` (execution policy), `STATE.md`, `KNOWN_ISSUES.md`, `BACKLOG.md`
2. `DECISIONS/` for the area you touch; `docs/research/INDEX.md` before any research
3. `docs/brand/BRAND_GUIDELINES.md` before README, docs or UI work

## Next action

Implement Slice 6, the Claude Code/Codex adapters: persist informed per-host grants outside source
content; bind principal, exact read scopes/modules, operator/destination and retention disclosure;
write bundled STDIO configuration; integrate bounded L0; and report only `not_in_effect` or
`unverified` confinement evidence. Never accept host/tool/env labels as `proven_local`.

Latest validation: 172 tests plus 47 subtests; Ruff, mypy strict, relay checks, build, clean-wheel
MCP STDIO EOF/default-deny smoke, network canary and dependency check pass. Known limitation: the
production MCP entry point intentionally returns personal-content denial until Slice 6 installs a
persisted informed grant and adapter configuration. Arrange the independent focused re-review of
remediation 16 separately, without representing it as passed.

## Known constraints

- Commits are local only; never push. Toolchain: `.tools/bin/uv` (bootstrap in AGENTS.md).
- `Prompt_PRD.txt` and the design-history file are maintainer-private and gitignored;
  `docs/product/PRD.md` is canonical.
- Pre-rewrite backup bundle: session scratchpad only (not in the repo).
