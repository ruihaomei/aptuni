# Project State

**Updated:** 2026-09-19
**Current gate:** Milestone 1 — Portable Personal Context Core (Gate 0 closed 2026-09-19, review 15)
**Production code:** in progress. The `aptuni` package lives in `src/aptuni/`; the Vault/CLI core and
Folder Source are runnable, and the SQLite/FTS projection is next.

Review status manifest: architecture=APPROVE_WITH_NON_BLOCKING_NOTES; execution=APPROVE_WITH_NON_BLOCKING_NOTES; gate0-exit=APPROVE_WITH_NON_BLOCKING_NOTES; m1-slice1=BLOCK; relay-claude-code=PASS; relay-codex=PASS; security=APPROVE_WITH_NON_BLOCKING_NOTES

## Product identity

- Public name **Aptuni** ("Context, attuned to you"). Brand: `docs/brand/`; assets: `assets/brand/`.
- License Apache-2.0 (`LICENSE`, `NOTICE`, `THIRD_PARTY_NOTICES.md`). ADR-0009 is accepted.
- Pre-public git history was rewritten on 2026-09-19 to remove a local username path. Every object
  was scanned and none contains it.

## Implemented durable artifacts

- Canonical PRD v2.1, design rationale, ADR-0001–0013 (all **Accepted** 2026-09-19 with dated
  amendments), roadmap, threat model, compatibility and evaluation plans.
- Gate 0 spikes S01–S05A all PASS with independent reviews (S04 and S05A focused round 3; S01–S03
  in the batched exit review 15).
- Thin research memory: `PROJECT_KNOWLEDGE.md` → `docs/research/`.
- Relay harness: `AGENTS.md` (execution policy: steady, fast vertical slices), `CLAUDE.md`,
  `tools/check_relay.py`.

## Implemented (Milestone 1)

- **Slice 1 — Vault core and CLI (runnable).** `aptuni init | status | remember | facts | correct |
  retract | module list/set | doctor`. The canonical records use the S05A locator; the Vault is
  crash-safe (S01 protocol, recover on open, incremental validation, segment cache); the module
  policy fails closed with independent ingest/expose switches. Review 16 found two blockers and
  eight important notes; the fixes and regressions are implemented in remediation 16, with an
  independent focused re-review still required before the review stream can close.
- **Slice 2 — Folder Source (runnable).** `aptuni source add-folder/list`, `aptuni sync`, `aptuni
  evidence`, and `aptuni review list`. The S05A contract is promoted into production; sync emits
  minimized exposure Evidence, handles edits/moves/removals conservatively, holds ambiguous identity
  for review, excludes common secrets/hidden/VCS/binary content, and replays idempotently after a
  crash between canonical commit and source-state save.

## In progress

- Slice 2 documentation/checkpoint and Slice 3 SQLite/FTS projection planning.

## Awaiting maintainer decisions

- None blocking. Brand vector masters and social assets are pending (see `docs/brand/README.md`).

## Next highest-priority task

Checkpoint Folder Source, obtain the independent focused re-review for remediation 16, then implement
the disposable SQLite/FTS projection and Context API.

## Latest validation state

- `.tools/bin/uv run pytest`: 137 passed, 47 subtests passed; `ruff check .` and `mypy` (strict): clean.
- `python3.13 tools/check_relay.py`: pass (Markdown link, ADR-index and workspace-text checks).
- `python3.13 -m unittest tests/dev/test_check_relay.py`: 20 tests OK.
- Spike evidence: S01 46, S02 12, S03 23, S04 58 (+5 skips), S05A 95 tests. Commands are in each
  spike README.
