# S05A result — common source identity contract

**Result:** PASS. Review round 3 (`S05A-review-round3.md`): APPROVE WITH NON-BLOCKING NOTES,
after rounds 1 and 2 blocked and were remediated test-first.

**Run date:** 2026-09-19

**Baseline:** CPython 3.13.3, standard library only, no network

**ADR impact:** supports ADR-0006 option B, with the contract refinements listed below. Keep the ADR
`Proposed` until the batched spike-evidence review.

## Question

Can one common SourceLocator/Snapshot/CandidateDelta/SourceConfig envelope represent the Folder,
MarginNote-OPML and GitHub identity families before v1 freezes, without changing common
invariants for each provider?

## Measured facts

`run_s05a.py` ran 95 tests and passed; 23 of them are regressions from the review rounds. Each
acceptance criterion maps to named tests, and a missing or failing mapped test fails the run (`spikes/s05a_sources/results/S05A-result.json`).

| Criterion (SPIKES.md) | Evidence |
|---|---|
| Identical replay is idempotent | `delta_id` is content-addressed. Replaying a scan gives a byte-identical delta for all three providers. Each delta carries a per-source `sequence`, and that sequence is part of `delta_id`, so every delivery gets a distinct id even when content goes A→B→A→B. The ledger treats a known `delta_id` as a duplicate, in or out of order, including a late redelivery after a content cycle. It applies a new delta only when its base is the current head and its sequence is the next one; a gap is rejected. Intake recomputes `delta_id`, so a mutated delta is rejected. Replaying a whole history, including in-order and late duplicate delivery, gives the same state digest. |
| Source identity fits versioned extensions | `folder.locator@1`, `marginnote.locator@1` and `github.locator@1` validate through one registry. Common invariants never read provider fields. Intake gates every operation through the registry: an unknown extension version round-trips losslessly and goes to review, and an invalid understood locator is rejected before any state changes. Candidates are allowed only on `ambiguous`, and each subject gets at most one operation per delta. |
| Unknown/ambiguous identity is reviewable | Duplicate-hash renames, indistinguishable OPML duplicates, same-position leaf edits, and any would-be move under partial coverage (Folder bound, truncated GitHub tree, OPML branch export) become `ambiguous` + `needs_review`, with at least 2 candidates. A single-child OPML signature is too weak to link parents. A rename+edit is not silently linked. A different repository under one source is refused. Ambiguous items enter the review queue. |
| Disappearance never deletes facts | `remove` is only a `tombstone_proposal`. Partial coverage never produces removals: a Folder file-count bound, an OPML branch export, a truncated GitHub tree, or a sticky selection that drops a known item. A sticky GitHub item renamed to an unselected path gets priority for a slot and becomes a `move`. Old items named as ambiguity candidates are carried forward `held`: never re-matched or tombstoned. A held Folder/GitHub item re-observed at its own key keeps its identity. If its bytes changed, that is a reviewable `modify` (`held_item_changed`), not a silent `add`. When a delta arrives, the ledger withdraws evidence and marks dependent facts `needs_reevaluation`. It never deletes or rewrites facts. |
| Authority conflicts and locators round-trip | The envelope, `SourceConfig` and `Resolution` round-trip through JSON. A sole configured primary supersedes only within its dimension. Absent or multiple primaries give parallel review, and 0.99 confidence does not override that. A policy-version change before commit forces review. |
| Truncation is explicit | A truncated tree gives coverage `partial` plus a `tree_truncated` note. Standard selection is bounded, deterministic under input shuffling, prioritized (README → manifests → source) and sticky. |

Per-provider identity behaviour exercised:

- **Folder:** an unchanged rescan is a no-op with a stable snapshot. An edit is `modify`. An exact
  unique-hash rename is a `move` with identity kept. Rename+edit becomes `remove`+`add`. Delete
  becomes a tombstone proposal. A parser upgrade re-parses unchanged bytes (`modify`,
  `parser_upgrade`). Symlinks and `.git` are never read.
- **MarginNote OPML:** hierarchy and unknown attributes are preserved. DTD/entities are rejected and
  node/depth limits enforced. Instruction-like text stays plain data. Vendor attributes are kept but
  untrusted by default: a re-export with changed `mnid` values keeps identity. A move keeps
  identity. A branch edit with an unchanged child signature is `modify`. A copied card is a plain
  `add`. A configured, trusted vendor ID survives a text edit.
