# Review 29 — M1 privacy inventory, purge, and restore

**Date:** 2026-09-20

**Reviewer:** independent privacy/security review agent (did not modify the implementation or tests)

**Scope:** the complete uncommitted diff relative to `0b0eabf`, including the untracked
`tests/integration/test_privacy_purge.py`. The review checked ADR-0010/0013 confirmation, journal,
receipt, deletion, restore and host-boundary requirements; Reviews 15/16/19; and the owning backlog
items.

**Validation:**

- `.tools/bin/uv run pytest tests/integration/test_privacy_purge.py
  tests/integration/test_privacy_inventory.py tests/integration/test_vault.py -q`: **25 passed**.
- Additional throwaway probes used `TemporaryDirectory`; no repository fixture or personal data was
  written. They reproduced every blocking finding below.

## Blocking findings

### B1 — Purge follows attacker- or corruption-controlled parent symlinks and can delete outside Aptuni

`_remove_owned()` checks only the final path and then calls `shutil.rmtree()`
(`src/aptuni/application/privacy.py:271-278`). The cleanup targets are constructed below potentially
replaceable parents such as `state/adapters` and `vault/sources`
(`src/aptuni/application/privacy.py:349-361`). If `state/adapters` is a symlink, then
`state/adapters/grants` is not itself a symlink and `rmtree()` follows the parent alias into an
arbitrary external directory.

Reproduction: initialize a temporary Vault, preview a one-Fact purge, create
`external/grants/do-not-delete`, make `state/adapters -> external`, then confirm. The result was:

```text
marker_exists False grants_dir_exists False result [('adapter_grants', 'deleted')]
```

This is a destructive path-confinement failure, not merely an out-of-band integrity limitation: an
adopted/pre-existing state directory can contain such an alias, and confirmation then deletes data
outside the reviewed scope. Resolve this with component-by-component, no-follow deletion rooted at
an already opened core-owned directory (or fail closed on any alias), and add regressions for parent
aliases under both `state/adapters` and `vault/sources`.

### B2 — A committed purge intent does not exclude source sync, leaving canonical source data behind

The intent becomes durable at `src/aptuni/application/privacy.py:321-323`, but confirmation does not
take the affected sources' `SourceSyncLock`. Source sync uses only that independent per-source lock
(`src/aptuni/application/source_commands.py:183-188`). On retry, an existing intent intentionally
skips the original Vault-sequence/epoch admission check (`src/aptuni/application/privacy.py:305-325`)
and purges only the record IDs frozen in the old preview.

Reproduction: preview deletion of source Evidence, call `_load_or_commit_intent()` to model a stop
immediately after durable intent commit, add a second source file and sync, then resume confirmation.
The purge returned `complete_managed_external_action_needed`, removed the SourceConfig and replay
state, but left the newly committed Evidence:

```text
before: SourceConfig + two Evidence records
after:  one Evidence record whose provenance.source_id names the deleted SourceConfig
doctor: ok
```

The owner therefore receives a complete receipt while managed source-derived personal content from
the affected source remains canonical and can still be exposed. Acquire all affected per-source
locks in a deterministic order before committing the intent and hold them through canonical purge
and replay-state cleanup, or introduce an equivalent tombstone/intent check in sync. Add a crash
test for `intent durable -> concurrent sync -> retry`.

### B3 — The confirmation is not an exact preview of the copies it deletes

The digest binds five generic prose effects (`src/aptuni/application/privacy.py:219-248`), but the
worker deletes entire adapter-grant, adapter-bundle, adapter-pending, memory-confirmation and
privacy-pending trees (`src/aptuni/application/privacy.py:349-362`). The preview does not enumerate
grant/action IDs, provider/operator/destination, locations, presence or counts, and it does not
mention deletion of memory confirmations or other privacy previews at all. These trees can also be
created concurrently because their writers do not share the privacy lock. The receipt later reports
only generic copy classes (`src/aptuni/application/privacy.py:380-394`), after deleting the grants
that held the only provider/destination metadata needed to tell the owner which external host copies
still require action.

This violates ADR-0010's exact-preview/per-copy-receipt requirement and ADR-0013 item 2's full
core-rendered scope/provider/destination preview. Snapshot exact managed copy identities and the
external-copy disclosure into the action digest; either delete only that set or explicitly preview
and serialize a whole-class revocation. Preserve enough content-free provider/destination metadata
in the receipt to keep later external-action guidance honest.

### B4 — The shipped CLI cannot resume an `incomplete_retryable` purge

The service's direct retry test passes, but the CLI always loads the pending preview before calling
the worker (`src/aptuni/cli/main.py:587-596`). Committing an intent removes that pending file
(`src/aptuni/application/privacy.py:321-323`), and cleanup also removes the whole pending directory
(`src/aptuni/application/privacy.py:361`).

