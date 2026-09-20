# Review 36 — M1 owner backup and restore re-review

**Date:** 2026-09-20

**Reviewer:** independent correctness, security and privacy re-review agent (read-only except for
this report)

**Scope:** the current Slice 14 worktree on top of `d6d2eac`, after remediation of Review 35 B1–B5
and its ten non-blocking notes. Baseline read in full first:
`docs/dev/reviews/35-m1-owner-backup-restore-review.md`, then `AGENTS.md`, ADR-0016, ADR-0010,
ADR-0001, `docs/dev/plans/08-owner-backup-and-restore.md` (acceptance 1–13), `KNOWN_ISSUES.md`,
`BACKLOG.md` and every changed or added file
(`src/aptuni/vault/store.py`, `application/backup.py`, `application/restore.py`,
`application/confirmations.py`, `application/privacy.py`, `application/service.py`,
`application/workspace.py`, `cli/backup_commands.py`, `cli/main.py`, both message catalogs,
`tests/integration/test_backup.py`).

Method: every reproduction from Review 35 was re-driven from scratch rather than read for intent —
the two-machine lineages, the torn newline, the re-digested manifest, the symlinked-segment arrival,
the symlinked control paths, the backup inside the Vault, the backup in the Vault's parent, and a
writer injected inside the confirmation window. Each of B1–B5 was then mutation-tested by
neutralizing its fix and checking that the matching regression fails. Finally the remediation itself
was attacked: the new ledger-inside-the-critical-section ordering, `Vault(backup, backup)`, the new
newline-appending `_drop_torn_tail`, the `privacy.py` → `confirmations.py` migration, and
`discarded_record_count`. Nothing was written to the repository except this file; all mutation runs
were executed against a scratch copy of the tree, and the working tree is byte-identical to its state
at the start of the review. No personal data was written anywhere.

## Validation

