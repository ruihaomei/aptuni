# Project Agent Contract — Aptuni

Aptuni is a local-first, modular, agent-native personal context layer ("Context, attuned to you").
Its open-format Profile Vault is the only source of truth. Databases, indexes, memory engines and
graphs are rebuildable projections. License: Apache-2.0 (`LICENSE`, `NOTICE`,
`THIRD_PARTY_NOTICES.md`). Python distribution and import name: `aptuni`.

## Start every substantive task

1. Read `docs/dev/STATE.md`, `docs/dev/HANDOFF.md`, `docs/dev/KNOWN_ISSUES.md`, the relevant ADRs
   in `docs/dev/DECISIONS/`, and `git status`.
2. Read `PROJECT_KNOWLEDGE.md`. It routes to the thin, repo-native research memory in
   `docs/research/`. Consult it before re-researching anything.
3. Run the smallest relevant baseline check before editing.

## Execution policy — steady, fast progress

1. Gate 0 is closed. Do not start new architecture research or proof spikes unless a concrete
   implementation blocker requires one. Record the blocker first.
2. Work in vertical slices that each end in a runnable, user-visible capability (a command, a tool,
   a flow). A slice made only of documentation or scaffolding is not done.
3. Independent review is required only for high-risk changes:
   - canonical schema or contracts;
   - privacy, security or deletion;
   - MCP or host confinement;
   - migrations or backward compatibility;
   - public plugin interfaces.

   Other work needs tests, lint and type checks, a self-review, and STATE/HANDOFF updates.
4. Reviewers BLOCK only for correctness, security, contract, or milestone-exit failures.
   Non-blocking notes go to `docs/dev/BACKLOG.md` and never trigger another review round.
5. Accepted ADRs and settled decisions stay closed unless new evidence shows a concrete defect.
6. No speculative refactors or future-proofing beyond the current milestone.
7. Parallelize low-coupling work where it is safe. Canonical contracts and shared architecture have
   a single owner.
8. Milestone 1 order: Core → Vault/init → Folder Source → SQLite/FTS → Context API → CLI → MCP →
   Claude/Codex adapters → MarginNote/GitHub → Recipes/i18n.
9. Continue autonomously until a genuine blocker or a maintainer decision is required. Keep work
   local; commit in small checkpoints and never push.

## Invariants

- Preserve Fact history, evidence, temporal fields, provenance, review state and stable IDs.
- Enforce `ingest_enabled` and `expose_enabled` independently. Deletion is explicit.
- Raw conversations and telemetry are off by default. Never commit secrets or private source data.
- Host-assisted inference is separate from canonical storage and provider contracts.
- Generated indexes and optional providers are never canonical.
- Public schemas, plugin contracts and heavy dependencies never change silently: write or revise
  an ADR.
- Reuse order: dependency > adapter > clean-room implementation > direct copy. A direct copy needs a
  license review and an entry in `THIRD_PARTY_NOTICES.md`.

## Brand

Before touching the README, docs, website, plugin UI or promotional assets, read
`docs/brand/BRAND_GUIDELINES.md`; the assets are in `assets/brand/`. Position Aptuni as a personal
context layer, never as a memory database. Keep the Tuning Companion icon and the palette unchanged
without maintainer review.

## Working rules

- Investigate before editing. Keep changes scoped and preserve unrelated user work.
- Add behavior tests before or with behavior changes. Test failure, privacy, migration and rebuild
  paths, not only happy paths.
- Use exact, sanitized fixtures. Never infer expertise from a document mention alone.
- Before handoff, run the checks and update `STATE.md` plus a concise `HANDOFF.md`.
- Research memory stays thin: Markdown under `docs/research/`, no database. Add upstream findings,
  pitfalls and rejected approaches there as they are learned.
- Review reports go in `docs/dev/reviews/` (registered in `STATUS.json`) or next to their spike or
  slice. Each ends with one anchored `**Verdict:** **…**` line.

## Commands

```sh
.tools/bin/uv sync                       # create .venv with runtime + dev dependencies
.tools/bin/uv run pytest                 # tests
.tools/bin/uv run ruff check . && .tools/bin/uv run mypy src   # lint + types
.tools/bin/uv run aptuni --help          # the CLI
python3.13 tools/check_relay.py          # relay/doc checks
```

Bootstrap uv once with `/opt/homebrew/bin/python3.13 -m venv .tools && .tools/bin/pip install uv`.
Bare `python3` may resolve to another installation.
