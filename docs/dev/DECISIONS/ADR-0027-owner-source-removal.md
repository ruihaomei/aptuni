# ADR-0027: Let the owner remove an approved source by revoking it and retracting its evidence

- **Status:** Accepted
- **Date:** 2026-09-29
- **Deciders:** maintainer (chose "deactivate + retract evidence", Beta Day 0) · implementing agent · independent reviewer
- **Builds on:** ADR-0010 (privacy purge), ADR-0011/0018 (review events), ADR-0013 item 2 (owner-facing rendering)
- **Needs maintainer confirmation:** no — the maintainer chose these semantics on 2026-09-29, twice

## Context

On Beta Day 0 User #1 approved sixteen sources in one setup. One repository could not be read,
and the owner then wanted to keep only the public repositories. There was no way to stop using an
approved source: `aptuni source` could only add and list. The only removal path was ADR-0010's
irreversible privacy purge, reachable only as `aptuni privacy purge preview RECORD_ID`, which
deletes the source and all of its evidence and history. The maintainer chose a softer, reversible
operation: stop using the source and withdraw what it contributed, keeping history.

## Decision drivers

- The owner can stop Aptuni using a source without deleting history (deletion stays explicit).
- Nothing the removed source contributed stays visible to agents.
- No change that the published 0.2.0b3 cannot read: Beta users may run mixed versions.

## Options considered

### Option A — new `source_retirement` record type
**+** explicit. **−** needs a new id prefix and record type; older builds reject the Vault.

### Option B — `schema_version: 2` of `source_config` with a status field
**−** a mutable-looking status on an append-only record; older builds reject the Vault.

### Option C — a `review_event` with `decision: "revoke"` targeting the `source_config`
Review events already target candidates, memories and facts; `revoke` and schema version 1 exist.
**+** readable by every released build; one append-only record; reuses the owner-decision audit
trail. **−** consumers of review events must not mistake a source revocation for a memory decision.

## Decision

We choose **Option C**.

- `aptuni source remove SOURCE_ID` shows what will happen (the source, how many current evidence
  items it contributed) and applies only after the owner types `APPLY` at the prompt. The preview is
  bound to a digest of the source id and the exact current evidence ids; if a sync changes them
  before APPLY, nothing is written (`confirmation_stale`).
- One Vault commit writes a `review_event` (`schema_version: 1`, `decision: "revoke"`,
  `actor: "user_cli"`, `rationale_code: "source_removed"`, `target_id` = the source id) and one
  retraction `evidence` record (`change_kind: "retraction"`, superseding the current item) for every
  current, non-retracted evidence item of that source. History is kept; ADR-0010 purge remains the
  way to delete it.
- A removed source is no longer listed by `aptuni source list` or used by setup, cannot be synced
  (`source_removed`), and cannot be removed twice. Approving the same location again creates a new
  source with a new id.
- **Invariants** (checked by `RecordSet.validate`): a review event that targets a `source_config`
  must be exactly the `revoke` / `user_cli` / `source_removed` shape; there is at most one per source;
  and every current evidence item of a removed source is a retraction marker.
- **Defense in depth:** `exposable()` never returns evidence whose source is revoked.
- **Other consumers:** the evaluation count of owner review decisions excludes source removals;
  a privacy purge of a source also purges its removal event.

## Consequences

- **Positive:** reversible, auditable removal that every released build can read.
- **Negative / risks:** review-event consumers written later must filter by target type; the
  invariant and the evaluation filter cover the ones that exist today.
- **Follow-ups:** show removed sources in `source list --all` if owners ask for it.

## Verification

`tests/integration/test_source_removal.py`: preview creates nothing; APPLY writes the event and the
retractions and hides everything from agents; a stale preview is refused; sync and a second removal
are refused; setup re-approves a removed location as a new source; purge still works; the Vault
passes `doctor`; invariants reject a malformed source revocation and a surviving evidence item.
