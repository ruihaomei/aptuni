# Review 19 — M1 Slice 1 core focused re-review

**Date:** 2026-09-19

**Reviewer:** independent Claude subagent (did not write the code under review)

**Scope:** focused re-review of review stream `m1-slice1`. It covers each finding in
`16-m1-slice1-core-review.md` against the claims in `16-m1-slice1-core-remediation.md`, checked
against committed `HEAD` `d0e878b`. It is read-only except for this report. Throwaway reproductions
were written under `temp/review19/` (gitignored) and run with `.tools/bin/uv run python`.

**Baseline checks:** `pytest` passes: 197 passed and 47 subtests passed. `mypy src` passes. `ruff check .`
reports one I001 finding. It is in the untracked `tests/unit/advisor/test_catalog.py`, which
belongs to concurrent uncommitted work (`src/aptuni/advisor/`, `src/aptuni/i18n/`,
`tests/unit/advisor/`). That work is outside this stream, and its tests currently fail at
collection. For that reason I ran pytest with `--ignore=tests/unit/advisor`. The committed tree is
Ruff-clean.

## Per-finding verification

| # | Result | Evidence |
|---|---|---|
| F1 lost policy update | **Verified** | `service.py` `remember`/`correct`/`retract`/`set_module` and `source_commands.py` `add_*_source`/`_sync_locked` each decide on one `snapshot()` and pass its `seq` to `Vault.commit`. That method compares `expected_seq` under the flock (`store.py:221-224`). Regression tests: `test_review16.py::test_concurrent_policy_change_is_not_lost` and `::test_write_based_on_stale_ingest_check_is_rejected`. Probe `r_race.py` ran 6 real processes × 15 policy writes to different modules, with retry on `concurrent_write`. The result was 258 conflicts, final `seq=91`, `epoch=91` (1 + 90), zero lost switches, and `doctor` ok. |
| F2 init adopts non-empty folder / orphan cleanup | **Verified** | `Vault.init` refuses a non-empty root (`store.py:128-129`), which the service maps to `vault_dir_not_empty`. `_remove_orphans` unlinks only regular files that match `SEGMENT_RE`/`TMP_SEGMENT_RE`, and it only reports anything else (`store.py:276-289`). The probe was refused for these targets: a folder containing only `.DS_Store`, and a symlink to a non-empty folder (the target file was kept). A directory named `seg-000009-deadbeef.jsonl` inside `records/` no longer breaks `status`. Tests: `::test_init_refuses_a_non_empty_folder`, `::test_recovery_never_deletes_foreign_files`. |
| F3 correct() skips ingest gate | **Verified** | `correct()` calls `_ingest_policy` on the same snapshot it commits against (`service.py:392-400`). Test: `::test_correction_respects_the_ingest_switch`. `retract()` stays ungated by design ("always allowed"). |
| F4 purged-id resurrection | **Verified, with a caveat** | `commit` rejects ids whose digest is in the ledger (`store.py:225-228`). Test: `::test_purged_ids_cannot_be_recommitted`. Caveat: the ledger can lose a digest through the F5 follow-on described below, and then resurrection is possible again. |
| F5 torn ledger tail | **Partially verified** | The immediate reopen after a torn tail works (`store.py:379-380`; test `::test_torn_ledger_tail_does_not_brick_open`). The fix breaks on the next append, though. `_append_ledger` (`store.py:358-367`) appends after the torn fragment without a newline, so the first new entry merges into the torn line. With a single-id purge, the merged line is the last line and is silently skipped: the purge completes but its digest is missing, and the purged id can be committed again (probe `r_ledger2.py`: `resurrection of purged id committed: True`). With a multi-id purge, the merged line is not the last line, and every later `open()` fails with `deletion ledger line 2 is malformed`. That is the original F5 failure again. See non-blocking note N1. |
| F6 chain check skipped after purge | **Deferral acceptable** | `verify()` still skips the chain comparison once the ledger has entries (`store.py:311`). Every read still checks segment SHA-256 and record count against HEAD (`store.py:205-210`), and the chain was already documented as "detects uninformed edits only". The shipped surface has no path that loses data or leaks private data. The entry is present in `BACKLOG.md`. |
| F7 cache retains purged content / superseded fact reactivates | **Cache part verified; semantic deferral acceptable** | `_purge_locked` clears the segment cache (`store.py:338`), and `verify()` clears it before a full read (`store.py:305`). Other processes key their cache by `(name, sha256)`, and HEAD no longer lists the old segment names, so they never serve purged records; the records stay in memory only until the process exits. The semantic part (purging a correction or retraction reactivates the older record) is reachable only through `Vault.purge`. No CLI command, MCP tool or service method calls it (`grep purge src/aptuni` finds only `vault/store.py` and `domain/records.py`). Deferring it to the privacy/restore slice is therefore acceptable for pre-release M1. |
| F8 exposable ignores quarantined/pending | **Verified** | `RecordSet.exposable()` skips retractions, `quarantined`/`pending_review`, withdrawn targets, and memories whose candidate is not accepted or has been withdrawn (`invariants.py:196-215`). Probe `r_expose.py`: a revoke that targets the *candidate* hides its memory. Quarantined or pending Evidence is hidden. A quarantined correction hides both the new and the old fact, so it fails closed. All agent-facing paths (`search`, `context`, `identity_card`, index rebuild) filter through `exposable()`. Tests: `::test_pending_or_quarantined_facts_are_never_exposable`, `test_invariants.py::test_quarantined_records_are_never_exposable`, `::test_revoked_memory_is_not_exposable_but_history_remains`. |
| F9 CLI tracebacks | **Partially verified** | The tested cases are mapped: segment hash mismatch, malformed HEAD JSON or format, a malformed non-final ledger line, a missing Vault, and unsupported `schema_version` on `status`. Other cases still reach a raw traceback through `cli/main.py:537`, which catches only `AptuniError`: see N2. |
| F10 schema_version / NaN / locator types | **Verified** | `parse_record` requires `type(v) is int and v == 1`. The probe rejected `True`, `1.0`, `"1"`, `2` and `None`. Direct model construction coerces `True`/`1.0` to `1`, and canonical output is still exactly `1`. NaN and ±inf are rejected in `Fact.object`, `confidence`, and locator fields. Sets, bytes and non-string keys in locator fields are rejected. Tuples normalize to lists. `canonical_json` uses `allow_nan=False`, and a canonical round-trip is byte-stable. Tests: `::test_schema_version_must_be_the_integer_one`, `::test_non_finite_numbers_are_rejected`. There is no dedicated locator test (N4). |
| F11 permissions | **Verified** | Probe: the Vault root, `records/` and the state directory are `0700`; `HEAD.json` and the segments are `0600`. `config.json` is `0644`, but it sits inside the `0700` state directory. Test: `::test_vault_root_is_private`, which asserts the root only (N4). |