With `SqliteProjection.delete` injected to fail once, the first CLI confirmation returned exit 2
and an `incomplete_retryable` receipt. Re-running the documented exact command, including the same
action ID and digest, failed with `privacy_action_not_found`; it never reached the durable intent.
This defeats ADR-0010's retryable partial-failure contract on the only supported approval surface.
Let CLI confirmation resolve a validated preview from pending state, committed intent, or receipt as
appropriate, and add a subprocess test for incomplete result followed by successful CLI retry.

### B5 — A crash after receipt publication can permanently block every later purge

The terminal receipt is durably replaced before the intent is unlinked
(`src/aptuni/application/privacy.py:415-421`), but the unlink is not followed by a parent-directory
fsync. More importantly, when a terminal receipt exists, retry returns immediately without removing
a surviving matching intent (`src/aptuni/application/privacy.py:402-405`). New actions treat every
other intent file as active and fail with `privacy_action_in_progress`
(`src/aptuni/application/privacy.py:305-313`).

Reproduction: preserve the committed intent bytes, complete the purge, recreate that intent to model
the receipt-written/intent-unlink-not-durable crash state, then retry the completed action. It
returned the terminal receipt but left the stale intent. A newly previewed purge was then rejected
with `privacy_action_in_progress` indefinitely. Recovery must validate and reap an intent already
covered by its terminal receipt, fsync intent-directory removals, and include this exact crash window
in the journal fault-injection matrix.

### B6 — Restore accepts committed segment paths outside the selected backup

`restore_from()` rejects symlinked control paths and final segment symlinks, but never validates a
HEAD segment name as a protocol basename (`src/aptuni/vault/store.py:354-370`). `_read_segments()`
then reads `records_dir / segment["name"]` directly (`src/aptuni/vault/store.py:202-215`).

Reproduction: copy a valid backup, move its valid segment files beside the backup, and replace each
HEAD name with `../../external-N.jsonl` while retaining the recorded digest, count and chain. Restore
accepted the backup, imported those outside files, and `doctor` returned healthy. A restore artifact
can therefore make Aptuni read/import data outside the user-selected backup boundary. Require every
segment name to match `SEGMENT_RE`, contain no separators, resolve beneath `backup/records`, and be
opened no-follow relative to that directory. Test traversal, intermediate symlinks and non-regular
files.

### B7 — Restore publishes the new Vault before unjournaled source-state cleanup

The live HEAD is atomically replaced and the writer lock released at
`src/aptuni/vault/store.py:376-388`; only afterward does restore delete source replay state, without
a restore journal or retry receipt (`src/aptuni/vault/store.py:389-394`). A process stop or cleanup
error therefore leaves the restored canonical generation committed while old replay manifests and
pending deltas remain. The caller can also observe an exception as though restore failed even though
the canonical restore already succeeded. A later sync can apply deltas based on state from the
pre-restore generation.

That is not the atomic restore required by the ADR-0010/0013 amendments. Journal the full restore
intent and make source-state invalidation recoverable/idempotent before reporting success (without
ever deleting the live Vault first). Add fault injection between HEAD publication and every cleanup,
then prove reopen/resume reaches one unambiguous terminal outcome.

## Non-blocking warnings and test gaps

- The new durable `privacy/intents` state is omitted from the owner inventory, which lists pending
  actions and receipts only (`src/aptuni/application/privacy.py:513-516`). Add it with a bounded
  retention/retry control; it is the most important state when a purge is incomplete.
- `_preview_from_dict()` coerces booleans/strings/containers instead of strictly validating stored
  schema types, and committed `intent["results"]` values are trusted without schema validation
  (`src/aptuni/application/privacy.py:89-118,306-309,409-414`). Direct same-user tampering is outside
  the core boundary, but accidental corruption should fail closed rather than skip an effect or
  manufacture a complete receipt.
- Current MCP handlers do not reference the purge methods, which is correct. Add the ADR-0013
  call-graph/schema regression proving no MCP, hook, worker or non-CLI input exposes action IDs,
  digests, nonces or approval fields; the implementation currently relies on inspection only.
- Add format-1 purge and restore tests, projection rebuild-after-purge/restore tests, and per-copy
  fault injection. The present focused suite covers the happy path, one projection failure and Vault
  publication, but not the required cleanup crash matrix.

## Overall judgment

The chain-base migration, supersession expansion, ledger reapplication, content-free error shape and
basic idempotent service worker are directionally sound, and all focused tests pass. The current
slice cannot checkpoint, however: confirmed deletion can escape owned paths, a durable intent can
leave affected canonical Evidence behind, the CLI cannot perform the promised retry, journal
recovery can deadlock future purges, and restore is neither path-confined nor operation-atomic.

**Verdict:** **BLOCK**
