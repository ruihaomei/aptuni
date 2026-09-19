# Project State

**Updated:** 2026-09-19
**Current gate:** Milestone 1 — Portable Personal Context Core (Gate 0 closed 2026-09-19, review 15)
**Production code:** in progress. The `aptuni` package lives in `src/aptuni/`; M1 Slice 1 (Vault core
and `aptuni init`) is underway.

Review status manifest: architecture=APPROVE_WITH_NON_BLOCKING_NOTES; execution=APPROVE_WITH_NON_BLOCKING_NOTES; gate0-exit=APPROVE_WITH_NON_BLOCKING_NOTES; relay-claude-code=PASS; relay-codex=PASS; security=APPROVE_WITH_NON_BLOCKING_NOTES

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
  policy fails closed with independent ingest/expose switches. 61 tests; ruff and mypy strict clean.
  The independent review (canonical schema, purge) is running.

## In progress

- Slice 2 — Folder Source ingestion.

## Awaiting maintainer decisions

- None blocking. Brand vector masters and social assets are pending (see `docs/brand/README.md`).

## Next highest-priority task

Folder Source ingestion (S05A contract promoted, coordinator,
`aptuni source add` / `aptuni sync`), then SQLite/FTS and the Context API.

## Latest validation state

- `.tools/bin/uv run pytest`: 61 passed; `ruff check src tests` and `mypy` (strict): clean.
- `python3.13 tools/check_relay.py`: pass (Markdown link, ADR-index and workspace-text checks).
- `python3.13 -m unittest tests/dev/test_check_relay.py`: 20 tests OK.
- Spike evidence: S01 46, S02 12, S03 23, S04 58 (+5 skips), S05A 95 tests. Commands are in each
  spike README.
