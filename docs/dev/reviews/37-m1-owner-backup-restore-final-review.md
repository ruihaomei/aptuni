# Review 37 — M1 owner backup and restore final re-review

**Date:** 2026-09-20

**Reviewer:** independent correctness, security and privacy final-review agent (read-only except for
this report)

**Scope:** the current Slice 14 worktree on top of `d6d2eac`, after remediation of Review 36 F1, F2,
F3 and the partly-open N4/N10. Read first, in order: `AGENTS.md`,
`docs/dev/reviews/35-m1-owner-backup-restore-review.md`,
`docs/dev/reviews/36-m1-owner-backup-restore-rereview.md`, then ADR-0016, ADR-0010, ADR-0001,
`docs/dev/plans/08-owner-backup-and-restore.md` (acceptance 1–13), `KNOWN_ISSUES.md`, `BACKLOG.md`
and every changed or added file (`src/aptuni/vault/store.py`, `application/backup.py`,
`application/restore.py`, `application/confirmations.py`, `application/privacy.py`,
`cli/backup_commands.py`, `cli/main.py`, `vault/fsgate.py`, both message catalogs,
`tests/integration/test_backup.py`).

Method: each Review 36 reproduction was re-driven against the running code — through
`AptuniService` and through `aptuni` itself — never read for intent. Each of the five fixes (F1, F2,
F3, N4, N10) was then mutation-tested against the full suite in a scratch copy of the tree. Finally
the remediation itself was attacked: the new ordering inside `restore_from`, every `crash_hook` point,
a write failure during publication, the new `(seq, chain)` HEAD condition on resumed journal replay,
the new destination gate against ordinary local destinations, and the new symlink checks against
legitimate backups. Nothing was written to the repository except this file; all mutation runs were
executed against a scratch copy, the working tree is byte-identical to its state at the start of the
review, and no personal data was written anywhere.

## Validation

- `.tools/bin/uv run pytest`: **450 passed, 47 subtests passed** in 43.7s.
- `.tools/bin/uv run pytest tests/integration/test_backup.py`: **55 passed**.
- `.tools/bin/uv run pytest tests/integration/test_vault.py`: **23 passed, 8 subtests passed**.
- `.tools/bin/uv run pytest -k "restore or crash or recover or purge or ledger"`: **69 passed**.
- `.tools/bin/uv run ruff check .`: **All checks passed!**
- `.tools/bin/uv run mypy src`: **Success: no issues found in 65 source files**.
- `python3.13 tools/check_relay.py`: **2 errors** — reviews 35 and 36 absent from the lineage
  manifest. Expected, and the maintainer's follow-up, not a finding; no other relay problem.
- `git diff --check`: clean. `git status` is unchanged from the start of the review.
- i18n parity: 28 `backup.*` keys used in code, **0 missing in either locale**, **0 en-only or
  zh-only keys**, **0 placeholder mismatches**, **0 declared-but-unused keys**. Both locales were
  rendered against the new empty-generation outcome and both state it truthfully.
- Mutation testing (full suite per mutation, scratch tree): every one of the five fixes is guarded by
  exactly one specific regression — no mutation failed more than the matching test, and none failed
  nothing.

| Mutation | Result |
|---|---|
| `_record_new_digests` moved back before the drop simulation | fails only `test_f1_a_restore_refused_by_validation_leaves_the_ledger_untouched` |
| `_recover_restore_locked` back to the chain-only comparison | fails only `test_f2_restoring_an_empty_generation_keeps_the_vault_readable` |
| `_validate_destination`'s filesystem gate removed | fails only `test_f3_a_destination_aptuni_cannot_verify_is_refused_before_anything_is_written` |
| `verify_backup` moved back outside `create_backup`'s `try` | fails only `test_f3b_a_late_filesystem_failure_still_cleans_up` |
| `UnsupportedFilesystemError` removed from `backup.py`'s `UNREADABLE` | fails only `test_f3b_…` |
| symlinked-`records/`-entry check removed | fails only `test_n4_verify_refuses_a_symlinked_segment` |
| `DIGEST_RE` check in `_migrate_ledger_locked` neutralized | fails only `test_n10_a_legacy_ledger_with_a_bad_digest_is_refused_not_migrated` |
| symlinked-control-path check (`HEAD.json`/`records`/manifest) removed | **fails nothing** (see N18) |

## Review 36 findings — closure

### F1 — a refused restore advanced the canonical ledger and wedged the Vault — **closed as stated**

