# Milestone 1 Slice 14 — Owner backup and restore

**Status:** Accepted 2026-09-20 (plan 07 orders this first)
**Decision basis:** ROADMAP M1.1 "migration/backup restore failure matrix" and M1.5 "rollback and
migration drill"; ADR-0001 (canonical Vault), ADR-0010, ADR-0013 (confirmation); KI-021; the
`Vault.restore_from` implementation and its ten tests shipped in Slice 12.
**Risk class:** high — deletion correctness and canonical replacement. Independent review required.

## Problem

Three facts hold at `db7a5d9`:

1. `Vault.restore_from` is implemented, hardened and reviewed, but **no product surface can produce
   an input for it**. The owner cannot make a restorable copy of their own canonical Vault.
2. `aptuni export` says in its own output that it is not a restorable backup, and it deliberately
   omits pending/rejected/revoked records and all `full_content`.
3. **KI-021, reproduced 2026-09-20:** the deletion ledger that enforces "purged stays purged" lives
   in the state directory, not in the portable Vault. Restoring a pre-purge Vault copy with a fresh
   state directory re-admits the purged record — `ledger=0, goals=1` where the same-state-directory
   run gives `ledger=1, goals=0`.

Shipping a backup command without fixing (3) would turn a hand-copy edge case into the product's
recommended flow. So the format and the fix land together, in one slice.

## User-visible capability

- `aptuni backup create PATH` — write a verified, self-describing backup of the canonical Vault.
- `aptuni backup verify PATH` — check a backup end to end without touching the live Vault: manifest,
  hash chain, every segment digest, record validation, and deletion-ledger coverage.
- `aptuni backup list [DIR]` — show backups with their Vault sequence, record count, creation time
  and verification status. No record content.
- `aptuni backup restore PATH` — preview exactly what the restore replaces, drops and keeps, then
  accept one terminal confirmation bound to the preview digest before publishing the generation.

## Design

**Backup is a format, not a folder copy.** A backup directory holds the Vault control paths plus
`aptuni-backup.json`: format version, creation time, source Vault sequence, `chain`/`chain_base`, each
segment name with its digest, the record count, and the **deletion-ledger digests as of creation**.
The manifest is itself digested so a silent edit is detectable. ADR-0016 records the format; no
canonical Vault schema changes, so ADR-0001 stays closed.

**Restore unions the ledgers.** `restore_from` already drops records whose digest is in the live
ledger. Restore additionally seeds the live ledger from the backup manifest before calling it, so a
purge recorded on either side is honoured. A backup with no manifest is refused: it is not a
supported restore input, and `verify` says so in plain language.

**Restore keeps the project's confirmation discipline.** Preview → digest-bound, expiring terminal
confirmation, mirroring `privacy purge` and `setup apply`. The preview names the live sequence being
replaced, the backup sequence arriving, the record delta, the count of records the ledger will drop,
and the fact that source replay state is cleared. Cancellation changes nothing.

**Backup never widens exposure.** A backup is a copy of canonical records including hidden modules,
so it is written mode 0700/0600 outside the Vault, refuses a destination inside or containing the
live Vault, and `create` states plainly that the copy is unencrypted and now the owner's to protect.

## Acceptance (each is one failing test first)

1. `create` → `verify` → `restore` round-trips a Vault with facts, evidence, memories and a
   correction chain; `doctor` passes and `search` finds the restored records after reindex.
2. **KI-021:** purge a record, then restore a pre-purge backup with a **fresh state directory**. The
   purged record does not come back, and the preview says how many records the ledger dropped.
3. A backup without `aptuni-backup.json` is refused by both `verify` and `restore`.
4. A manifest whose digest, segment list, chain or record count disagrees with the segments on disk
   is refused, and the live Vault is untouched.
5. A truncated, extended or byte-edited segment is refused by `verify` before `restore` is reachable.
6. `create` refuses a destination equal to, inside, or containing the live Vault; refuses to
   overwrite a non-empty directory; and leaves no partial backup when it fails mid-write.
7. Restore is digest-bound and expiring: a stale digest, a tampered preview, a wrong action id and
   anything but the terminal confirmation word all fail closed with no generation published.
8. A crash between the preview and the confirmation leaves the live Vault at its original sequence;
   a crash during publication is completed by the next `open()` (existing journal, re-asserted here).
9. Restore clears source replay state, invalidates the retrieval projection, and reports both.
10. A concurrent writer during restore yields one valid serial outcome, never a mixed generation.
11. Backup files are mode 0600 in a mode 0700 directory; `list` and `verify` print no record content.
12. Every new message renders in English and Simplified Chinese with no untranslated key.
13. A crafted Vault path or backup label cannot forge a line in the restore preview.

## Exclusions

No encryption, no scheduling, no remote destinations, no incremental or differential backups, and no
automatic backup before purge. Those are separate decisions; this slice gives the owner the primitive
and one honest confirmation. A hand-copied Vault folder stays unsupported as a restore input.

## Exact commands

```sh
.tools/bin/uv run pytest tests/integration/test_backup.py -q
.tools/bin/uv run pytest
.tools/bin/uv run ruff check . && .tools/bin/uv run mypy src
python3.13 tools/check_relay.py
```

Dogfood: `init → remember → sync a folder → backup create → privacy purge → backup restore` with a
fresh `APTUNI_STATE_DIR`, then `doctor` and `search`.

## Exit evidence

- Acceptance 1–13 pass as named tests; the KI-021 case is a permanent regression test.
- KI-021 moves to resolved history with the reproduction and the fix recorded.
- Independent review returns no blocking correctness, security, privacy or contract findings.
- `STATE.md`/`HANDOFF.md` record the checkpoint hash and the remaining limitations.
