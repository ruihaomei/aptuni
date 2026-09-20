# Review 30 — M1 privacy purge remediation focused re-review

**Date:** 2026-09-20

**Reviewer:** independent privacy/security re-review agent (read-only except for this report)

**Scope:** remediation of Review 29 B1–B7 in the current uncommitted diff. The re-review read the
full remediation diff and Review 29, ran all new privacy/Vault regressions, repeated the original
adversarial cases, and probed the new lock, exact-copy and restore publication boundaries.

## Validation

- `.tools/bin/uv run pytest tests/integration/test_privacy_purge.py
  tests/integration/test_privacy_inventory.py tests/integration/test_vault.py -q`: **33 passed**.
- Review 29 B1, B2, B4, B5 and B6 adversarial states now fail closed or recover as intended.
- Temporary probes reproduced the two remaining correctness failures below. All probes used
  `TemporaryDirectory`; no repository fixture or personal data was written.

## Review 29 finding disposition

| Review 29 | Result | Evidence |
|---|---|---|
| B1 parent-symlink deletion | **Verified for pre-existing aliases** | The adapter/source parent-alias regressions leave external markers intact and return `incomplete_retryable`. `_owned_child()` rejects a pre-existing aliased component before cleanup (`src/aptuni/application/privacy.py:234-248,367-375`). |
| B2 source sync after intent | **Verified** | Purge confirmation and sync now share `source_operations_lock` in the same order (`privacy.py:529-547`; `source_commands.py:185-189`). A durable source intent blocks later sync, including after restart (`ingest.py:190-204`). The regression proves no source-derived Evidence survives. |
| B3 exact managed-copy scope | **Partially fixed; still blocking** | IDs and external provider/destination metadata are digest-bound, and later adapter files are not silently deleted. A managed copy created after preview can still retain purged content; see R1. |
| B4 CLI retry | **Verified** | Scripted retry no longer requires the removed pending preview (`cli/main.py:587-596`); the injected one-shot projection failure returns 2 then 0 on the same exact action/digest. |
| B5 stale terminal intent | **Verified** | Terminal receipt recovery durably unlinks the matching intent (`privacy.py:392-416,529-533`); the crash-state regression then completes a new purge. |
| B6 restore traversal | **Verified** | HEAD parsing now requires protocol segment basenames, digest/count types and uniqueness (`vault/store.py:173-194`). The original `../../` artifact is rejected without changing the live HEAD. |
| B7 restore publication ordering | **Not fixed; still blocking** | Cleanup moved before HEAD publication but is not atomic or journaled. A later publication failure now destroys replay state while leaving the old live generation; see R2. |

## Blocking findings

### R1 — Copies created after preview are not detected, so a complete receipt can leave purged content in SQLite

The preview includes `retrieval_projection` only if the database exists at preview time
(`src/aptuni/application/privacy.py:279-295`). Confirmation deletes only the frozen tokens
(`src/aptuni/application/privacy.py:490-502`) and validates staleness only through Vault sequence and
policy epoch. Creating a projection does not advance either value.

Reproduction:

1. Create a private Fact without searching, then preview its purge. The preview does not contain
   `retrieval_projection`.
2. Search after preview. `SqliteProjection.ensure()` builds the projection from the still-live Fact
   (`src/aptuni/application/service.py:267-283`).
3. Confirm the unchanged action/digest.

Observed result:

```text
projection_in_preview False
projection_created True
terminal complete_managed_external_action_needed
projection_survives True
SQLite row: (<purged fact id>, 'post preview private marker')
```

The deletion ledger prevents canonical resurrection, but the managed derived copy still contains the
purged text while the receipt says managed cleanup is complete. The same missing state-generation
check permits later adapter/memory copies; the new adapter regression explicitly preserves a grant
created after preview. Exact snapshot semantics require either (a) comparing the complete managed
copy set/generation again before intent commit and staling on additions or replacement, then
serializing creators once committed, or (b) digest-binding explicit always-run copy-class effects
such as projection invalidation even when the copy was absent at preview. Add the projection sequence
above as a regression and verify the raw SQLite row is absent before a complete receipt is published.