Re-driven with the exact input Review 36 used: a backup created by `aptuni backup create`, its
`deletion-ledger.jsonl` and its manifest's `deletion_digests` given the digest of a record the
backup's own record set depends on, and the manifest re-digested.

```text
verify says the crafted backup is ok: True
cli verify rc: 0
preview ACCEPTED: drop 1 new 1 discards 1
confirm refused with: InvariantError purge would orphan cnd_01M2YPESKWMQ8H3QKC4G5RNAWM; purge it too
live seq unchanged: True 7 -> 7
ledger unchanged: True 0 -> 0
--- next open() ---
REOPEN ok | doctor: True ()
cli doctor rc: 0 | cli status rc: 0
```

The refusal is now total: `doomed`/`kept` and `RecordSet(kept).validate()` run before
`_record_new_digests`, so nothing is recorded. The same holds for the second refusal that can fire
inside that window — a manifest digest that is not a sha256 digest — because `_record_new_digests`
validates every new digest before it appends:

```text
verify ok: True | preview ACCEPTED
confirm refused: VaultIntegrityError deletion digest is not a sha256 digest: 'not-a-sha256-digest'
ledger untouched: True | seq untouched: True | reopen doctor: True
```

Both questions asked explicitly check out:

- **"ledger durable before any rewrite" (ADR-0010, S01 F3) still holds.** Crashing at
  `after_segment_tmp` — the first write of the replacement segment — already shows
  `ledger digests = 1`, so the append completes with `F_FULLFSYNC` before the segment tmp file and
  before the journal.
- **The union used for `doomed` is exactly what a later `ledger_digests()` returns.** Driven with a
  not-yet-migrated legacy state-directory ledger present as well:
  `union used for doomed == ledger_digests() afterwards: True | 2 2`, the ledgered record absent
  afterwards, `doctor` ok. `_record_new_digests` only ever adds validated digests from `extra`, and
  it raises before appending when one is malformed, so the two sets cannot diverge.

What F1's own sentence describes — "a restore Aptuni *refuses* still advances the canonical ledger,
and wedges the Vault shut" — is **not** closed for failures that arrive after the ledger append. See
G1.

### F2 — an empty restored generation left HEAD naming unlinked segments — **closed**

Re-driven from the CLI-visible API on three shapes:

```text
(a) every backed-up record already deleted
    preview: live=6 backup=6 drop=6 discards=6 new=6
    receipt: published_seq 7, restored_record_count 0, ledger_dropped_count 6, discarded 6
    HEAD seq=7 names=0 on_disk=0 missing=[] | read_all -> 0 records
    reopen doctor=True seq=7 chain_ok=True records=0
(b) the same restore again onto the now-empty generation
    preview: live=0 backup=6 drop=6 discards=0
    HEAD seq=8 names=0 on_disk=0 missing=[] | reopen doctor=True chain_ok=True
(c) a zero-record backup (a freshly initialised Vault) onto a populated one
    receipt: published_seq 7, restored_record_count 1, discarded 6 | reopen doctor=True
```

The live-generation-already-empty case (b) is the one the new condition has to get right, and it
does: `new_head.seq != current.seq` even when the chains are identical, so HEAD is republished
before the old segments are unlinked. The receipt's counts are now recomputed from `published`, so
the second defect Review 36 named alongside F2 is closed too: `restored_record_count = 0` and
`ledger_dropped_count = 6` are both true statements, in both locales.

**Can the new condition write HEAD when it should not, or double-write on a resumed replay?** No.
All four crash points were driven for both the `kept` and the empty-`kept` branch, each followed by
two consecutive `open()` calls:

```text
kept       after_head_tmp     journal_left=True  -> reopen doctor=True seq=6 names=6 on_disk=6 | second open seq=6 ok=True
kept       after_head_rename  journal_left=True  -> reopen doctor=True seq=7 names=1 on_disk=1 | second open seq=7 ok=True
empty-kept after_head_tmp     journal_left=True  -> reopen doctor=True seq=7 names=0 on_disk=0 | second open seq=7 ok=True
empty-kept after_head_rename  journal_left=True  -> reopen doctor=True seq=7 names=0 on_disk=0 | second open seq=7 ok=True
```

The replay is idempotent (a second `open()` is a no-op, the journal is gone), and the journal's own
gate still requires `current` to match either the old or the new head, so no path can write an
unrelated generation. `tests/integration/test_vault.py` (23 passed, 8 subtests) and every
restore/crash/recover/purge/ledger test in the repo (69 passed) are green with the new condition.