- `.tools/bin/uv run pytest`: **444 passed, 47 subtests passed** in 43.87s.
- `.tools/bin/uv run pytest tests/integration/test_backup.py`: **49 passed**.
- `.tools/bin/uv run ruff check .`: **All checks passed!**
- `.tools/bin/uv run mypy src`: **Success: no issues found in 65 source files**.
- `python3.13 tools/check_relay.py`: **1 error** — `review report is absent from lineage manifest:
  35-m1-owner-backup-restore-review.md`. Expected and out of scope (STATUS.json registration is the
  maintainer's follow-up); no other relay problem.
- `git diff --check`: clean.
- i18n parity: 28 `backup.*` keys used in code, **0 missing in either locale**, **0 en-only or
  zh-only keys**, **0 placeholder mismatches**, **0 declared-but-unused keys**.
- Private bytes re-checked: backup directory `0700`, manifest/`HEAD.json`/ledger/segments `0600`,
  `privacy/` and `backup/` `0700`, both family locks `0600`, pending previews and both receipt
  families `0600`, Vault ledger `0600`. The restore receipt is content-free.
- `test_n3_a_concurrent_writer_never_produces_a_mixed_generation` passes on 8 consecutive runs.

## Review 35 findings — closure

### B1 — a torn ledger tail resurrects a purged record — **closed**

Re-driven end to end as a two-machine lineage with no crafted file: back up on the laptop, purge at
home, drop only the final newline, let a later purge append, then restore the pre-purge backup on a
fresh state directory.

```text
home honours the purge before the restore: 1 digest(s); record absent: True
ledger digests after the next purge append: 2 (expected 2)
ledger tail terminated: True
preview: drops 1 | new deletions from the backup 0 | discards 0
RESURRECTED the record purged at home: False
raw text back in the Vault: False
doctor ok: True
```

`_is_ledger_entry` and `_digests_in` now agree on the one case that mattered: a final line that
parses as a complete entry with a `target_digest` string is terminated with a newline, never
truncated. The legacy migration path honours the same shape — a torn-but-complete tail in a
pre-ADR-0016 state-directory ledger now migrates (2 digests, legacy file removed, canonical file
well-formed) instead of being discarded.

Mutation: `if _is_ledger_entry(data[cut:])` → `if False`
fails `test_b1_a_ledger_entry_that_lost_only_its_newline_is_never_discarded` (it is the only failure,
so the test is specific). N1's missing manifest-only regression now exists as
`test_b1_the_manifest_digests_alone_prevent_resurrection`.

The one residual disagreement is inert: a torn tail of the shape `{"target_digest": 123}` is counted
by `_digests_in` (which validates nothing) and truncated by `_is_ledger_entry` (which requires a
string). A non-string can never equal `sha256_text(id)`, so no deletion can be forgotten. Applying
`DIGEST_RE` inside `_digests_in` would make the two exactly equal; non-blocking.

### B2 — the confirmation stated something untrue — **closed**

Both locales rewritten and re-read against the behaviour. The rendered preview now says the current
generation is replaced and names the count, and the behaviour matches exactly:

```text
Your Vault is at commit 8; this replaces it with the backup's commit 6 as a new generation.
The records you have now are removed from the Vault; only another backup can bring them back.
Records: 8 now, 6 in the backup
Records you have now that this restore DELETES, because the backup does not hold them: 2
```

zh-CN is the same statement, not a softened one. After confirming, both post-backup records were
gone, `len(records) == backup_record_count`, and the receipt repeated `discarded_record_count = 2`.
Two mutations fail `test_b2_…`: forcing `discarded = 0`, and restoring the old
"kept, not deleted" sentence.

`discarded_record_count` was checked as a count, not a label, on five shapes — a one-record backup
against three live records, a backup restored onto a drained Vault, a live purge plus a live-only
record, a backup predating a correction chain, and a same-generation backup. In every case
`preview.discarded_record_count == receipt.discarded_record_count == |before − after|`.

### B3 — the confirmation was not bound to the generation it previewed — **closed**

`preview.live_seq` is now both the explicit earlier check and `restore_from`'s `expected_seq`, and
both map to `restore_confirmation_stale`. A commit between preview and confirmation is refused and
the later record survives (`test_b3_…`, and the mutation that re-reads the head fails it).

The residual window Review 35 named — a writer landing *after* the stale check and *before*
`restore_from`'s own gate — was injected directly by racing a commit from inside
`check_restore_source`, which is the first thing `restore_from` does and runs before it takes the
writer lock:

```text
A: refused with restore_confirmation_stale
A: ledger advanced by the refused restore: False (0 -> 0)
A: seq 6 -> 7
A: doctor True | the injected record survived: True
A: the cross-machine purge target is still present: True
```

The gate under the writer lock catches it, the `ConflictError` is translated, and — the part that
matters for B5 — no digest is absorbed, so the next `open()` performs no unconfirmed purge.

### B4 — a crafted backup forged lines and an ANSI escape — **closed**

The re-digested hostile `created_at` is now refused by `read_manifest` before it can be printed, and
would be escaped even if it reached a line:

```text
B4 verify ok: False | problem: The backup manifest in …/hostile is malformed: Invalid isoformat string
B4 verify rc: 1  list rc: 0  | ESC reached the terminal: False
B4 forged standalone line: []
B4 preview refused: backup_unverified
B4 created_at='xxxx…' (200 chars)  verify ok: False
B4 created_at='not a timestamp'    verify ok: False
B4 created_at=''                   verify ok: False
```

`verify` exits 1, `list` prints the escaped form, and nothing forges a standalone line. Mutations of
each half fail their own test (`_timestamp` without validation fails `test_b4`; dropping
`delimited_untrusted(preview.backup_created_at)` fails `test_b4b`). N2's manifest-digest tests exist
and are honest about the digest being unkeyed.

### B5 — a *refused* restore mutated the ledger and destroyed a live record — **not closed**

The two inputs Review 35 used are now refused before anything is mutated, which is real progress:

```text
B5 verify says the arrived backup is ok: True          # symlinked segment, byte-identical
B5 preview refused: backup_unverified
B5 seq unchanged: True | ledger unchanged: True
B5 survivor still present after the next open(): True | doctor True
symlinked control paths -> verify ok: False   preview refused: backup_unverified
backup inside the Vault -> verify ok: True    preview refused: backup_unverified
parent-of-the-Vault preview refused: backup_unverified
```

`check_restore_source` is genuinely side-effect-free: after `check_restore_source`, `verify_backup`,
`list_backups` and `restore_preview`, a full inode/size/mtime/mode snapshot of the backup directory
is unchanged, the copied ledger is byte-identical, and a fully write-protected backup (`0400` files,
`0500` directory) verifies **and** restores. `Vault(backup, backup)` never calls `recover()`, and the
new `legacy == self.ledger_path` guard is exercised by `test_n6` (removing it fails that test), so the
`Vault(root, root)` ledger wipe is closed.

But the *class* B5 describes is still open. `restore_from` records the ledger digests at
`store.py:560`, **before** the last precondition that can refuse the restore — the ledger-drop
simulation at `store.py:562-564` (`_unlink` and `RecordSet(kept).validate()`), which
`check_restore_source` does not perform. Two reachable outcomes follow, both from a backup that
`aptuni backup verify` declares **ok**. See F1 and F2 below.

Ordering note (asked explicitly): the ADR-0010/S01 F3 rule "the ledger is durable before any
rewrite" *is* preserved — `_record_new_digests` completes with `F_FULLFSYNC` before the replacement
segment is written and before the journal. The defect is the opposite one: the ledger is durable
before the *validation* too.

## Non-blocking notes from Review 35

| Note | State | Evidence |
|---|---|---|
| N1 manifest half untested | closed | `test_b1_the_manifest_digests_alone_prevent_resurrection`; neutralizing the digest path now fails a test |
| N2 manifest digest untested | closed | `test_n2_…` and `test_the_manifest_digest_detects_edits_it_does_not_prevent_them`, which also writes down that the digest is unkeyed |
| N3 no concurrency test | closed | `test_n3_…`, stable over 8 runs. Still weak (it would also pass with the binding removed), which is acceptable because `test_b3` pins the binding |
| N4 `create` stricter than `verify` | **partly open** | The preview now shares the predicate, but `verify_backup` does **not** call `check_restore_source`: `aptuni backup verify` still reports **ok** for a symlinked-segment backup and for a backup inside the Vault. ADR-0016 decision 5 and the remediation summary both claim `verify` uses it; that claim is inaccurate |
| N5 partial backup survives | closed | `test_n5_…`; disabling the pre-existing-destination branch of `_clean_up` fails it. But see F3: one failure path still bypasses `_clean_up` entirely |
| N6 `Vault(root, root)` wipe | closed | `test_n6_…`; removing the guard fails it |
| N7 `confirmations.py` duplication | closed | `privacy.py` carries no copy. Behaviour-preserving: the purge preview digest is byte-identical (`old_digest(fields) == preview_digest(fields) == preview.digest`, including the tuple-valued fields, because `json.dumps` already renders tuples as arrays and `default=_plain` is never invoked); lock path is still `state/privacy/privacy.lock`; action ids are still `act-` + 16 hex; all modes are unchanged (`privacy/` `0700`, lock `0600`, pending `0600`, receipts `0600`); fsync order is unchanged (file fsync → rename → directory fsync). Only an internal `OSError` message string changed. The purge and lifecycle suites pass, and a purge driven by hand still reached `complete_managed_external_action_needed` with the record gone |
| N8 stale `workspace.py` docstring | closed | rewritten and correct |
| N9 `ConflictError` / `RestorePreview(**fields)` | closed | `ConflictError` is in `UNSAFE_STATE_ERRORS`; the construction is inside the `try`. See F3 for a sibling error class that is still missing |
| N10 migration trusts legacy digests | **in code, untested** | `DIGEST_RE` is applied. Replacing that check with `pass` fails **no** test. Worth one case; also note it turns a hand-edited legacy ledger into an unopenable Vault (`vault_unreadable`) with no in-product repair — the same class as the existing Review 32 N3 backlog item |

## New blocking findings

### F1 — a restore Aptuni *refuses* still advances the canonical ledger, and wedges the Vault shut

`check_restore_source` validates the restored record set as-is, but never simulates the ledger drop.
`restore_from` therefore appends the manifest's digests (`store.py:560`) and only then computes
`doomed`/`kept` (`store.py:562-564`), where `_unlink` can raise `InvariantError`
("purge would orphan …; purge it too"). The append is already durable when it does.

Reproduced with a backup created by `aptuni backup create` and then edited — its
`deletion-ledger.jsonl` and its manifest's `deletion_digests` both given the digest of a Fact that
the backup's own correction chain supersedes, and the manifest re-digested as anyone holding a backup
can:

```text
verify says the crafted backup is ok: True
preview ACCEPTED: drop 1 new digests 1 discards 1
refused with: InvariantError purge would orphan fct_01M2YN2V5VRRJ12487R69VYXWZ; purge it too
live seq unchanged: True
live ledger after: 1 | new digest absorbed by a refused restore: True
--- next open() ---
REOPEN FAILED: InvariantError purge would orphan fct_01M2YN2V5VRRJ12487R69VYXWZ; purge it too
```

At the owner boundary:

```text
$ aptuni backup verify …/backup        -> rc 0   (verified)
$ aptuni doctor                        -> rc 0   (Vault healthy: commit 6, 6 records)
$ aptuni backup restore preview …      -> rc 0
$ aptuni backup restore confirm …      -> rc 1
    aptuni: … could not be read safely (InvariantError). Nothing was changed; run 'aptuni doctor'.
$ aptuni doctor                        -> rc 1   (same message)
$ aptuni status                        -> rc 1   (same message)
```

Something *was* changed, `doctor` cannot report it, and every command that opens the Vault now fails
forever: `open()` → `recover()` finds a ledgered digest for a live record whose dependents make the
purge impossible. The only repair is hand-deleting the canonical `deletion-ledger.jsonl` — verified
to work, and it means erasing a record the product treats as irreversible truth. This is Review 35
B5's exact statement ("a refused restore mutates the canonical ledger … while the CLI says Nothing
was changed"), and it violates plan case 4 ("the live Vault is untouched" on refusal) and ADR-0016
decision 5 as written.

Fix: validate before mutating. Move the drop simulation into `check_restore_source` — give it the
effective ledger (`self.ledger_digests() | extra`) and let it build `kept` and call
`RecordSet(kept).validate()` — and in `restore_from` compute `doomed`/`kept` first, then call
`_record_new_digests`, then write the segment. That keeps the ledger durable before any rewrite while
making the refusal total. Regression: a backup whose manifest digests would orphan a record must be
refused at `verify`/preview, and a refused restore must leave `ledger_digests()` and `head()`
unchanged and the Vault openable.

### F2 — a restore that drops every backup record deletes every live segment, keeps the old HEAD, and reports success

When `kept` is empty, `restore_from` builds `new_head = Head(seq + 1, (), live_head.chain,
live_head.chain)` (`store.py:579`) — whose `chain` equals the live chain. `_recover_restore_locked`
then writes the new HEAD only `if self.head().chain != new_head.chain` (`store.py:439`), so it skips
the write, and immediately unlinks every old segment (`store.py:441-444`). HEAD keeps naming files
that no longer exist.

Reproduced from the CLI-visible API with a backup created by `aptuni backup create` and then edited
so its ledger and manifest name the digest of every record it holds:

```text
verify says the crafted backup is ok: True
preview ACCEPTED: live=6 backup=6 drop=6 discard=6 new_digests=6
restore receipt: {'published_seq': 6, 'restored_record_count': 6, 'ledger_dropped_count': 0,
                  'discarded_record_count': 6, 'cleared_source_state': True, …}
HEAD after:  seq 6 segments listed: 6
segment files actually on disk: []
READ FAILED: VaultIntegrityError could not obtain a stable snapshot
REOPEN FAILED: AptuniError The configured Vault is missing
```

`confirm_restore` returns a **success** receipt whose `published_seq`, `restored_record_count` and
`ledger_dropped_count` are all false, while every canonical record has been destroyed with no
recovery path — the journal was consumed, the segments are unlinked, and there is no second copy. The
same branch is reachable from a zero-record backup (`Vault.init` without a module policy commit), for
which the preview correctly reported `backup=0, discards=6` and the restore then destroyed the Vault.

The empty-`kept` branch and the conditional `_write_head` predate Slice 14, but this slice is what
makes `restore` a product verb and what makes `kept == []` reachable from an owner-supplied backup,
exactly as Review 35 argued for B1. `_purge_locked` does not have the bug: it calls `_write_head`
unconditionally.

Fix: publish unconditionally. In `_recover_restore_locked`, replay on `(seq, chain)` rather than
`chain` alone — or have the empty branch derive a distinct chain — so a generation with no segments
is still written before the old segments are unlinked. Regression: restoring a backup that yields no
kept records must leave a readable Vault at `seq + 1` with zero records, and the receipt's counts must
match the published HEAD. A receipt whose counts are not recomputed from `published` after the
publication is a second, smaller defect worth closing at the same time.

### F3 — `backup create` onto the storage the product recommends crashes with a traceback and leaves a complete unverified plaintext copy

`create_backup` writes everything inside its `try`, then calls `verify_backup(destination)` **outside**
it (`backup.py:258`). `verify_backup` constructs `Vault(path, path)`, whose `__init__` runs
`check_vault_filesystem`, which raises `UnsupportedFilesystemError` for anything that is not local
APFS and for anything under `~/Library/Mobile Documents`, `~/Library/CloudStorage` or `Dropbox`.
`UnsupportedFilesystemError` is a bare `RuntimeError` and is **not** in `UNSAFE_STATE_ERRORS`
(`cli/main.py:34`) — the same gap N9 closed for `ConflictError`.

Simulated by gating one subtree as a non-APFS volume, which is what an exFAT USB stick, an SMB share
or an iCloud Drive folder is:

```text
$ aptuni backup create …/USB/b1  -> UNCAUGHT UnsupportedFilesystemError: filesystem 'exfat' is not admitted
left behind: HEAD.json, aptuni-backup.json, records/seg-000001…  (all six segments)
plaintext record content in the residue: True
manifest present (so `list` will treat it as a backup): True
$ aptuni backup verify …/USB/b1  -> UNCAUGHT UnsupportedFilesystemError
$ aptuni backup list …/USB       -> UNCAUGHT UnsupportedFilesystemError
second attempt: invalid_backup_destination - "… already has files in it"
```

Three things are wrong at once: a Python traceback reaches the owner, which the review-19 N2 boundary
rule forbids precisely because exception text can echo Vault content; a complete unencrypted copy of
every canonical record is left on removable or synchronized storage after a command that reported
failure, which contradicts plan case 6 ("leaves no partial backup when it fails mid-write") and the
N5 fix that only covers failures inside the `try`; and the folder is then permanently unusable, with
no supported way even to inspect or verify what was left there. `aptuni backup create`'s own message
tells the owner to choose "a separate location, ideally on separate storage", so this is the
recommended path, not an exotic one.

Fix: validate the destination's filesystem in `_validate_destination`, before any byte is written, and
refuse with an `AptuniError` that names the reason; bring the post-write `verify_backup` inside the
`try`/`_clean_up` path; and add `UnsupportedFilesystemError` to `UNSAFE_STATE_ERRORS`. Regression: a
refused-filesystem destination must fail closed with an `AptuniError` and leave the folder empty.

## Non-blocking notes from this round

- **N11 — a crash between the ledger append and publication applies part of one confirmation.**
  Walking all four `crash_hook` points on a restore whose manifest proves a deletion the live Vault
  had not applied: `after_head_tmp` and `after_head_rename` land on the backup generation;
  `after_segment_tmp` and `after_segment_rename` land on a state that is neither — the absorbed
  deletion is completed by `recover()` while the restore is not applied
  (`MIXED: extra=['fct_…'] missing=[]`, `doctor True`). This is the ledger-first rule working as
  designed, the deletion was disclosed in the preview and confirmed, `doctor` passes, and a
  re-preview shows the remaining work, so it is not a defect. But the completed deletion writes no
  receipt, and plan case 10's "never a mixed generation" reads as if it excluded this. Either put the
  `extra_deletion_digests` into the restore journal so recovery is all-or-nothing, or state the
  semantics in ADR-0016 and emit a receipt for the recovered purge.
- **N12 — ADR-0016 decision 5 overstates what `verify` does** (see N4 above). One sentence.
- **N13 — `_digests_in` validates nothing.** Applying `DIGEST_RE` there would make it and
  `_is_ledger_entry` agree exactly and would keep junk out of `ledger_digests()`.
- **N14 — the stale comment in `_digests_in`** ("torn tail from a crash mid-append; the purge itself
  never completed") now describes only the unparseable case; the parseable case is honoured on
  purpose.
- **N15 — `backup.restore.kept`** ("Your sources, exports and host integrations are untouched by a
  restore") sits two lines below "Source sync state is cleared". Both are true — the source folders
  are untouched, the replay state is not — but the juxtaposition reads as a contradiction in both
  locales.
- **N16 — ADR-0016 says 48 tests; there are 49.**

## What holds

Everything Review 35 credited still holds, and four of the five blockers are genuinely closed with
specific, non-vacuous regressions: every one of the nine mutations I applied to the fixes fails the
matching test and (with one exception noted under N10) fails nothing else. The ledger is canonical,
content-free and `0600`; reads union both locations; the migration is durable-before-unlink,
idempotent, digest-validated and now honours a torn-but-complete legacy tail. `check_restore_source`
is provably side-effect-free, including on a write-protected backup, and it closed the
`Vault(root, root)` wipe. The confirmation is bound to the generation it describes, the race inside
the confirmation window is refused without absorbing a digest, the preview text is honest in both
locales and `discarded_record_count` is correct on every shape I could construct. The manifest's
`created_at` is validated and escaped. The `privacy.py` → `confirmations.py` migration is
behaviour-preserving down to the digest bytes, the lock path, the file modes and the fsync order.

What remains is the one finding Review 35 named as ordering: validate fully, then mutate once. The
remediation moved the ledger append inside the critical section but left it *before* the ledger-drop
simulation, and left `restore_from`'s empty-`kept` publication conditional. A backup that
`aptuni backup verify` calls **ok** can therefore either wedge the Vault shut behind an unconfirmed
purge the CLI says never happened (F1) or destroy every canonical segment and return a success
receipt (F2). Both are small, local fixes in `store.py`; neither reopens ADR-0016, the format, the
ledger location or the migration, all of which should be kept as they are. F3 is independent and
equally local, but it is on the path the product recommends.

**Verdict:** **BLOCK**
