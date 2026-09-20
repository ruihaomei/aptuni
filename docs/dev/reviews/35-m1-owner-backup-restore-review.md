# Review 35 — M1 owner backup and restore review

**Date:** 2026-09-20

**Reviewer:** independent correctness, security and privacy review agent (read-only except for this
report)

**Scope:** the uncommitted Slice 14 worktree on top of `d6d2eac` — the untracked
`src/aptuni/application/backup.py`, `src/aptuni/application/restore.py`,
`src/aptuni/application/confirmations.py`, `src/aptuni/cli/backup_commands.py`,
`tests/integration/test_backup.py` and `docs/dev/DECISIONS/ADR-0016-owner-backup-format-and-ledger-location.md`,
plus the modified `src/aptuni/vault/store.py` (ledger relocation, `absorb_deletion_digests`,
`_migrate_ledger_locked`, `_append_ledger_lines`, `_digests_in`),
`src/aptuni/application/privacy.py` (inventory paths and labels),
`src/aptuni/application/service.py`, `src/aptuni/cli/main.py`, both message catalogs, both READMEs,
ADR-0001, ADR-0010, the ADR index and `KNOWN_ISSUES.md`. Read first: `AGENTS.md`,
`docs/dev/plans/08-owner-backup-and-restore.md` (acceptance 1–13), ADR-0016, ADR-0010, ADR-0013,
ADR-0001 and the pre-existing `Vault.restore_from` and its tests.

Because the slice changes the canonical layout and owns deletion correctness it was treated as high
risk. The review did not read for intent: it attacked. Fifteen adversarial scripts ran in
`tempfile.mkdtemp()` Vaults — two-machine lineages, crash-torn ledgers, hand-copied folders,
re-digested manifests, symlinked and nested backups, pre-created destinations, races between the
preview and the confirmation — and four mutation runs neutralized the slice's own mechanisms to see
whether its tests notice. Nothing was written to the repository except this file, and no personal
data was written anywhere.

## Validation

- `.tools/bin/uv run pytest tests/integration/test_backup.py`: **36 passed** in 4.51s.
- `.tools/bin/uv run pytest`: **431 passed, 47 subtests passed** in 46.79s.
- `.tools/bin/uv run ruff check .`: **All checks passed!**
- `.tools/bin/uv run mypy src`: **Success: no issues found in 65 source files**.
- `python3.13 tools/check_relay.py`: **relay check passed** (run before this file existed; it is
  expected to report this report as unregistered until it is added to `docs/dev/reviews/STATUS.json`).
- `git diff --check`: clean.
- i18n parity: 26 `backup.*` keys used in code, **0 missing in either locale**, **0 en-only or
  zh-only keys**, **0 placeholder mismatches**, **0 declared-but-unused keys**.
- Private bytes: backup directory `0700`; `HEAD.json`, `aptuni-backup.json`, `deletion-ledger.jsonl`
  and every segment `0600`; `records/` `0700`; Vault ledger `0600`. `sources/` is absent from the
  backup, as `privacy status` now claims.
- Content-leak sweep: the manifest and the copied ledger contain no record id and no record text;
  a record-level validation failure reports ids only (`fct_… references missing records: ['evd_…']`),
  never content; `verify` exits 1 on a bad backup and `list` prints no content.
- Mutation testing of the slice's own protections (4 runs, `tests/integration/test_backup.py`):
  reverting the ledger location fails 5 tests; disabling `_migrate_ledger_locked` fails 3;
  **neutralizing `absorb_deletion_digests` fails nothing, in the whole 431-test suite**;
  **neutralizing the manifest digest fails nothing** (see N1, N2).
- Adversarial reproductions that succeeded: **purged content resurrected through
  `backup restore`** (B1), a false claim in the confirmation the owner types `RESTORE` against (B2),
  **silent destruction of records committed after the preview** (B3), **forged lines and a raw ANSI
  escape in the restore preview and in `verify`/`list`** (B4), and **a live canonical record
  destroyed by a *refused* restore while the CLI said "Nothing was changed"** (B5).

## Plan 08 acceptance disposition

