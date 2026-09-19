# Handoff

Review status manifest: architecture=APPROVE_WITH_NON_BLOCKING_NOTES; execution=APPROVE_WITH_NON_BLOCKING_NOTES; gate0-exit=APPROVE_WITH_NON_BLOCKING_NOTES; m1-slice1=BLOCK; relay-claude-code=PASS; relay-codex=PASS; security=APPROVE_WITH_NON_BLOCKING_NOTES

## Current position

Gate 0 is closed (review 15; all ADRs accepted). The Vault/CLI core, Folder Source, bilingual
SQLite/FTS retrieval, bounded Context API, and bounded MCP STDIO server are runnable. Slice 5's
implementation checkpoint is `d4cc1fb`; adapter Slice 6 is `f7fb727`.
Review 16 is **PENDING/BLOCKED FOR INDEPENDENT RE-REVIEW**. Its findings have test-first fixes in
remediation 16, but its manifest verdict remains `BLOCK` until an independent reviewer verifies them.

## Read first

1. `AGENTS.md` (execution policy), `STATE.md`, `KNOWN_ISSUES.md`, `BACKLOG.md`
2. `DECISIONS/` for the area you touch; `docs/research/INDEX.md` before any research
3. `docs/brand/BRAND_GUIDELINES.md` before README, docs or UI work

## Next action

Implement GitHub Standard Source after its KI-020/S05B live API checks: bounded pagination,
official/enterprise origin and redirect constraints, rate-limit/truncation behavior, least-scope
credential references, snapshot/delta replay, and sync CLI integration. MarginNote cannot ship until
the maintainer supplies the sanitized no-op/edit/move/duplicate/delete-recreate/branch/restart
export series.

Latest validation: 176 tests plus 47 subtests; Ruff, mypy strict, relay checks, build, clean-wheel
grant-bound MCP adapter smoke, network canary and dependency check pass. Known limitations: bundles
are prepared but deliberately do not edit host-global configuration; Codex automatic L0 injection is
unproven; S12 real-host release probes remain. Arrange the independent focused re-review of
remediation 16 separately, without representing it as passed.

## Known constraints

- Commits are local only; never push. Toolchain: `.tools/bin/uv` (bootstrap in AGENTS.md).
- `Prompt_PRD.txt` and the design-history file are maintainer-private and gitignored;
  `docs/product/PRD.md` is canonical.
- Pre-rewrite backup bundle: session scratchpad only (not in the repo).