### R2 — Restore still has a destructive pre-publication window and no recovery journal

`restore_from()` now holds the shared source-operation and Vault writer locks, but it deletes and
fsyncs all live source replay state before it attempts to write the replacement segment/HEAD
(`src/aptuni/vault/store.py:389-405`). Any segment write, fsync, rename or process failure after
`_clear_source_state()` leaves the original canonical HEAD live with its replay state already gone.

Reproduction: create a live Vault with a source-state marker, copy a valid backup, inject the
existing `after_segment_tmp` crash hook, and call restore. The result was:

```text
restore_error injected_after_source_cleanup
head_unchanged True
source_state_survives False
```

This is the opposite partial outcome from Review 29 B7, not atomic restore. Source state is
rebuildable only under source-specific identity/reconciliation rules; losing it can change delta
identity or replay behavior, and the caller sees a failed restore after a durable managed-state
mutation. Stage the replacement and a durable restore journal before invalidating live replay state,
then make recovery finish one unambiguous generation switch and cleanup. Fault-inject every boundary
from source-state staging through HEAD publication and journal completion.

### R3 — The terminal preview still does not meet ADR-0013's untrusted-name/data-class contract

The remediation correctly adds external provider and destination, but not the required data class
(`src/aptuni/application/privacy.py:260-276,305-328`). The human preview prints the user-controlled
source destination directly, without delimiters, escaping or confusable/control-character marking
(`src/aptuni/cli/main.py:620-635`). A folder name can contain newlines, terminal controls, quotes,
backticks or shell-looking text and visually forge adjacent preview lines. The persisted receipt
flattens these fields into one ambiguous `details` string (`privacy.py:505-517`), while the normal
human receipt output omits `details` entirely (`cli/main.py:596-603`).

ADR-0013 item 2 makes these properties normative for the confirmation surface: the full preview must
show provider, destination and data class, and untrusted names must be delimited with confusables
flagged. Render destinations through a bounded escaped/delimited representation, add the data class
(for example, the granted modules/scopes and minimized context class) to the digest-bound structured
copy description, and preserve/print structured external-action details in the receipt. Add terminal
tests with newline, ANSI/control, quote, backtick, semicolon and Unicode-confusable source paths.

## Non-blocking notes

- **Lock ordering is consistent.** Source sync uses `source_operations -> per-source -> Vault
  writer`; purge uses `privacy -> source_operations -> Vault writer`; restore uses
  `source_operations -> Vault writer`. No reverse acquisition was found, and the focused concurrency
  tests complete. Keep this order documented beside `source_operations_lock`.
- `_owned_child()` closes the original pre-existing-alias exploit, but its check and later pathname
  deletion are not descriptor-relative and remain susceptible to a component-swap TOCTOU
  (`privacy.py:234-248,367-375`). Under ADR-0013 an already unconfined same-user process is outside
  core enforcement, so this is not a current blocker; use `dir_fd`/no-follow operations before
  broadening the threat claim.
- Strict stored-preview/result schema validation remains desirable. `_preview_from_dict()` still
  coerces several values, and intent result values are accepted without an enum/schema check. This
  fails closed in ordinary CLI paths but makes corrupted retry state harder to diagnose safely.
- The privacy root and inventory readers still use ordinary pathname traversal. A pre-existing
  `state/privacy` alias should be rejected consistently with adapter/source aliases even though the
  current generated action filenames make arbitrary deletion unlikely.

## Overall judgment

The remediation materially improves deletion safety: it closes the demonstrated pre-existing
symlink escape, prevents post-intent source sync, restores CLI retry, reaps terminal intents, and
validates HEAD segment names. The slice is not ready to checkpoint because a post-preview projection
can retain purged content under a complete receipt, restore still has an unrecoverable partial-state
window, and the terminal preview remains below the accepted ADR's explicit untrusted-name/data-class
contract.

**Verdict:** **BLOCK**