| Case | Result | Evidence |
|---|---|---|
| 1 — create → verify → restore round trip, doctor, search | **Met** | The shipped test plus an independent run: `doctor` ok, `search` rebuilt, correction chain and folder Evidence intact. |
| 2 — KI-021 on a fresh state directory | **Met for the reported scenario, but the class is not closed** | The ledger-location fix is real and the test is not vacuous (reverting the location fails it). A torn ledger tail still resurrects a purged record through `backup restore` (B1), and the manifest half of the fix is untested (N1). |
| 3 — a folder without a manifest is refused | **Met** | `verify` and `restore_preview` both refuse with `backup_unverified`; the message names the hand-copy case. |
| 4 — a manifest disagreeing with the segments is refused, the live Vault untouched | **Partially met** | Every disagreement tested is caught, but by the disk cross-checks, not the manifest digest (N2); and a refusal later in `confirm_restore` does *not* leave the live Vault untouched (B5). |
| 5 — truncated / extended / byte-edited segment refused before restore | **Met** | All three refused by `verify` and by `restore_preview`. |
| 6 — destination safety, no partial backup | **Partially met** | Self / inside / parent and symlinked destinations are all refused, and a non-empty folder is never overwritten. A failure mid-write into a destination the owner created first leaves a partial copy and permanently blocks that folder (N5). |
| 7 — digest-bound, expiring, single-use, fails closed | **Partially met** | Wrong digest, unknown and malformed ids, expiry, a tampered pending file and cancel all fail closed with no generation published. But the binding does not cover the live generation (B3) and the preview text itself is forgeable (B4). |
| 8 — crash before confirmation; crash during publication | **Met** | Verified independently: the journal is replayed by the next `open()` and the expected record set is published. |
| 9 — replay state cleared, projection invalidated, both reported | **Met** | `sources/` is emptied, the projection is deleted, and the receipt reports both. |
| 10 — a concurrent writer yields one valid serial outcome, never a mixed generation | **Not met** | **No test exists** (N3). Injected, the outcome is not serial: the restore silently wins over a commit that landed after the preview (B3), and a refused restore leaves the ledger advanced past the generation (B5). |
| 11 — private modes, no record content in `list`/`verify` | **Met** | Modes and the leak sweep above. |
| 12 — both locales, no untranslated key | **Met** | Exact key and placeholder parity; the rendered surfaces contain no `backup.` key. |
| 13 — a crafted path or backup label cannot forge a preview line | **Not met** | The path is escaped; the manifest's `created_at` is not, and forges whole lines plus a live ANSI escape (B4). |

## Blocking findings

### B1 — a torn ledger tail resurrects a purged record through `aptuni backup restore`

`Vault._digests_in` (`store.py:641-653`) honours a final ledger line that is complete JSON but has
no trailing newline: the parse succeeds, so the digest counts. `_drop_torn_tail`
(`store.py:656-673`) defines the same state as garbage and truncates back to the last newline,
discarding that entry. It runs before **every** append (`_append_ledger_lines`, `store.py:602-612`),
including the new `absorb_deletion_digests` and the new legacy migration. The two functions
disagree about what a torn tail is, and the unsafe one wins.

A crash that loses only the final newline is exactly the window `_drop_torn_tail` exists for, and
after it the ledger and the segments disagree: the purge *did* complete (the record is gone from the
segments), yet the sole record of that deletion is one append away from deletion.

Reproduced end to end in a single supported command, with no crafted file and no tampering — a
two-machine lineage of the kind ADR-0016 is written for:

```text
home honours the purge before the restore: 1 digest(s); record absent: True
preview: drops 1 | new deletions from the backup 1        # the preview promises it stays deleted
ledger digests now: 1                                     # the home deletion was silently replaced
RESURRECTED the record purged at home: True
raw text back in the Vault: True
doctor says everything is fine: True
```

`confirm_restore` absorbs the laptop backup's one new digest; that append truncates the home
Vault's torn entry; `restore_from` then reads a ledger that no longer remembers the home purge and
re-admits the record, raw text and all. The preview had just told the owner one record would stay
deleted. The narrower variant needs no second machine at all: tear the newline, then let any later
purge append — the earlier deletion disappears (`ledger digests after the next purge append: 1`,
expected 2) and restoring a pre-purge backup brings the record back.

