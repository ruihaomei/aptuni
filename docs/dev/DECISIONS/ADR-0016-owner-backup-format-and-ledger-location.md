# ADR-0016: Make the owner's backup a verified format and keep the deletion ledger in the Vault

- **Status:** Accepted (2026-09-20, maintainer chose the ledger location directly)
- **Date:** 2026-09-20
- **Deciders:** maintainer (final say) · proposing agent · reviewing agent
- **Amends:** ADR-0001 (canonical Vault layout), ADR-0010 (retention, destruction and restore)
- **PRD refs:** §4, §14, §23 (Retention Guard), §52
- **Research refs:** KI-021 reproduction 2026-09-20; `docs/dev/plans/08-owner-backup-and-restore.md`
- **Needs maintainer confirmation:** no (the maintainer selected "move the ledger into the Vault" on
  2026-09-20 after the reproduction was presented)

## Context

`Vault.restore_from` shipped in Slice 12: atomic, chain-preserving, journaled, and reviewed. But
nothing in the product could produce an input for it, and `aptuni export` states in its own output
that it is not a restorable backup. The owner had no supported way to make a restorable copy of their
own canonical Vault — in a product whose first principle is that the owner keeps their data.

Building that surface exposed a defect in the existing layout. ADR-0001 put the deletion ledger at
`<state>/deletion-ledger.jsonl`, and the `store.py` layout comment described it as living "outside the
Vault and its backups". The ledger is the only thing that stops a restore from re-admitting a purged
record. The state directory is documented as disposable and rebuildable. Those two facts contradict
each other, and ADR-0010's own acceptance requirement — "restore a backup predating purge and prove
the deletion ledger prevents resurrection" — only held on the original machine.

Reproduced on 2026-09-20: purge a Fact, then restore a pre-purge Vault copy.

| Live state directory | Ledger entries seen | Purged Fact after restore |
|---|---|---|
| the original one | 1 | absent (correct) |
| a fresh one | 0 | **restored** |

A new machine, a reinstall, or a cleared state directory silently resurrected a record the owner had
explicitly deleted. No CLI reached `restore_from`, so the path required a hand-copied Vault — but
shipping `aptuni backup` would have made it the recommended flow.

## Decision

**1. The deletion ledger is canonical and lives in the Vault.**

```text
<vault>/HEAD.json                  committed manifest, hash-chained
<vault>/records/seg-NNNNNN-*.jsonl immutable canonical segments
<vault>/deletion-ledger.jsonl      irreversible id digests; canonical, travels with the Vault
<vault>/restore-intent.json        in-flight ledger + HEAD transaction; normally absent
<state>/writer.lock                flock target
<state>/projections/…              disposable
```

A deletion is a durable fact about the owner's data, not an acceleration structure, so it belongs
with the data. The ledger stays content-free: each entry is a one-way SHA-256 digest of a record id
and never the record itself, so moving it into the portable Vault discloses nothing new.

**2. Reads union both locations; `recover()` migrates.** `ledger_digests()` returns the union of the
Vault ledger and any not-yet-migrated state-directory ledger, so an old Vault is protected from the
first read, before any migration runs. `recover()` — which `open()` always calls — folds the legacy
file into the Vault: entries are durable in the Vault *before* the old file is unlinked, so a crash in
between leaves both present and the next pass unlinks the redundant copy. Migration is idempotent,
never duplicates an entry, and tolerates a torn legacy tail.

**3. A backup is a format, not a folder copy.** A backup directory holds the Vault control paths plus
`aptuni-backup.json`: format version, creation time, source sequence, `chain`/`chain_base`, every
segment name with its digest, the record count, and the deletion digests as of creation. The manifest
is itself digested, so a later edit is detectable. `verify_backup` checks the manifest against the
bytes on disk — segments, chain, record count, unexpected files, full record validation — and requires
the copied ledger to match the manifest's digests.

