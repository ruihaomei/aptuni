# Milestone 2 S10 Mem0 admission focused re-review

**Reviewer:** independent Codex re-review of Review 51 remediation

## Scope

Re-reviewed the three Review 51 blockers against the remediated harness, Mem0 driver, focused
tests, README boundary, remediation note, hash-locked runtime, and freshly reproduced fixture and
Mem0 result artifacts. This review does not reopen the already-conservative rejection of Mem0
interaction inference.

## Blocking findings

None.

## Review 51 blocker disposition

### B1 — Fresh rebuild and exact equality: closed

The harness now keeps restart and rebuild distinct. After closing and removing the original
provider root, it initializes a separate rebuild root and replays the canonical records directly
(`spikes/s10_mem0/s10/harness.py:487-507`). The replay therefore writes only current active values;
a tombstone with no provider ID remains absent.

`_assert_projection` now rejects malformed or duplicate identities and compares exact memory text,
canonical ID, scope, and schema version. The harness separately rejects corrected-old and
tombstoned markers after rebuilding and requires the current corrected marker. The corruption
regression demonstrates that preserving IDs while changing content fails. The fresh Mem0 artifact
records both `restart_projection_matches=true` and `rebuild_projection_matches=true`, and reproduced
byte-for-byte in this review.

### B2 — Network-boundary evidence: closed for the stated admission scope

The guard now covers non-loopback name resolution, bind, connect, connect_ex, connected
send/sendall, datagram sendto, and addressed sendmsg paths
(`spikes/s10_mem0/s10/harness.py:98-164`). Focused regressions exercise DNS, TCP connect, and UDP
sendto/sendmsg denial. The admission run rejects preloaded `mem0`, `qdrant_client`, or `posthog`
modules and imports the provider and its exercised dependencies only during the guarded phase.

The result correctly presents `network_attempts` as observations from this process boundary and
records both the guarded paths and `provider_preloaded_before_network_guard=false`. The README no
longer overstates that evidence as host-wide network isolation. Within this bounded, fresh-process
spike, the zero-attempt result is supported.

### B3 — Classified deletion evidence and required strategy: closed

Marker digests are now inventoried by sanitized storage class after correction, after the
single-record tombstone, and after fresh rebuild. The real Mem0 artifact exposes the adverse result
instead of claiming record deletion: the tombstoned marker remains once in embedded Qdrant bytes
and twice in history, so `record_delete_removes_all_copies=false` and
`required_delete_strategy=whole_store_rebuild`.

After whole-store removal and canonical replay, both the tombstoned and corrected-old markers are
absent while the exact current projection is restored. The README makes this a hard adapter
boundary: `Memory.delete()` cannot satisfy Aptuni record-level privacy deletion, and an adapter must
close/remove the whole projection and rebuild it from canonical active records. This is an honest,
actionable limitation rather than an unsupported deletion guarantee.

## Non-blocking notes

- `run_s10.py` supplies a newly created temporary parent, so the sibling rebuild root is fresh in
  the evidence run. A future reusable harness hardening could explicitly reject an already-existing
  rebuild root before initialization.
- The network guard is application-level evidence, not an OS network sandbox or a proof about
  unrelated host processes. The current README/result wording is sufficiently scoped; preserve
  that wording in future adapter documentation.
- Provider-specific failed add/delete/rebuild injection and the pinned Qdrant SQLite lifecycle
  warning are appropriately retained in `docs/dev/BACKLOG.md` for the production adapter slice.

## Verification

- Isolated Mem0 runtime at `/tmp/aptuni-s10-runtime.gmDDO3`: all 15 focused tests passed. The known
  Qdrant temporary SQLite `ResourceWarning` appeared once and matches the documented upstream
  limitation.
- A fresh `--driver mem0` run completed with `REJECT_RAW_RETENTION`; its JSON was byte-identical to
  `spikes/s10_mem0/results/S10-mem0-2.0.20-result.json`.
- A fresh standard-library fixture run was byte-identical to
  `spikes/s10_mem0/results/S10-fixture-result.json`.
- The recorded requirements lock digest matches the current lock:
  `237dd322f395826dfe31ccaa0b88cd40d6e60715a5ac7544d62f483f675991a8`.

## Overall judgment

All three Review 51 blockers are resolved. The evidence supports only the deliberately narrow
admission recorded by the slice: Mem0 2.0.20 may serve as a disposable `infer=False` projection,
raw-interaction inference remains rejected, and privacy deletion requires whole-store removal plus
canonical rebuild. No production adapter may weaken those conditions.

**Verdict:** **APPROVE WITH NON-BLOCKING NOTES**
