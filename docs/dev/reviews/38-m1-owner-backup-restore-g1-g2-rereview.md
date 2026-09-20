# Review 38 — M1 owner backup/restore G1/G2 focused re-review

**Date:** 2026-09-20

**Reviewer:** independent correctness, security and privacy re-review agent (read-only except for
this report)

**Scope:** the current uncommitted Slice 14 worktree after Review 37, limited to G1 restore/ledger
atomicity, G2 refused-filesystem owner boundaries, their regressions, and correctness/security/privacy
defects introduced by those fixes. Read first: `AGENTS.md`, Reviews 35–37, ADR-0010, ADR-0016, the
changed backup/restore/Vault/CLI source, and `tests/integration/test_backup.py`.

## Validation

- `.tools/bin/uv run pytest tests/integration/test_backup.py -k 'g1 or g2' -q`: **6 passed**.
- Re-drove Review 37's cross-machine deletion lineage and crashed at `after_head_tmp`: reopening
  with the original state directory succeeds because its restore journal completes the operation.
- Re-drove the same crash with a fresh state directory, as the project explicitly permits for
  disposable host state: the canonical ledger contains the incoming deletion, canonical HEAD is
  still the old generation, and `Vault.open(vault.root, fresh_state)` fails permanently with
  `InvariantError: purge would orphan ...; purge it too`.
- Inspected the G2 exception paths: `_check_against_disk` now catches
  `UnsupportedFilesystemError`, `verify_backup` returns a failed content-free summary, restore
  preview converts that summary to `backup_unverified`, and the CLI last-line boundary also includes
  `UnsupportedFilesystemError`.

## Review 37 closure

### G2 — refused-filesystem inspection escaped as a traceback — **closed**

`backup.py:135-139` now constructs the read-only `Vault(path, path)` inside the `UNREADABLE` guard,
whose tuple includes `UnsupportedFilesystemError`. Thus `verify` and `list` return an owner-readable
failed summary rather than raising; restore preview consumes the same failed summary and refuses
before it can touch the live Vault. `cli/main.py:35-36` also includes the exception in
`UNSAFE_STATE_ERRORS`, providing the required last-line boundary if another path raises it.

The focused regression drives both `verify` and `list`, asserts exit 1 and an actionable `exfat`
message, and fails on the pre-fix construction outside the guard. The preview path is not named in
that test, but it has no distinct exception route: it calls the same `verify_backup` first and raises
`AptuniError("backup_unverified", ...)` on the returned summary. I found no remaining correctness,
security or privacy blocker in G2.

### G1 — restore and ledger append are atomic — **not closed**

The new format-2 journal is a real improvement for an unchanged state directory. `restore_from`
stages the replacement segment first, then durably writes a journal containing both the replacement
HEAD and incoming deletion digests (`store.py:583-604`). Recovery reads that journal, records the
digests, and immediately publishes HEAD (`store.py:416-461`). This closes Review 37's reproduced
same-state crash and ENOSPC-before-journal cases, and the new tests cover all four existing crash
hooks plus the early segment-write failure.

However, the journal is stored in the disposable state directory (`store.py:405-406`) while the
first half of the transaction — the deletion ledger — is canonical in the Vault. Atomic recovery
therefore depends on preserving state which `workspace.py` and ADR-0016 explicitly say may be wiped
and rebuilt.

## Blocking finding

### B1 — losing disposable state after a mid-publication crash still strands the canonical ledger against the old generation

At `after_head_tmp`, `_recover_restore_locked` has already appended the backup's deletion digests to
`<vault>/deletion-ledger.jsonl` (`store.py:452-455`), but `HEAD.json` still names the old live
generation. The only durable description of the replacement generation is
`<state>/restore-intent.json`. If that disposable state directory is cleared, lost during a machine
migration, or simply replaced with a fresh one before the next open, recovery cannot discover the
transaction. It instead applies the newly canonical deletion to the old generation through normal
ledger recovery, recreating Review 37 G1's permanent `InvariantError` wedge.

Reproduction used only the supported lineage from Review 37 and the documented fresh-state
operation:

```text
A: remember Fact; backup create
B: restore A backup; privacy purge Fact; backup create
A: correct Fact; restore B backup; crash at after_head_tmp

old HEAD seq: 3
canonical ledger digests: 1
old state restore journal exists: true
Vault.open(A_vault, fresh_state):
  InvariantError: purge would orphan fct_...; purge it too
```

Opening with the original state succeeds, confirming that the missing journal is the only
difference. Hand-removing the canonical ledger would reopen the old generation but resurrect the
cross-machine purge, so it is not a valid recovery. This violates ADR-0010's atomic-restore
requirement, ADR-0016's canonical/deletions-travel contract, and the stated rule that the state
directory is disposable. The current G1 regression always reopens with `vault.state_dir`
(`test_backup.py:994`), so it cannot detect the failure.

**Actionable fix:** place the restore transaction journal in the canonical Vault (or otherwise make
the replacement HEAD plus incoming digests recoverable without any state-directory bytes) before a
canonical ledger append can occur. Keep the ordering journal → ledger → HEAD, and remove the journal
only after HEAD and cleanup are durable. Add a regression that crashes at `after_head_tmp`, opens the
same Vault with an empty fresh state directory, and proves the Vault opens with a ledger/generation
pair that agrees and does not resurrect the purged record. Also cover the no-journal early crash to
prove a fresh-state open safely retains the old generation.

No non-blocking note is added: the remaining defect is a correctness/privacy and milestone-exit
failure, while G2 is closed.

**Verdict:** **BLOCK**
