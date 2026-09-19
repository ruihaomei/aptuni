# S05A result — common source identity contract

**Result:** PASS (pending independent evidence review)

**Run date:** 2026-09-19

**Baseline:** CPython 3.13.3, standard library only, no network

**ADR impact:** supports ADR-0006 option B, with the contract refinements listed below. Keep the ADR
`Proposed` until the batched spike-evidence review.

## Question

Can one common SourceLocator/Snapshot/CandidateDelta/SourceConfig envelope represent the Folder,
MarginNote-OPML and GitHub identity families before v1 freezes, without changing common
invariants for each provider?

## Measured facts

`run_s05a.py` ran 72 tests and passed. Each acceptance criterion maps to named tests, and a missing or
failing mapped test fails the run (`spikes/s05a_sources/results/S05A-result.json`).

| Criterion (SPIKES.md) | Evidence |
|---|---|
| Identical replay is idempotent | `delta_id` is content-addressed. Replaying a scan gives a byte-identical delta for all three providers. The ledger ignores a duplicate `delta_id`. Replaying a whole history, including duplicate delivery, gives the same state digest. |
| Source identity fits versioned extensions | `folder.locator@1`, `marginnote.locator@1` and `github.locator@1` validate through one registry. Common invariants never read provider fields. An unknown extension version round-trips losslessly and forces review. |
| Unknown/ambiguous identity is reviewable | Duplicate-hash renames, indistinguishable OPML duplicates and same-position leaf edits become `ambiguous` + `needs_review`, with at least 2 candidates. A rename+edit is not silently linked. A different repository under one source is refused. Ambiguous items enter the review queue. |
| Disappearance never deletes facts | `remove` is only a `tombstone_proposal`. Partial coverage never produces removals: a Folder file-count bound, an OPML branch export, a truncated GitHub tree, or a sticky selection that drops a known item. When a delta arrives, the ledger withdraws evidence and marks dependent facts `needs_reevaluation`. It never deletes or rewrites facts. |
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
3. `delta_id` must be content-addressed over the canonical envelope. The ledger also needs
   `base_snapshot` == current head, otherwise the delta is rejected as stale. Together these give
   idempotent, ordered delivery.
4. Provider identity lives in `<provider>.locator@<version>` extensions, validated by a registry.
   An unknown version is preserved, not dropped, and gated to review.
5. The OPML manifest needs `parent_node_id`, `children_signature` and `sibling_index` besides
   `ancestor_path`. Move/modify is decided from final parent *identity*, not ancestor text,
   otherwise renaming a parent would look like moving its children.
6. GitHub Standard selection must be sticky. A known item that is merely unselected is a coverage
   gap, not a disappearance.

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
- `ledger.py` stands in for canonical intake. It proves the boundary (no fact mutation from
  deltas), not the storage design, which S01 covers.

## Reproduce

```sh
cd spikes/s05a_sources && /opt/homebrew/bin/python3.13 run_s05a.py
```