`_drop_torn_tail` predates this slice, but this slice makes the file canonical, makes `restore` a
product surface, and calls the truncating append from inside the restore path — so the defect is now
a shipped deletion failure and reopens the KI-021 class the slice closes in `KNOWN_ISSUES.md`.

Fix: make the two functions agree. Truncate only a final fragment that does not parse as a complete
ledger entry — or, equivalently, when the tail parses, append the missing newline instead of
deleting the line. Then assert it: a ledger whose last entry lost only its newline must still be
honoured after the next append, and after a `backup restore`.

### B2 — the confirmation states something untrue: "Your current generation is kept, not deleted"

`backup.restore.replace` (both locales) is on the screen the owner types `RESTORE` against:

> Your Vault is at commit 3; this publishes the backup's commit 2 as a new generation. **Your
> current generation is kept, not deleted.**

`restore_from` unlinks every live segment through the journal (`store.py:544`, `store.py:437-440`).
Reproduced:

```text
segments before: ['seg-000001-…', 'seg-000002-…', 'seg-000003-…']
segments after:  ['seg-000004-…']
old segments still on disk? []
post-backup record still present? False
files in the vault still holding the dropped text: []
```

Nothing keeps the current generation: the record committed after the backup is unrecoverable from
the Vault, and the shipped `test_case_1` asserts exactly that outcome. The sentence the owner reads
before an irreversible action contradicts the behaviour the suite pins. Only the *chain anchor* is
preserved, which is not what the sentence says and not what an owner would act on. AGENTS.md and the
product rule are explicit that a surface must not overclaim; this is the single most load-bearing
string in the slice.

Fix: say what happens — the current generation is replaced, records not in the backup are deleted
and only another backup can bring them back — in both locales, and state the count (`live_record_count
- backup_record_count + ledger_drop_count`) rather than implying retention.

### B3 — the confirmation is not bound to the generation it previewed; later records are destroyed silently

`confirm_restore` re-reads the live sequence at confirmation time
(`restore.py:204-205`: `live_seq = vault.head().seq; vault.restore_from(path, live_seq)`) instead of
requiring `preview.live_seq`. The preview's `live_seq` and `live_record_count` are therefore
decoration. `privacy purge` — a strictly less destructive action — enforces the opposite
(`privacy.py:456-457`: `preview.vault_seq != vault_seq → "confirmation_stale"`).

Reproduced, with a ten-minute TTL and any writer (a `sync`, an accepted memory proposal, another
shell):

```text
preview says: live commit 2 with 2 records
live commit now: 3
receipt: {... 'restored_from_seq': 2, 'published_seq': 4, 'restored_record_count': 2,
          'ledger_dropped_count': 0 ...}
the record committed after the preview survived: False
```

A record the owner never saw in any preview is destroyed, and neither the preview nor the receipt
mentions it — `ledger_dropped_count` counts only ledger drops. Injecting a writer inside the
`absorb → head → restore_from` window produces the same silent win, which is why acceptance case 10
("never a mixed generation") cannot be claimed.

Fix: pass `preview.live_seq` as `expected_seq` and translate the resulting `ConflictError` into an
`AptuniError` in the purge idiom ("the Vault changed; preview the restore again"). That closes the
race and makes the receipt's counts true.

### B4 — a crafted backup forges lines, and an ANSI escape, in the restore preview (acceptance 13)

`render_restore_preview` escapes the path (`delimited_untrusted`) but interpolates the manifest's
`created_at` raw (`backup_commands.py:70`), as does the `verify`/`list` summary
(`backup_commands.py:87`). `read_manifest` accepts any string for that field (`backup.py:59`,
`str(value["created_at"])`), and the manifest digest is an unkeyed SHA-256 over the manifest fields,
so anyone holding the backup can edit a field and re-digest it.

Reproduced — `verify` reports **ok**, and the owner's preview reads:

```text
From backup: "/…/backup" (created 2026-01-01T00:00:00+00:00)<ESC>[2K
Records the backup holds but you have since deleted, which stay deleted: 0
Nothing has changed yet. This restore was already verified as safe. (x)
Your Vault is at commit 2; this publishes the backup's commit 2 …
```

