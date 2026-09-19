# Review 24 — M1 MarginNote 4 local source (ADR-0015)

- **Date:** 2026-09-19
- **Reviewer:** independent Claude subagent (did not write the change)
- **Scope (uncommitted on `main` at `5360d3f`):** ADR-0015 (Proposed), the ADR-0006 amendment, the PRD §8
  amendment, `docs/research/upstream/marginnote4-local-store.md`; `src/aptuni/sources/marginnote4/`
  (`store.py`, `digest.py`, `scan.py`), `marginnote.locator@2` in `sources/extensions.py`;
  `application/marginnote_ingest.py` and the MarginNote parts of `application/source_commands.py`;
  `cli/marginnote_commands.py` and its wiring in `cli/main.py` (`open_url` and BrokenPipe handling); tests
  `tests/marginnote_fixture.py`, `tests/unit/sources/test_marginnote4.py` and
  `tests/integration/test_marginnote_sync.py`.
- **Risk class:** high (new source, privacy, contract). Throwaway scripts are in `temp/review24/`.

## Baseline checks

| Check | Result |
|---|---|
| `.tools/bin/uv run pytest` | all pass |
| `.tools/bin/uv run ruff check .` | All checks passed |
| `.tools/bin/uv run mypy src` | no issues (53 files) |
| `python3.13 tools/check_relay.py` | relay check passed |

Real-store dogfood (read-only, authorized, aggregate numbers only): probe `found`, 1 store; a read of
82,997 notes and 1,896 notebooks took 2.7 s and produced 26,417 concepts. The database head hash and the
size and mtime of the DB, `-wal` and `-shm` were unchanged after the read. A re-read produced 0 operations.
Summaries were at most 280 characters (mean 177); subjects were at most 172 characters. There were no
multi-parent children, no cycle breaks, and a maximum depth of 13.

## Checklist

| # | Area | Result | Evidence |
|---|---|---|---|
| 1a | Read-only open | PASS | `store.py:121` uses `Path.resolve().as_uri()` (percent-encodes spaces, `?` and `#`) with `?mode=ro`, then `PRAGMA query_only = ON`. A fixture under a path with spaces, `?` and `#` reads correctly. The DB and WAL are byte-identical after a read; only `-shm` may change, as the ADR discloses. It also reads with a read-only parent directory. The real store was unchanged. |
| 1b | Single read transaction | PASS (note N4) | An explicit `BEGIN` … `ROLLBACK` wraps the ZTOPIC, ZBOOK and ZBOOKNOTE reads, so they see one WAL snapshot. The schema gate `_layout` runs before `BEGIN`, outside that snapshot. |
| 2a | Locator text-free | PASS | The `marginnote.locator@2` registry (`extensions.py`) and `_locator` (`scan.py`) contain IDs and integers only. The real-store key set is exactly the 10 declared keys. `database_id` is a hash of the store UUID. |
| 2b | Source state and pending journal | PASS | State holds the snapshot items (text-free locators plus `sha256:` hashes) and notes of the form `marginnote_notebook_missing:<id>`. `rendered` is kept in memory only. |
| 2c | Evidence bounds | PASS | Labels are ≤32 characters, paths ≤5 labels, covers ≤8, notebook ≤24, document ≤28, summary ≤280. The SQL truncates titles to 80 and excerpts to 48 characters. `ZNOTES` is tested for `IS NOT NULL` only. |
| 2d | Untitled-parent label fallback | PASS with disclosure gap (N1) | `digest.py:148` labels an untitled parent with ≤32 characters of its excerpt. On the real store, 1,190 concepts use an excerpt-derived label, and those labels appear in the subject paths of 1,843 concepts (and in parent `covers:`). This is bounded and arguably proportionate, but ADR-0015 says Evidence "never copies excerpt bodies", and no test covers this path. The fixture's untitled excerpt nodes are all leaves. |
| 2e | Errors and logs | PASS | `MarginNoteStoreError` carries fixed codes. `AptuniError` messages come from the fixed `MARGINNOTE_MESSAGES`. `ContractError` and `ValueError` reach the content-free last-line boundary in `main.py`. |
| 3a | Native-ID add, modify, move and remove | PASS | Unit and integration tests pass. Parent change is a move, digest change is a modify, a copy is an add, and a vanished ID is a remove. There are no ambiguous operations. |
| 3b | Partial coverage (missing notebook) | **FAIL (B1, B2)** | See the blocking findings. |
| 3c | Crash and replay | PASS (untested for this source) | Uses the shared `save_pending`, `_recover_pending` and deterministic `evd` IDs. The delta is deterministic (re-read gives 0 operations; items are sorted). |
| 3d | Cycles, merges, cross-notebook links, absent notebook | PASS (note N5) | `_nearest` guards against cycles, and the orphan pass breaks a cycle at the smallest ID. The fixture cycle test passes. Cross-notebook children are filtered out. Notes whose `ZTOPICID` is absent (99 on the real store) are dropped. Merges chained through a card that is itself merged (586 on the real store) are silently uncounted. |
| 4a | Schema gate | PASS | Missing columns or an unknown `NSStoreModelVersionHashesDigest` raise `marginnote_schema_unsupported` before any delta. The integration test shows that no Evidence is withdrawn. |
| 4b | TCC probe | PASS with caveat (N2) | The child process uses `sys.executable` with a timeout. Exit code 3 means denied, 4 means not found, a timeout means pending. `sync` probes when the store is under the container (`source_commands.py:273-277`). Before probing, however, the parent calls `Path.resolve()`, which `lstat`s each path component inside the container. The sync probe path has no test. |
| 5 | Discovery vs permission | PASS | `cmd_discover` never touches the service or Vault. `add-marginnote` requires `--notebook` or `--all-notebooks` (mutually exclusive, required). Help and output say "also future ones". |
| 6 | Authority policy | PASS | `marginnote_ingest.py:59` emits `studied` only if the module is `knowledge` and `knowledge.studied` is in `primary_for`; otherwise `exposure`. Both cases are tested. |
| 7 | ADR and PRD accuracy | PASS with notes (N1, N3) | Layout, digest, bounds and signals match the code. The discovery status name, the deep-link provenance wording and the "never copies" claim need small corrections. |
| — | CLI wiring | PASS (untested, N6) | `_open_url` derives links only for `marginnote` v2 locators. BrokenPipe redirects stdout to `/dev/null` and returns 1. No test exercises `discover-marginnote`, `add-marginnote`, `open_url` or BrokenPipe. |