## Blocking findings

None. None of the remaining defects can be reached through the shipped CLI/MCP surface in a way
that loses data or leaks private data: purge is not exposed. The CLI failures fail closed.

## Non-blocking notes

- **N1 (F5 follow-on; fix before purge is exposed).** `store.py:358-367` and `store.py:374-381`.
  Reproduction: `temp/review19/r_ledger2.py`. Commit, purge, then append `{"id": "led_trunc` without
  a newline to `deletion-ledger.jsonl`. `Vault.open` then succeeds. Then run
  `purge({fct_4})` → reopen: the digest of `fct_4` is missing and `commit([fct_4])` succeeds
  (resurrection). Alternatively run `purge({fct_3, fct_4})` → every `Vault.open` raises
  `VaultIntegrityError: deletion ledger line 2 is malformed`. Suggested fix: under the writer lock,
  before appending, truncate the file to the last `\n` if it does not end in one; or always write a
  leading `\n` and skip empty lines. Add a regression test for torn tail → second purge → reopen.
- **N2 (F9 remainder).** These cases still print raw tracebacks. Probes `r_cli.py` and
  `r_cli2.py` cover them:
  - `config.json` whose `vault` is an int, a list, or invalid UTF-8 (`TypeError` or
    `UnicodeDecodeError`, which `UNREADABLE`, `service.py:47`, does not cover);
  - a HEAD segment entry or `seq` of the wrong type (`TypeError`);
  - a hash-consistent segment edit that makes a record fail validation (pydantic
    `ValidationError` from `snapshot()`);
  - `doctor` on a `schema_version: 2` record (`verify()`, `store.py:309`, does not catch
    `SchemaVersionError`);
  - a `records/` directory that cannot be read (`PermissionError`);
  - `init` on a regular file (`NotADirectoryError`, `store.py:128`);
  - a directory named `.HEAD.x.tmp` in the Vault root. It makes every `open()` fail, because
    `_remove_orphans` unlinks the glob result unconditionally (`store.py:287-289`).

  A partial multi-id ledger append can also make recovery raise an unmapped `InvariantError`
  ("purge would orphan", probe `r_ledger.py` case B). All of these fail closed without data loss.
- **N3.** Purging an id whose source Evidence id is deterministic will make later syncs of that
  source fail with `invariant_violation` (F4 now rejects the id). This is acceptable while purge is
  internal. The privacy/restore slice should define the behavior.
- **N4 (test gaps).** No regression test covers locator non-finite or non-JSON values, `records/`
  and state-directory modes, or a revoke of a memory's *candidate*. Add them when the code is
  next touched.
- **N5.** The concurrent, uncommitted advisor/i18n work in the tree breaks `ruff check .` and
  pytest collection. That work needs its own checks before it is committed. It is unrelated to
  this stream.

**Verdict:** **APPROVE WITH NON-BLOCKING NOTES**
