# Milestone 2 S10 Mem0 admission remediation

- **Responds to:** `51-m2-s10-mem0-admission-review.md`

This remediation answers the three blockers in Review 51 without widening the production contract.

## B1 — Fresh rebuild and exact equality

- Kept restart and fresh rebuild as separate phases and evidence fields.
- After purging the first provider root, the harness creates a second fresh root and replays only the
  canonical current records with inference disabled.
- Equality now covers active text, `aptuni_canonical_id`, scope and schema version, rejects duplicate
  IDs and malformed rows, and proves the tombstoned and corrected-old markers are absent after the
  fresh rebuild.
- Added a corruption regression that preserves IDs but changes content and must fail.

## B2 — Network boundary

- Extended the guard across bind, connect, connect_ex, connected send/sendall, datagram sendto and
  sendmsg; non-loopback datagram regressions now fail closed.
- The evidence process refuses the Mem0 admission run if any `mem0` module was loaded before the
  guard. The pinned provider and its Qdrant/PostHog dependencies are imported lazily inside the
  guarded phase, so they cannot reuse a provider-created pre-guard socket.
- The artifact records every guarded path and whether provider code was preloaded. It reports
  attempts observed by this boundary, not a claim about unrelated host processes.

## B3 — Per-record retention and deletion

- Added marker-digest inventories by sanitized storage class after correction, after the individual
  tombstone, and after fresh rebuild.
- Mem0 2.0.20 leaves the tombstoned marker in embedded Qdrant bytes and history; the result therefore
  records `record_delete_removes_all_copies=false` and `required_delete_strategy=whole_store_rebuild`.
- Whole-store close/remove plus canonical rebuild removes the tombstoned and corrected-old markers,
  restores the current active projection exactly, and leaves canonical bytes unchanged.
- The README now forbids a future adapter from claiming single-record deletion from `Memory.delete()`.

## Additional review notes

- Regenerated both checked-in artifacts from the final harness.
- Added Python and hash-locked requirements-lock digests to each result.
- The remaining provider-specific add/delete failure-injection matrix and the pinned Qdrant
  temporary in-memory SQLite warning are recorded in `BACKLOG.md` for the production adapter slice.

## Verification

- Standard-library suite: 13 passed; 2 isolated-runtime tests skipped honestly.
- Hash-locked Mem0 2.0.20 suite: 15 passed.
- Real artifact verdict remains `REJECT_RAW_RETENTION`; the safe projection boundary requires
  `infer=False` and whole-store rebuild for deletion.

**Verdict:** **READY FOR FOCUSED REREVIEW**
