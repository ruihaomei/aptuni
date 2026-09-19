# Backlog

Non-blocking improvements from reviews and self-review. Each item records where it came from.
Pick an item up when its owning slice starts; do not open a review round for these alone.

| Item | Source | Owning slice |
|---|---|---|
| Atomic restore that never deletes the live Vault first and never re-baselines the chain | Review 15 F2; ADR-0010/0013 amendments | M1 privacy/restore slice |
| Out-of-band-edit path: quarantine and diff a hash mismatch instead of a read refusal | S01 F2; ADR-0013 item 5 | M1 Vault hardening |
| Segment compaction (chain-preserving rewrite) | S01 F1 | M1 Vault hardening |
| ADR-0001 untested items: same-valid-time conflict, out-of-order observation, export/import round-trip | Review 15 F4 | M1 ingestion + export slices |
| Plugin approval-to-import atomicity; files not listed in RECORD | Review 15 F5 (S02) | Plugin activation slice |
| `spikes/s03_fts/frozen/thresholds.json` says "24k-document" (actual 25,000); the file is hash-frozen, so fix only in a new versioned protocol | Review 15 F6 | none (evidence stays frozen) |
| Re-run S01 in a fresh pinned venv to refresh its recorded run | Review 15 F1 | optional |
| OPML/Folder held-item review loop, stale review items, held growth | S05A rounds 2–3 | Review workflow slice |
| Pending-review ops may also flag dependent facts | S05A round 3 note 2 | Review workflow slice |
| Preserve verifiable chain semantics after a privacy purge instead of disabling the chain check once any ledger entry exists | Review 16 F6 | M1 privacy/restore slice |
| Purging a superseding correction/retraction must not silently reactivate the older record | Review 16 F7 | M1 privacy/restore slice |
| Torn deletion-ledger tail followed by a purge glues entries together (purged ID can return, or later opens fail) | Review 19 N1 | Next Vault slice (scheduled first) |
| Map remaining raw exceptions (malformed config/HEAD, schema_version 2 in doctor, unreadable records dir, init on a file, stray `.HEAD.*.tmp` directory, partial multi-ID ledger entry) to stable CLI errors | Review 19 N2 | Next Vault slice |
| Purging a deterministic-ID source Evidence makes later syncs of that source fail with `invariant_violation` | Review 19 N3 | M1 privacy/restore slice |
| Tests for bad locator values, `records/` and state-directory permissions, and revoking a memory candidate | Review 19 N4 | Next Vault slice |
| Collision re-check for `aptuni` on PyPI/npm/GitHub before first publish | Review 15 F9 | Release |