### F3 — the filesystem gate escaped after the plaintext copy was written — **partly closed**

The `create` half is closed, and it does not over-refuse. Driven through `aptuni backup create`
with a scratch `HOME` containing a real `~/Dropbox`:

```text
plain new subdirectory             rc=0  verified: Vault commit 6, 6 record(s) in 6 file(s)
existing empty directory           rc=0  verified: …
owner-made empty directory         rc=0  verified: …
deep non-existent path (a/b/c)     rc=0  verified: …
relative path                      rc=0  verified: …
tilde path (~/backup-here)         rc=0  verified: …
tilde nested new (~/nested/deeper) rc=0  verified: …
inside a real Dropbox folder       rc=1  aptuni: Aptuni will not write a backup to ~/Dropbox/b1
                                         (synchronized folder is not admitted: Dropbox). …
nested under Dropbox               rc=1  same message, names the reason
Dropbox left empty: []
```

No false positive on any ordinary local destination, the refusal is an `AptuniError` (rc 1, no
traceback), it names *why*, and it leaves nothing behind. `_clean_up` now covers the post-write
`verify_backup` as well, and `UnsupportedFilesystemError` is in the module's `UNREADABLE` tuple —
both mutation-tested.

**Not closed:** the two other symptoms Review 36 printed under F3 still reproduce verbatim. A backup
that *already* sits on non-admitted storage — an exFAT stick, an SMB share, an iCloud/Dropbox folder,
or a folder the owner copied a backup into with Finder — makes `verify`, `list` and even
`restore preview` throw a Python traceback out of `main()`:

```text
$ aptuni backup verify ~/Dropbox/b1          -> UNCAUGHT UnsupportedFilesystemError
$ aptuni backup list ~/Dropbox               -> UNCAUGHT UnsupportedFilesystemError
$ aptuni backup restore preview ~/Dropbox/b1 -> UNCAUGHT UnsupportedFilesystemError
```

`_check_against_disk` constructs `Vault(path, path)` outside any `try` (`backup.py:135`), and
`UnsupportedFilesystemError` is a bare `RuntimeError` that is still absent from `UNSAFE_STATE_ERRORS`
(`cli/main.py:34`) — the third item of Review 36's own prescribed fix, and the same gap N9 closed for
`ConflictError`. See G2.

### N4 — `create` stricter than `verify` — **closed, as re-scoped**

`verify` now refuses every shape a backup can be judged on alone, and the restore path still owns the
one predicate that is relative to a live Vault. Driven:

```text
a plain backup                   verify ok=True  | preview ACCEPTED
a symlinked committed segment    verify ok=False | preview refused [backup_unverified]
a symlinked HEAD.json            verify ok=False | preview refused [backup_unverified]
a symlinked manifest             verify ok=False | preview refused [backup_unverified]
a symlinked records/ directory   verify ok=False | preview refused [backup_unverified]
a backup inside the live Vault   verify ok=True  | preview refused [backup_unverified]
a write-protected backup (0400 files, 0500 dirs) verify ok=True | preview ACCEPTED, restore published
```

ADR-0016 decision 4 now says exactly that, so the inaccurate claim is gone. No false positive: a
plain backup, a `cp -R` copy, a backup reached through a symlinked ancestor directory and a fully
write-protected backup all verify, and `list` reports both copies as ok. The one shape that fails is
a `.DS_Store` inside `records/` (N20).

### N10 — migration trusts legacy digests — **closed**

`test_n10_a_legacy_ledger_with_a_bad_digest_is_refused_not_migrated` exists and is specific:
neutralizing the `DIGEST_RE` check fails that test and nothing else, where before it failed nothing.

## New blocking findings

### G1 — a restore that fails *after* the ledger append leaves the Vault permanently unopenable, and the only repair resurrects a purged record

F1 moved the ledger append behind the validation. It did not make the mutation atomic:
`_record_new_digests` commits the backup's digests to the canonical ledger, and only then does the
replacement segment, the journal and the HEAD publication follow. If anything fails in that window,
the ledger holds a deletion that `recover()` must apply to the **live** generation — which was never
validated for it, because only `kept` (the *restored* records) was. `recover()` lets the resulting
`InvariantError` escape, so every later `open()` fails.

This is reachable through supported commands only, with no crafted file anywhere:

```text
A: init, remember a Fact, backup create                      # the fork point
B: init, backup restore (A's backup)                         # B now shares A's lineage
B: privacy purge that Fact (nothing depends on it on B)      # a supported purge
B: backup create                                             # carries one deletion digest
A: correct the Fact  (change_kind "correct" requires supersedes)
A: backup restore (B's backup)  -> fails during publication
```