- **GitHub Standard:** a new commit with identical blobs is a no-op. Edit → `modify`; same blob at
  a new path → `move`; delete → tombstone proposal. A repository rename keeps identity because
  `repository_id` is the anchor.

## Contract refinements discovered (ADR-0006 impact)

1. `Snapshot` needs an explicit `coverage` (`complete` | `partial`). Removal is only legal against
   complete coverage, and a partial snapshot carries unobserved items forward unchanged.
2. `ambiguous` needs at least 2 candidates. When a single old item might match, the new
   provisional ID is the second candidate ("same as old" vs "genuinely new").
3. Snapshot ids are content-addressed, so they repeat when content cycles. The envelope therefore
   needs a per-source monotonic `sequence`, and `delta_id` has to cover it so one id means one
   delivery. Intake de-duplicates by `delta_id`, requires `base_snapshot` == head plus the next
   `sequence`, and recomputes `delta_id` itself. Delivery rule: every delta, even an empty one, is
   delivered. Otherwise the provider must rebase on the ledger's head and sequence. A skipped
   delta makes later deltas stale; that is safe but blocks until the rescan.
   The envelope is now version 2, and a missing field is a `ContractError`.
4. Provider identity lives in `<provider>.locator@<version>` extensions, validated by a registry.
   An unknown version is preserved, not dropped, and gated to review.
5. The OPML manifest needs `parent_node_id`, `children_signature` and `sibling_index` besides
   `ancestor_path`. Move/modify is decided from final parent *identity*, not ancestor text,
   otherwise renaming a parent would look like moving its children.
6. GitHub Standard selection must be sticky. A known item that is merely unselected is a coverage
   gap, not a disappearance. A blob that vanished from a sticky path claims a slot first, but only
   when exactly one fresh path has that blob, so a common blob such as an empty file can't flood
   the budget.
7. `SnapshotItem` needs a `held` flag. Review-reserved old items must survive later scans, and
   under partial coverage an unobserved item is never a move source.
8. The registry gate belongs at canonical intake, not only in provider tests.

## Interpretation and limits

- These fixtures are synthetic. **Real MarginNote 4 export identity is still unverified**, and no
  vendor attribute is trusted until a maintainer-created export series (no-op, edit, move,
  duplicate, delete/recreate, branch export, app restart) shows it stable. That work belongs to the
  MarginNote S05B suite (KI-020).
- GitHub inputs are shaped like Trees API responses. Live pagination, redirects, rate limits and
  subtree traversal after truncation belong to GitHub S05B.
- Folder continuity across rename+edit is intentionally lost. The reviewable alternative (content
  similarity) is out of scope and must not be silent.
- Admission hardening (approved-root TOCTOU, parser/archive bombs beyond the OPML DTD ban, secret
  exclusion, deceptive metadata) stays with S05B for each provider, as plan 00 §6 already states.
- **Review resolution → manifest is not built.** Held items stay held, except when a Folder/GitHub
  item is re-observed at its own key. The resolution command that re-keys, releases or tombstones
  them is Foundation Slice 7 work (with the review UI).
- OPML child-signature linkage uses exact multisets of at least 2 children, not a similarity
  threshold. OPML held nodes are never auto-released, so repeated edits or reverts of one card add
  a held node and a review item each time. Held items grow without bound until the Slice 7 review
  loop exists.
- On an OPML branch export, demotion cascades: descendants of a demoted node are demoted too. One
  branch export after a legitimate subtree move can therefore split that subtree's identity (new
  provisional IDs, originals held) until review resolves it. Full exports keep it a single `move`.
- When a hold is released, any queued review item that names the held subject can go stale, for
  example when its provisional `after` subject is later tombstoned. The Slice 7 review loop must
  detect and close stale items.
- Behaviours to know: a content swap between two paths is two `modify` ops (path identity), and a
  vendor-attribute churn re-export emits `modify (attributes_changed)` on every node. That flags
  dependent facts for re-evaluation without changing identity.
- Review-gated operations take no effect before review. That includes `ambiguous` items and a
  `held_item_changed` modify: dependent facts stay `active` until the review decision, even though
  the evidence bytes changed. Slice 7 must decide whether a pending review also flags dependents.
- `Extension.fields` is a JSON-normalized copy, not a deep-frozen mapping. Integrity comes from
  intake recomputing `delta_id`.
- `ledger.py` stands in for canonical intake. It proves the boundary (no fact mutation from
  deltas), not the storage design, which S01 covers.

## Reproduce

```sh
cd spikes/s05a_sources && /opt/homebrew/bin/python3.13 run_s05a.py
```