**4. A folder without a manifest is not a restore input.** `verify` and `restore` both refuse it and
say so in plain language. A hand-copied Vault directory is explicitly unsupported for restore. This is
what keeps the KI-021 class closed at the product boundary rather than by convention. `verify` also
refuses every shape a backup can be judged on alone — a symlinked `HEAD.json`, `records/`, manifest or
committed segment — so it does not accept inputs the restore will reject. "Separate from the live
Vault" is inherently relative, so it stays with `check_restore_source` on the restore path, which runs
before any preview exists (Review 36 N4).

**5. Restore unions deletions from both sides, inside one critical section.** The backup manifest's
digests are passed into `restore_from` as `extra_deletion_digests` and recorded there, after every
precondition and after the `expected_seq` gate, so a restore Aptuni refuses can never leave a digest
behind for `recover()` to apply as an unconfirmed purge. `restore_from` then drops every record whose
digest is ledgered. `Vault.check_restore_source` exposes those preconditions with no side effect, so
`verify` and the preview refuse exactly what the restore would refuse rather than accepting inputs
that fail late (Review 35 B5, N4).

Nothing is recorded until the whole outcome is known to be valid. `restore_from` simulates the drop
and runs `RecordSet(kept).validate()` *before* it appends the manifest's digests, because a restore
that record validation refuses would otherwise leave the canonical ledger advanced — and the next
`open()` would then try to complete a purge nobody confirmed, wedging the Vault with no in-product
repair. The replacement segment is staged first, then a canonical restore journal durably binds its
new HEAD to the incoming deletion digests. Recovery clears disposable replay state, appends the
ledger, and immediately publishes HEAD. The journal lives in the Vault, not disposable state, so a
fresh-state reopen can finish the transaction; it is removed only after publication and cleanup.
Thus the ledger is durable before canonical publication and cannot be stranded against the old
generation (Reviews 37–39).

A restored generation that keeps nothing has the same hash chain as the live one, so the HEAD republish
is decided on the sequence, not the chain. A chain-only comparison skipped the write while the old
segments were unlinked anyway, leaving HEAD naming files that no longer existed (Review 36 F2).

The deletion ledger's two helpers must agree on what a torn tail is. `_digests_in` honours a final
line that is complete JSON without a trailing newline — a crash that lost only the newline — so
`_drop_torn_tail` terminates such a line instead of truncating it. While they disagreed, the
truncating append ran inside the restore path and a completed purge could be forgotten, which
re-opened exactly this class (Review 35 B1).

**5b. The preview states both counts, and states them truthfully.** `restore_from` unlinks every live
segment, so the current generation's records are removed, not kept. The preview names
`discarded_record_count` — live records the backup does not hold, computed from the two record sets
rather than inferred from totals — alongside `ledger_drop_count`, and the receipt repeats both
(Review 35 B2). Every manifest-derived string is rendered through `delimited_untrusted` and
`created_at` is validated as a bounded ISO-8601 instant, because anyone holding a backup can edit a
field and re-digest it (Review 35 B4).