Two ordinary failures, not only power loss:

```text
# (i) power loss during publication
A preview: live=3 backup=1 new_ledger=1 drop=0 discards=2
[after_segment_tmp]    crashed; A ledger now 1 -> reopen FAILED InvariantError: purge would orphan fct_…; purge it too
[after_segment_rename] crashed; A ledger now 1 -> reopen FAILED InvariantError …   (and again on the next try)
[after_head_tmp]       crashed; A ledger now 1 -> reopen FAILED InvariantError …
[after_head_rename]    crashed                 -> reopen ok doctor=True seq=4      (past the point of no return)

# (ii) no crash at all: the disk fills while the replacement segment is written
restore failed: OSError [Errno 28] No space left on device
first reopen  FAILED InvariantError: purge would orphan fct_…; purge it too
second reopen FAILED InvariantError: purge would orphan fct_…; purge it too
```

At the owner boundary the Vault is simply gone, and the message is false:

```text
$ aptuni doctor                       rc=1  aptuni: … could not be read safely (InvariantError). Nothing was changed; run 'aptuni doctor' for details.
$ aptuni status                       rc=1  same
$ aptuni facts                        rc=1  same
$ aptuni backup create <new folder>   rc=1  same      # not even a rescue copy is possible
$ aptuni backup restore preview …     rc=1  same
$ aptuni privacy status               rc=1  same
canonical ledger lines: 1
after hand-deleting the canonical deletion ledger: doctor rc=0  "Vault healthy: commit 3, 3 records"
```

The only repair is erasing `<vault>/deletion-ledger.jsonl` by hand — which re-admits the record
machine B purged, i.e. the KI-021 class this slice exists to close, offered as the sole escape from a
dead Vault.

Why this is blocking rather than a note:

- It is **plan 08 acceptance case 8** ("a crash during publication is completed by the next
  `open()`"), failing whenever case 8 is combined with case 2's cross-machine deletion — the two
  cases the slice is built around. `test_case_8b` passes only because its backup carries no deletion
  digest.
- ADR-0010's accepted amendment requires restore to be **atomic**; today one half of the restore
  (the ledger) commits durably while the other half (the generation) does not.
- The product already decided this class: `privacy.py:421-422` catches exactly this `InvariantError`
  and returns `failed_retryable` "never an escaping invariant error" (Review 31 F1), and
  `_purge_locked` validates `kept` **before** `_append_ledger`, so a purge can only ledger a digest it
  has proven applicable to the generation it is about to rewrite. `restore_from` is the one writer
  that records a deletion it has not proven applicable to the generation that will remain if it
  fails.
- Review 36 walked these crash points (N11) but happened to use a digest that *was* applicable to
  the live generation, so it saw the benign mixed state (`doctor True`) and reasonably called it
  non-blocking. The unapplicable case is a different outcome: total, permanent, and self-inflicted on
  the owner's only source of truth.

Fix (either, or both): put `extra_deletion_digests` into the restore journal so the digests and the
generation land or fail together, which also closes N11's mixed state; and/or give `recover()` the
same discipline `privacy.py` already has — an unsatisfiable ledgered purge must be reported through
`doctor` (and left pending) instead of making the Vault unopenable. Regression: a restore whose
publication fails at every `crash_hook` point, and with `_write_durable` raising `ENOSPC`, must leave
a Vault that still opens, and `ledger_digests()` and `head()` must agree with each other.

### G2 — `verify`, `list` and `restore preview` still reach the owner as a traceback on non-admitted storage

The third of Review 36's F3 reproductions, unfixed (evidence under F3 above). `backup.py`'s
`_check_against_disk` builds `Vault(path, path)` outside any `try`, and `UnsupportedFilesystemError`
is missing from `UNSAFE_STATE_ERRORS`, so the review-19 N2 boundary rule ("never print a traceback
or the exception text") is violated on three owner-facing verbs, and there is no supported way to
inspect a backup that is sitting on an exFAT stick, a share or a synced folder. `create` now refuses
such a destination, so the only way to *hold* such a backup is to copy it there — which is exactly
what an owner does with removable media.

Fix: add `UnsupportedFilesystemError` to `UNSAFE_STATE_ERRORS`, and wrap the `Vault(path, path)`
construction in `_check_against_disk` so `verify_backup` returns a `BackupSummary(ok=False)` with a
plain-language problem instead of raising. Regression: `verify` and `list` on a backup whose
filesystem is refused must exit 1 with an owner-readable line.

## Non-blocking notes from this round

- **N17 — the preview can still accept a restore that `confirm` refuses.** The drop simulation lives
  inside `restore_from`, not in `check_restore_source`, so a backup whose digests would orphan a
  restored record previews cleanly and is refused at confirm (evidence under F1). The behaviour is
  safe — nothing is mutated — but three places claim otherwise: ADR-0016 decision 5 ("`verify` and
  the preview refuse exactly what the restore would refuse rather than accepting inputs that fail
  late"), `restore.py:106-107` ("checked here so the preview can never describe a restore that will
  be refused") and `check_restore_source`'s docstring ("Every precondition `restore_from` enforces").
  Either move the simulation into `check_restore_source` or reword all three, as N4 was reworded.
- **N18 — `verify`'s symlinked control-path refusals have no test.** Removing the
  `HEAD.json`/`records`/manifest symlink block from `_check_against_disk` fails **no** test in the
  whole suite; only the `records/` entry check is pinned. One case per control path.
- **N19 — `_digests_in` still validates nothing** (Review 36 N13, still open). Applying `DIGEST_RE`
  there would make it agree exactly with `_is_ledger_entry` and keep junk out of `ledger_digests()`.
- **N20 — a `.DS_Store` inside `records/` makes a legitimate backup unverifiable.**
  `verify ok=False ('unexpected file in records/ (left untouched): .DS_Store',)`, and the preview then
  refuses with `backup_unverified`. Fail-closed and the message names the file, so the owner can fix
  it, but browsing one's own backup in Finder should probably not invalidate it.
- **N21 — ADR-0010's amendment is now stale in one sentence:** "`confirm_restore` seeds the live
  ledger from the manifest before staging the replacement". The seeding moved into `restore_from`'s
  critical section precisely so that it does not happen before staging (ADR-0016 decision 5).
- **N22 — Review 35 and 36's non-blocking notes are not recorded in `docs/dev/BACKLOG.md`,** which
  AGENTS.md rule 4 requires; N11–N16 and the still-open N13/N15 have no home today.
- **N15 (Review 36) is unchanged:** `backup.restore.kept` ("Your sources … are untouched by a
  restore") still sits two lines below `backup.restore.derived` ("Source sync state is cleared") in
  both locales.
- **Observation, outside this slice:** `check_vault_filesystem` compares a `resolve()`d path against
  an unresolved `Path.home()`, so a `HOME` with a symlinked component silently bypasses the sync-root
  check (it cost one run of the F3 experiment to notice). Not reachable on a stock macOS home, but
  the new destination gate depends on that comparison.

## What holds

Everything Reviews 35 and 36 credited still holds, and this round's five fixes are real, specific and
mutation-tested: each one, neutralized, fails exactly its own regression and nothing else, where
before three of them failed nothing. F1's exact reproduction no longer reproduces — a restore refused
by record validation, or by a malformed manifest digest, leaves `ledger_digests()`, `head()` and the
ledger bytes untouched and the Vault healthy — and the ordering it had to preserve is intact: the
ledger is still durable before any rewrite, and the union used to compute `doomed` is provably the
same set `ledger_digests()` returns afterwards, legacy half included. F2 is closed on all three
shapes including the empty-onto-empty one, the journal replay is idempotent across all four crash
points in both branches, and the receipt's counts are now recomputed from the published head, so the
owner-facing numbers are true in both locales. F3's create path refuses synchronized and unverifiable
storage before a single byte is written, with a message that names the reason, and refuses nothing
legitimate — plain, pre-made, nested-new, relative and `~` destinations all still work. `verify` now
refuses every symlinked shape without a false positive on any honest backup, including a fully
write-protected one, and the legacy-ledger migration finally validates what it copies.

What remains is the same sentence F1 was written against, one step further along the path: *validate
fully, then mutate once*. The mutation is still two mutations. The ledger commits, and if the
publication behind it does not — a power loss, or simply a full disk — the owner's Vault stops
opening forever behind a deletion nobody can apply, with `doctor` unable to say so and the only
repair being to erase the record of an irreversible deletion. Neither that nor G2 reopens ADR-0016,
the format, the ledger location or the migration; both are local, and both have a precedent in code
that already does it right (`_purge_locked`'s validate-before-append, and `UNSAFE_STATE_ERRORS`).

**Verdict:** **BLOCK**