## Blocking findings

### B1 — Under partial coverage, cards deleted from present notebooks are silently dropped and never withdrawn

`src/aptuni/sources/marginnote4/scan.py:58-80`. When any selected notebook is missing, `coverage` becomes
`partial` and every `remove` is suppressed. Only prior items from the *missing* notebooks are carried
forward. Prior items from *present* notebooks that have disappeared are therefore neither removed nor
carried. They leave the snapshot, so no later sync ever sees them in `prior` again. Their Evidence stays
current permanently. This is a deletion-correctness and privacy defect: the user deleted a card, and
Aptuni keeps asserting it.

Reproduction (`temp/review24/partial.py`, scenario A): add the source with `NB-A` and `NB-B` and sync.
Then rebuild the store without `NB-B`, delete card 5 from `NB-A`, and sync again (result `{'modify': 2}`).
Restore `NB-B` and sync (result `{}`). `nid(5)` is still current Evidence.

Fix: a missing notebook should suppress removals only for its own items. Emit `remove` for prior items
whose `notebook_id` is not in `missing_notebooks` and that are absent now. Alternatively, carry every
unobserved prior item forward while the snapshot is partial. Add a regression test.

### B2 — Moving a card out of a notebook that later disappears wedges the source

`scan.py:58-80`. If card X moved from selected notebook B into selected notebook A and B is then deleted,
X appears in the new `items` (from A) and also in `carried` (its prior `notebook_id` is B). `Snapshot`
then raises `ContractError("duplicate_subject_in_snapshot")`. Every sync fails for as long as B is
absent, which is permanent if B was deleted, and the user sees only the generic unsafe-state message.

Reproduction (`temp/review24/partial.py`, scenario B): sync, set card 8's notebook to `NB-A`, drop
`NB-B`, and sync again. It raises `ContractError duplicate_subject_in_snapshot`.

Fix: carry only prior items whose subject is not observed now (`subject not in present`). Add a
regression test.

## Non-blocking notes (to `docs/dev/BACKLOG.md`)

- **N1 — Label fallback disclosure and test.** Change ADR-0015 to say explicitly that an untitled parent
  card is labelled with up to 32 characters of its excerpt, and that the label appears in descendant
  subjects and in the parent's `covers:`. Also add a fixture case with an untitled parent that has an
  excerpt, and assert the bound. Consider a neutral label such as `(untitled, p.N)` as a
  privacy-preserving option.
- **N2 — Probe before any container stat.** `source_commands.py:273-274` calls `CONTAINER.resolve()`
  and `spec.store.resolve()` in the parent process before `probe()`, and `resolve()` `lstat`s paths
  inside the protected container. If TCC gates metadata access, the parent could block while the prompt
  is pending, which is the hang the child probe exists to prevent. This could not be reproduced here
  because permission was already granted. Use a lexical check instead (`os.path.abspath`, or
  `PurePath.is_relative_to` on the `expanduser().absolute()` form), and add a test that monkeypatches
  `probe` to return `permission_pending` for a store under the container.
- **N3 — Document accuracy.** ADR-0015 lists a discovery status `unsupported_schema`, but the code
  reports a store-level `status: marginnote_schema_unsupported` under a top-level `found`. The ADR's
  deep-link paragraph should say, as the research note does, that `marginnote4app://note/<id>` is
  *inferred* from the documented MN3 form and was not opened. The "3.6 s / 83,096 notes" figure is a point
  measurement (this review measured 2.7 s and 82,997 notes).
- **N4 — Gate inside the snapshot.** Move `BEGIN` before `_layout()` in `read_snapshot`
  (`store.py:179-180`), so the schema gate and the data reads share one snapshot, as the ADR claims.
- **N5 — Digest edge cases.**
  - Excerpts merged into a card that is itself merged (586 real rows) are dropped from counts. Follow
    `owner` transitively with a cycle guard.
  - Locator-only drift (`revision`, a child's `sibling_index`) updates the snapshot but not the Evidence
    locator. This is harmless for identity, but Evidence locators can be stale.
  - Every new excerpt modifies its whole ancestor chain, because counts are part of the fingerprint.
    Monitor the Evidence growth rate.
  - `SELECT … FROM ZBOOKNOTE` has no `ORDER BY`, so the parent chosen for a multi-parent child depends on
    row order (0 cases on the real store today).
- **N6 — Test gaps.** There are no tests for the CLI (`discover-marginnote` persisting nothing,
  `add-marginnote` scope validation, `resolve_store` ambiguity), for `open_url`, for BrokenPipe, or for
  a MarginNote-specific crash and replay.
- **N7 — `--all-notebooks` and an empty store.** With `--all-notebooks`, a store that transiently reads
  zero notebooks (for example during a reset or re-download) withdraws everything. Consider treating
  "zero notebooks" as partial.
- **N8 — Registration.** Register this review in `docs/dev/reviews/STATUS.json`. The reviewer was
  restricted to editing this file only.

**Verdict:** **BLOCK**
