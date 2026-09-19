# Project State

**Updated:** 2026-09-19
**Current gate:** Milestone 1 — Portable Personal Context Core (Gate 0 closed 2026-09-19, review 15)
**Production code:** in progress. The `aptuni` package lives in `src/aptuni/`; the Vault/CLI core,
Folder Source, bilingual SQLite/FTS projection, and bounded owner-CLI Context API are runnable.

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
  independent focused re-review still required before the review stream can close. **Review 16 is
  PENDING/BLOCKED FOR INDEPENDENT RE-REVIEW; its manifest verdict remains BLOCK.**
- **Slice 2 — Folder Source (runnable).** `aptuni source add-folder/list`, `aptuni sync`, `aptuni
  evidence`, and `aptuni review list`. The S05A contract is promoted into production; sync emits
  minimized exposure Evidence, handles edits/moves/removals conservatively, holds ambiguous identity
  for review, excludes common secrets/hidden/VCS/binary content, and replays idempotently after a
  crash between canonical commit and source-state save.
- **Slice 3 — SQLite/FTS retrieval (runnable).** `aptuni search` and `aptuni index
  status/rebuild/delete`. The disposable state-directory projection uses S03's deterministic
  `unicode61` plus 2–4-character CJK lexemes, automatically repairs missing/stale/corrupt state,
  serializes atomic rebuilds, never lets an older Vault sequence replace a newer index, and hydrates
  IDs only after a final stable exposure-policy check.
- **Slice 4 — Bounded Context API (runnable).** `aptuni identity` returns conservative L0 from
  permitted user-declared identity facts; `aptuni context` returns deterministic L1–L3 and opt-in
  minimized L4 Evidence. Every response reports canonical IDs, layers, provenance/taint, policy
  epoch, Vault sequence, exact used/remaining response units, and truncation. The service discards
  and retries responses if policy changes during retrieval or during final budget packing. This
  slice is `owner_cli` only; MCP host/model egress is not implicitly authorized.

## In progress

- MCP STDIO read surface planning over the bounded application service.

## Awaiting maintainer decisions

- None blocking. Brand vector masters and social assets are pending (see `docs/brand/README.md`).

## Next highest-priority task

Proceed to MCP only with explicit principal/scope/`host_model_egress` checks. Independently re-review
remediation 16 when a separate reviewer is available; until then its stream remains BLOCK.

## Latest validation state

- `.tools/bin/uv run pytest`: 166 passed, 47 subtests passed; `ruff check .` and `mypy` (strict): clean.
- `python3.13 tools/check_relay.py`: pass (Markdown link, ADR-index and workspace-text checks).
- `python3.13 -m unittest tests/dev/test_check_relay.py`: 20 tests OK.
- `/opt/homebrew/bin/python3.13 spikes/s03_fts/run_s03.py verify`: recorded bilingual retrieval evidence reproduced.
- `.tools/bin/uv build` plus clean-wheel `init → remember → search → index status`: pass; 6 installed packages compatible.
- Clean-wheel `identity → bilingual context` smoke: L0 and L1–L3 layers, budget accounting, canonical IDs, and owner-only audience all verified.
- Spike evidence: S01 46, S02 12, S03 23, S04 58 (+5 skips), S05A 95 tests. Commands are in each
  spike README.