**6. Restore keeps the project's confirmation discipline.** `aptuni backup restore preview | confirm |
cancel`, mirroring `privacy purge`: a digest-bound, expiring, single-use action confirmed by one exact
action id. `--confirm-digest` names that action, so a scripted caller can finish what a preview
started; without a terminal and without a digest, nothing is restored. The confirmation is bound to
the *generation* it described: `preview.live_seq` is the `expected_seq`, so a commit landing between
preview and confirmation refuses the restore with `restore_confirmation_stale` instead of silently
destroying a record the owner never saw — the same rule `privacy purge` already enforced
(Review 35 B3).

## Consequences

- An owner can finally make and verify a restorable copy, and roll one back, which closes the M1.1
  restore clause and the M1.5 rollback/migration drill.
- The Vault gains one small content-free file. Anything that enumerates the Vault must expect it;
  `privacy status` now reports it as `included_with_vault` rather than `excluded`.
- A backup is a complete unencrypted copy of the canonical records, including hidden modules. It is
  written mode 0700/0600 outside the Vault, and `create` says plainly that protecting it is the
  owner's job. Encryption is deliberately out of scope for this slice.
- Because the copy is plaintext, `create` applies the Vault filesystem gate to the destination up
  front and refuses a synchronized folder or a filesystem it cannot verify on, with a message the
  owner can act on. Refusing before writing is the point: the previous ordering let the gate escape
  as a traceback only after the plaintext copy was already on disk (Review 36 F3).
- Restoring a backup taken before a purge now keeps that purge on every machine. Restore can never
  undo a purge, which is correct: purge means deletion.
- A hand-copied Vault folder cannot be restored by Aptuni. This is the honest trade: making an
  unlabelled copy restorable is exactly what re-admitted deleted records.

## Rejected alternatives

- **Manifest-only fix** (carry the ledger in the backup, leave the canonical layout alone). Protects
  only backups taken *after* a purge. The reported KI-021 scenario — a backup predating the purge,
  restored on a fresh state directory — stays broken, so ADR-0010's acceptance requirement stays
  unmet.
- **Fail closed instead** (refuse a restore whenever the ledger's provenance for this Vault cannot be
  proven). Safe, but it blocks restoring onto a new machine, which is the main reason backups exist.
- **Chain the ledger into HEAD.** Tempting for tamper evidence, but a purge must append to the ledger
  *before* it rewrites segments (ADR-0010, S01 F3), and folding it into the commit chain would invert
  that ordering. The owner can edit their own open-format Vault regardless; the guarantee worth making
  is that *Aptuni's own* backup and restore never resurrect a purged record.
- **Automatic backup before purge.** Would quietly recreate the data the owner asked to destroy.

## Verification

- `tests/integration/test_backup.py`: 61 tests covering the round trip, the KI-021 regression on a
  fresh state directory, manifest and segment tampering, destination safety, digest-bound confirmation,
  crash recovery, derived-state invalidation, private modes, both locales, preview forgery, the
  legacy-ledger migration including its idempotency and torn-tail cases, and one regression per
  Review 35 finding: the torn-newline ledger entry, the manifest-only two-machine lineage, the
  discarded-record count, the stale generation, the re-digested hostile timestamp, the refused
  restore, the manifest digest, concurrency, partial-create cleanup, and the `Vault(root, root)` wipe.
- Dogfood on a simulated new machine: purge a Fact, point an empty state directory at the Vault,
  restore the pre-purge backup. The preview reported `ledger_drop_count = 1`, the restore reported one
  record kept deleted, `doctor` passed, `search` rebuilt, and a raw byte scan of the Vault found no
  trace of the purged text.
- Negative checks: every claim is mutation-tested. Reverting the ledger location fails 5 tests;
  disabling the migration fails 3; reverting the torn-tail agreement, the generation binding, the
  timestamp validation, the render escaping and the validate-before-mutate ordering each fail their
  own regression. The pre-fix behavior was reproduced before each change, not assumed.
- Independent Review 35 returned **BLOCK** on five reproduced findings (B1 torn-tail resurrection,
  B2 a false sentence in the confirmation, B3 an unbound generation, B4 a forgeable preview,
  B5 a refused restore destroying a record) plus ten non-blocking notes. Review 36 independently
  confirmed B1–B4 and N1–N9 closed by mutation, and returned **BLOCK** on three further findings the
  B5 remediation had introduced or exposed: F1 (digests recorded before the drop was validated),
  F2 (an empty restored generation left HEAD naming unlinked segments) and F3 (the filesystem gate
  escaping after the plaintext copy was written). All three are remediated above, each with its own
  mutation-tested regression. Reviews 37 and 38 found two further atomicity/owner-boundary failures;
  Review 39 independently fault-injected every crash point with a fresh disposable state directory,
  verified legacy journal recovery, and closed the stream **APPROVE**.
