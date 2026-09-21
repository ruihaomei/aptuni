# Milestone 2 S10 Mem0 admission review

**Reviewer:** independent Codex review of the uncommitted S10 admission slice

## Scope

Reviewed the accepted S10 plan, provider-neutral harness, Mem0 2.0.20 driver, synthetic fixture,
focused tests, dependency lock, README decision, and both checked-in result artifacts. The review
focused on correctness, privacy/network confinement, deletion semantics, evidence honesty, and the
boundary implied for a future production adapter.

## Blocking findings

### 1. The required fresh rebuild is not exercised, and projection equality does not verify content

The admission plan makes a fresh rebuild from canonical input a mandatory gate
(`docs/dev/plans/08-m2-s10-mem0-admission-tdd.md:35-36,63-65`). The harness instead projects once,
reopens the same provider root through `restart()`, and enumerates the already-persisted projection
(`spikes/s10_mem0/s10/harness.py:370-376`; `spikes/s10_mem0/s10/mem0_driver.py:150-154`). It never
purges the first provider, initializes a fresh provider root, and replays the canonical fixture.

In addition, `_assert_projection` compares only the set of `aptuni_canonical_id` metadata values.
A provider that returns the right IDs with corrupted memory text, scope, or schema metadata still
passes, and the search check requires only one non-empty result. The result artifact truthfully
records `restart_projection_matches`, but that cannot support the plan's rebuild admission claim.

**Required fix:** add an explicit fresh-root rebuild phase after purge (or in a second disposable
root), replay only the canonical fixture with inference disabled, and assert exact active text plus
required metadata for every active canonical ID and absence of the tombstoned ID. Keep restart and
rebuild as separate result fields, and digest the canonical tree around the rebuild phase.

### 2. The network guard cannot substantiate the recorded zero-outbound-attempt claim

`NetworkGuard` intercepts only `connect`, `connect_ex`, and `bind`
(`spikes/s10_mem0/s10/harness.py:92-118`). A non-loopback datagram can leave via `sendto`/`sendmsg`
without incrementing `attempts`, and name resolution or a socket object captured before the monkey
patch is also outside the measurement. Nevertheless, the admission result reports
`network_attempts: 0`, and the plan treats zero outbound attempts as a mandatory privacy gate.

**Required fix:** make outbound denial cover all socket transmission paths used by the isolated
process (at minimum `sendto`/`sendmsg` with non-loopback regression tests), and run the provider in
a boundary that cannot reuse pre-guard sockets. The evidence should distinguish blocked attempts
from observed successful traffic; do not interpret the current counter as proof of zero outbound
activity.

### 3. Per-record deletion is masked by whole-root purge, so the adapter-facing deletion boundary is unresolved

The harness tombstones one record, but before purge it only records an aggregate count across all
markers. The Mem0 artifact reports nine marker copies before reset
(`spikes/s10_mem0/results/S10-mem0-2.0.20-result.json:11-12`) and does not classify which copies are
the corrected or tombstoned values or where they remain. It then deletes the entire provider root
and proves only that the root-wide purge removed all bytes (`spikes/s10_mem0/s10/harness.py:379-400`).
This does not establish whether `Memory.delete()` removes a single tombstoned memory from Mem0
history or other managed storage. The plan requires classified retention evidence and deletion that
does not claim success when managed copies remain.

**Required fix:** inventory by marker digest and sanitized storage class after correction and after
the individual tombstone operation, before root purge. Either prove all copies required by Aptuni's
per-record deletion contract are removed, or explicitly reject/condition the projection adapter on
a documented whole-store purge limitation. The future adapter must not inherit an ambiguous
single-item deletion promise.

## Warnings / non-blocking notes

- The checked-in fixture result is stale relative to the current harness. A fresh fixture run changes
  `export.missing_fields` from `revision_history` / `provider_native_ids` to
  `canonical_revision_history` / `embedding_rebuild_instructions`. Regenerate and review both
  evidence artifacts from the final code before checkpointing.
- Failure injection covers the fixture driver's project/reset paths, but not a failed Mem0 add and
  failed Mem0 delete as specified by the plan. Add provider-level failure tests and assert bounded,
  sanitized failure results plus cleanup; currently exceptions produce no structured result.
- The stored result exposes counts but not the promised sanitized storage classifications, exact
  runtime version, or lock-file digest. Including these makes the admission result independently
  traceable without exposing marker text.

## Verification

- `PYTHONPATH=spikes/s10_mem0 /opt/homebrew/bin/python3.13 -m unittest discover -s spikes/s10_mem0/tests -v`
  passed 12 runnable tests; the two Mem0-specific tests skipped because Mem0 is intentionally not
  installed in the product runtime.
- A fresh fixture result completed successfully but differed from the checked-in fixture result in
  the two `export.missing_fields` values described above.
- The hash-pinned lock includes `mem0ai==2.0.20` and `qdrant-client==1.19.1`; no product dependency
  change was observed in this slice.

## Overall judgment

The raw-retention rejection is appropriately conservative, the disposable-root purge is useful
evidence, and the public-export limitation is stated honestly. However, the current slice does not
yet meet its own mandatory rebuild, network-confinement, or deletion-evidence gates, so it cannot
admit Mem0 for a production projection adapter.

**Verdict:** **BLOCK**
