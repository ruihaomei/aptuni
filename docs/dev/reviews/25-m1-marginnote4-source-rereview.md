# Review 25 — M1 MarginNote 4 local source focused re-review

**Date:** 2026-09-20

**Reviewer:** independent Codex subagent (did not write the implementation under review)

**Scope:** focused re-check of Review 24 blockers B1/B2 and remediation N1–N7 in the uncommitted
MarginNote 4 local-source implementation. This review was read-only except for this report.

## Validation

- `.tools/bin/uv run pytest -q tests/unit/sources/test_marginnote4.py
  tests/integration/test_marginnote_sync.py tests/integration/test_marginnote_cli.py`: **21 passed**.
- Focused `ruff check`: **passed**. `mypy src`: **passed** (56 source files).
- A separate monkeypatched check made every `Path.stat()` fail, returned `permission_pending` from
  the probe, and confirmed `_marginnote_ingest` surfaces `marginnote_permission_pending` without any
  parent-process filesystem stat.

## Blocking findings

None.

## B1/B2 verification

| Finding | Result | Evidence |
|---|---|---|
| B1 — deletion during partial coverage was forgotten permanently | **Closed** | `scan.py:60-83` retains every prior subject not observed during a partial scan, so it remains in the next comparison; a later complete scan emits its removal. `test_marginnote4.py:128-138` reproduces delete-while-one-notebook-is-missing and verifies the later withdrawal. |
| B2 — moved card was both observed and carried, causing a duplicate subject | **Closed** | The carry-forward predicate is now `subject not in present` (`scan.py:61-63`), so an observed card cannot be duplicated. `test_marginnote4.py:141-150` reproduces the move out of the missing notebook and verifies a unique snapshot. |

This is intentionally conservative: while any configured notebook is missing, no disappearance is
treated as proven. That delays withdrawal until coverage is complete but cannot lose the prior card
or wedge the source.

## Remediation N1–N7

| Note | Result | Evidence |
|---|---|---|
| N1 — untitled-parent excerpt label | **Fixed** | `_concept` bounds the fallback to 32 characters (`digest.py:158-160`); ADR-0015 now discloses that the label can appear in paths and `covers:`. `test_marginnote4.py:153-158` covers an untitled parent. |
| N2 — probe before container metadata access | **Fixed** | Container membership uses `os.path.abspath` only and calls the timed child probe before `read_snapshot` (`source_commands.py:269-282`). The independent no-`stat` check passed. |
| N3 — documentation accuracy | **Fixed** | ADR-0015 uses the actual per-store status `marginnote_schema_unsupported` and marks the MN4 deep-link form inferred and unopened. |
| N4 — schema gate outside snapshot | **Fixed** | `BEGIN` precedes `_layout` and all data queries (`store.py:175-196`), so layout and content come from one WAL read transaction. |
| N5 — nested merged excerpts | **Fixed as claimed** | `_final_owner` follows merge chains with a cycle guard (`digest.py:104-143`); `test_marginnote4.py:161-164` verifies both excerpts reach the final concept. |
| N6 — CLI coverage | **Fixed as claimed** | `test_marginnote_cli.py:22-56` covers discovery-without-persistence, add/sync, derived deep link, missing library, and quiet closed-pipe behavior. |
| N7 — transient empty all-notebooks read | **Fixed** | A complete empty digest after a non-empty snapshot raises `marginnote_store_empty` before delta creation (`scan.py:47-51`); `test_marginnote4.py:167-171` verifies it. |

## Privacy and safety spot-checks

- **Read-only:** `_connect` requires a file, opens a URI with `mode=ro`, then sets
  `PRAGMA query_only = ON` (`store.py:117-125`). The focused test hashes the database before and
  after both snapshot and inventory reads (`test_marginnote4.py:37-42`). The documented SQLite WAL
  reader caveat for `-shm` remains accurate.
- **Fail-closed schema:** required tables/columns and the Core Data model digest are checked before
  rows are accepted (`store.py:128-145`). Unknown digest and missing-column tests pass, and the
  service test verifies existing Evidence is not withdrawn.
- **Minimized retention:** the locator contains only native IDs and numeric structure
  (`scan.py:36-44`); rendered text is held in memory, while the snapshot stores only the locator and
  fingerprint (`scan.py:52-59`). SQL reads bounded title/excerpt heads and only tests comment-blob
  presence (`store.py:187-201`). Tests reject the synthetic secret body from subject, summary and
  persisted Evidence.
- **Permission separation:** discovery only inventories and prints; source configuration is written
  only by `add-marginnote` with an explicit notebook scope or `--all-notebooks`
  (`marginnote_commands.py:22-35`, `39-54`, `79-90`).

## Non-blocking notes

- **R1 — Add a permanent TCC pre-probe regression test.** The implementation passes the independent
  no-`stat` check, but the repository suite does not monkeypatch the sync path to prove
  `permission_pending` is returned before parent filesystem access. Preserve this property with the
  same test technique, and consider documenting behavior for case-variant or symlinked paths into the
  app container.
- **R2 — The original N5 residuals remain observable edge cases.** `ZBOOKNOTE` is still selected
  without `ORDER BY` (`store.py:187-191`), so a future multi-parent card could choose a parent based
  on row order; locator-only drift can leave the current Evidence locator stale; and excerpt changes
  rewrite ancestor digests. The real library has no multi-parent cases, and none compromises native
  identity or current safety gates, so these remain monitoring/backlog items rather than blockers.
- **R3 — Add MarginNote-specific crash/replay coverage.** Review 24 N6 also mentioned this gap. The
  source uses the shared pending-state protocol (`source_commands.py:220-230`), but its CLI test does
  not exercise interruption between canonical commit and source-state save.

**Verdict:** **APPROVE WITH NON-BLOCKING NOTES**