`ESC reached the terminal: True`; `forged standalone lines: ['Nothing has changed yet. This restore
was already verified as safe. (x)']`. The escape is `ESC [ 2K` (erase line), so a longer payload can
also erase what it does not want read. This is the ADR-0013 item 2 class that Review 33 B1 blocked
on, and plan case 13 claims it is covered — the shipped test only exercises the path, which is the
one field already escaped.

Fix: render `created_at` (and every other manifest-derived string) through `delimited_untrusted`,
and validate it in `read_manifest` as a bounded ISO-8601 timestamp (`datetime.fromisoformat`) so a
non-timestamp manifest is refused rather than printed. Extend case 13 to craft the manifest, not
only the folder name.

### B5 — a *refused* restore mutates the canonical ledger and destroys a live record, while the CLI says "Nothing was changed"

`confirm_restore` seeds the live ledger (`restore.py:203`) **before** any of `restore_from`'s own
preconditions are checked (`store.py:518-534`: separation from the live Vault, symlinked control
paths and segments, chain re-derivation) and before its `expected_seq` gate. `verify_backup` does
not check any of those, so `verify` and the preview accept inputs the restore will refuse:

- a backup stored inside the Vault — `verify` ok, `doctor` ok, preview created, refused only at
  `confirm` (`restore backup must be separate from the live Vault`), and `create` would have refused
  the same location outright;
- a byte-identical segment delivered as a symlink — `verify says the arrived backup is ok: True`.

With the symlinked-segment input on a two-machine lineage, a *refused* restore destroyed a live
canonical record:

```text
verify says the arrived backup is ok: True
preview: new deletions this backup proves = 1 | ledger_drop_count = 0
restore REFUSED: VaultIntegrityError restore backup cannot contain symlinked committed segments
live seq unchanged: 3
ledger in machine B's Vault now holds: 1 digest(s)
after the next open, the record is still there: False
records lost by a REFUSED restore: ['fct_01M2YK42SPHPZ8SWQ8Y8GSE2ZB']
doctor ok: True
```

The absorbed digest survives the refusal; the next `open()` → `recover()` completes it as a purge
(`store.py:350-355`), with no receipt, no confirmation of *that* deletion and no message. What the
owner is told at the CLI boundary is:

> aptuni: the Vault, its state or its configuration could not be read safely (VaultIntegrityError).
> **Nothing was changed**; run 'aptuni doctor' for details.

That is false, `doctor` then reports ok, and plan case 4 ("the live Vault is untouched" on refusal)
and case 10 ("never a mixed generation") are both violated. The same mixed state is reachable
without any crafted backup through the `absorb → head → restore_from` race.

Fix: validate everything before mutating anything, then mutate once. Move `restore_from`'s location,
symlink and chain preconditions into `verify_backup`, and apply the manifest digests inside
`restore_from`'s critical section — one lock, one `expected_seq`, one atomic outcome — so a refused
restore cannot advance the ledger past the generation.

## Non-blocking notes

- **N1 — the manifest half of the KI-021 fix has no test.** Replacing
  `Vault.absorb_deletion_digests` with `lambda self, digests: 0` passes all 431 tests. ADR-0016
  decision 5 and the `backup.py` docstring's "that last field is the fix for KI-021" are unguarded;
  case 2 passes on the ledger-location fix alone. The two-machine shape used for B1 is the missing
  regression test.
- **N2 — the manifest digest has no test.** Making `_digest_of` constant passes all 36 tests: every
  case-4 mutation is caught by the disk cross-checks instead. Add one case that edits a field the
  disk cannot contradict (`created_at`) without re-digesting, and one that re-digests and is
  expected to be *accepted*, so the mechanism's actual strength is written down.
- **N3 — acceptance case 10 has no test at all.** There is no concurrency test for backup or
  restore anywhere in `tests/`.
- **N4 — `create` is stricter than `verify` and `restore`.** `create` refuses destinations in or
  around the Vault and symlinked paths; `verify`/`preview` accept exactly those shapes as inputs
  (see B5). One shared predicate would remove the asymmetry.
