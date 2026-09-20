# Review 39 — M1 owner backup/restore atomicity re-review

**Date:** 2026-09-20

**Reviewer:** independent correctness, security and privacy re-review agent (read-only except for
this report)

**Scope:** the current uncommitted Slice 14 worktree after Review 38, limited to the Review 38 B1
remediation, all restore crash hooks with fresh disposable state, G2's refused-filesystem boundary,
and compatibility with the former state-local restore journal. Read first: `AGENTS.md`, Reviews
35–38, ADR-0010, ADR-0016, and the changed Vault/backup/restore/CLI source and focused tests.

## Validation

- `.tools/bin/uv run pytest tests/integration/test_backup.py -k 'g1 or g2'
  tests/integration/test_vault.py -k 'restore_crash or g1 or g2' -q`: **8 passed**.
- `.tools/bin/uv run pytest tests/integration/test_backup.py tests/integration/test_vault.py -q`:
  **84 passed**.
- Independently fault-injected the Review 37 cross-machine deletion lineage at every crash hook,
  discarded the original host state, and reopened the Vault with a new empty state directory.
- Independently converted an interrupted canonical format-2 journal into the former state-local
  format-1 shape, then reopened and verified recovery and journal cleanup.

## Review 38 B1 — **closed**

The restore journal is now canonical at `<vault>/restore-intent.json`
(`store.py:405-409`). `restore_from` durably stages the replacement segment, writes the journal, and
only then calls recovery (`store.py:583-619`). Recovery validates the entire journal and replacement
generation before mutation, then performs the required canonical order: deletion ledger, HEAD,
old-segment cleanup, journal removal (`store.py:430-476`). No byte from the disposable state
directory is needed to resolve that transaction.

The fresh-state fault matrix produced exactly the two valid atomic outcomes:

| Crash point | Sequence | Purge target | Incoming digest | Recovery |
|---|---:|---|---|---|
| `after_segment_tmp` | 3 → 3 | present | absent | old generation retained, orphan tmp removed |
| `after_segment_rename` | 3 → 3 | present | absent | old generation retained, staged segment removed |
| `after_head_tmp` | 3 → 4 | absent | present | journal completes publication |
| `after_head_rename` | 3 → 4 | absent | present | journal finishes idempotent cleanup |

Every reopened Vault passed full verification; every canonical journal was removed. In particular,
the Review 38 reproduction at `after_head_tmp` no longer wedges: the fresh state finds the journal
in the Vault, publishes the replacement HEAD, and never attempts to apply the incoming deletion to
the old correction chain.

The regression is materially stronger than Review 37's: the parametrized test reopens each crash
with `fresh-state-<point>`, asserts the target's presence is the inverse of ledger membership, and
checks the expected old/new sequence. The segment-write `ENOSPC` regression still proves a failure
before the journal leaves both HEAD and ledger unchanged.

## Legacy state-local journal compatibility — **no blocker**

`_pending_restore_journal_path` accepts the former `<state>/restore-intent.json` only when no
canonical journal exists, and fails closed if both exist. The parser continues to accept format 1,
whose missing deletion list correctly means no incoming digests, as well as format 2. Recovery
unlinks the path it actually consumed.

An independent format-1 recovery run completed the staged generation, advanced HEAD, passed
`verify()`, and removed both the legacy and canonical journal paths. The dual-journal refusal is
appropriate: two independently durable transaction descriptions are ambiguous and must not be
guessed between. I found no backward-compatibility defect in this path.

## G2 — **remains closed**

The remediation reviewed in Review 38 is unchanged: constructing the inspection Vault is inside
`backup.py`'s `UNREADABLE` guard, that guard includes `UnsupportedFilesystemError`, and the CLI's
last-line boundary includes the same exception. The focused regression still proves owner-readable
`verify` and `list` failures with no traceback. Restore preview uses the same failed
`verify_backup` summary and refuses with `backup_unverified` before live mutation.

## Findings and judgment

No blocking correctness, security, privacy, contract, or milestone-exit finding remains in the
reviewed scope. The canonical-journal change restores the advertised disposable-state property
without weakening the ledger-before-HEAD rule, early failures still abort safely, post-journal
failures converge safely, and the shipped legacy journal has a fail-closed recovery path.

**Verdict:** **APPROVE**
