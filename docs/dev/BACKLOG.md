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
| Purging a deterministic-ID source Evidence makes later syncs of that source fail with `invariant_violation` | Review 19 N3 | M1 privacy/restore slice |
| Tests for bad locator values, `records/` and state-directory permissions, and revoking a memory candidate | Review 19 N4 | Next Vault slice |
| Manifest schema: strict typing (`contract_version = true` coerces), duplicate egress/recipe entries, file name must equal `id`, orphan message keys, `suggested_sources` vocabulary | Review 20 N3 | Plugin activation slice |
| `minimize_cloud` behaves like `quality`; give it a real budget/module difference or merge the answers | Review 20 N8 | Guided-setup apply slice |
| A plan whose only named source is unshipped (e.g. MarginNote) should suggest a Folder source over an export | Review 20 N9 | Guided-setup apply slice |
| Show configured GitHub Enterprise origins in the preview network list | Review 20 N10 | Guided-setup apply slice |
| Bind the apply confirmation digest to catalog/schema version and the answers | Review 20 N11 | Guided-setup apply slice |
| i18n polish: localized `recipe show` unknown-id error, CJK list separator `、`, CJK column widths, `--lang fr` notice, Claude Desktop file-access wording, retention heading vs provider-managed data | Review 20 N7, Review 21 | i18n pass |
| R3-demoted parent's children become moves under the parent's new generated ID | Review 22/23 | MarginNote ingest slice |
| Replay harness: hidden truth attribute inflates modify/no-op counts; restart stopped chains at later full snapshots; order roots by canvas position | Review 22/23 | MarginNote ingest slice |
| Collision re-check for `aptuni` on PyPI/npm/GitHub before first publish | Review 15 F9 | Release |