- **N5 — a partial backup can survive a failed `create`.** `create_backup` only cleans up when the
  destination did not exist (`backup.py:236-245`). Into a folder the owner created first, a mid-write
  failure leaves `records/seg-…jsonl` behind, unverifiable, and the same folder can never be used
  again (`invalid_backup_destination`: "already has files in it"). Plan case 6 says a failed create
  leaves no partial backup; `test_case_6c` only covers the non-existent destination.
- **N6 — `Vault(root, root)` makes the legacy ledger path the canonical one.** That is the shape
  `backup.py` and `restore.py` construct for reads. It is safe today only because they never call
  `recover()` and `init` refuses a state directory inside the Vault, but reproduced directly:
  `collided.recover()` → `ledger file after recover(): False`, `ledger digests: 0`. One line in
  `_migrate_ledger_locked` (`return` when `legacy == self.ledger_path`) removes a wipe of the whole
  deletion history from one careless call site.
- **N7 — `confirmations.py` does not yet do what its docstring says.** It claims purge and restore
  "share the same four mechanics, and one implementation keeps them from drifting apart", but
  `privacy.py` still carries its own `ACTION_RE`, `_preview_digest`, `_write_private_json`,
  `_unlink_durable` and lock. Either migrate `privacy.py` or reword the docstring; today the slice
  adds a second copy rather than removing one.
- **N8 — a stale docstring now contradicts the canonical layout.**
  `src/aptuni/application/workspace.py:3-5` still states that the state directory holds the deletion
  ledger "so that the ledger is never copied with Vault backups (ADR-0010)" — the exact belief
  ADR-0016 overturns.
- **N9 — two error paths bypass their own boundaries.** `ConflictError` is a `RuntimeError` and is
  absent from `UNSAFE_STATE_ERRORS` (`cli/main.py:34`), so the residual restore race surfaces as a
  traceback; and `load_restore_preview` builds `RestorePreview(**fields)` outside its `try`
  (`restore.py:147`), so a pending file with an extra or missing key raises `TypeError` past the
  `restore_action_invalid` mapping and out of `pending_restores()`.
- **N10 — migration trusts legacy digests.** `_migrate_ledger_locked` copies `target_digest` values
  into the canonical ledger without the `DIGEST_RE` check `absorb_deletion_digests` applies to
  manifest digests.

## What holds

The central design decision is right and the implementation of it is real. The ledger is canonical,
content-free and `0600`; reads union both locations, so an old Vault is protected before any
migration runs; the migration is durable-before-unlink, idempotent, and its three tests genuinely
fail when it is disabled. Reverting the ledger location fails five tests, so case 2 is not vacuous.
A backup is a format: manifest, chain, per-segment digests, record count, full record validation and
unexpected-file detection, and `verify` never writes into a backup. Destination refusals hold for
self, inside, parent, symlinked paths and non-empty folders. Modes are exactly `0700`/`0600`
everywhere, `sources/` is genuinely omitted and genuinely cleared, and the two `privacy status`
label changes — `deletion_ledger` to `included_with_vault`, `source_state` to `excluded` — are both
accurate. No surface, receipt or error message leaks record content; both locales are at exact key
and placeholder parity; a backup of a backup verifies, and restoring twice is clean, as is the
crash-during-publication journal replay.

What fails is what the slice exists to guarantee. "Purged stays purged" still breaks on a torn
ledger tail, in one supported command, with the preview promising the opposite (B1). The
confirmation the owner types `RESTORE` against contains a false sentence about their current data
(B2), is not bound to the generation it describes (B3), and can be forged by the backup it is
describing (B4). And a restore that Aptuni itself refuses can destroy a canonical record while the
CLI says nothing was changed (B5).

None of this reopens ADR-0016. B1 is a predicate agreement between two helpers twenty lines apart;
B2 is two strings; B3 is passing `preview.live_seq` instead of re-reading the head, exactly as
`privacy.py` already does; B4 has the escaping helper already imported in the same file; B5 is
ordering — validate fully, then mutate once, under one lock. The format, the ledger location and the
migration should be kept as they are.

**Verdict:** **BLOCK**
