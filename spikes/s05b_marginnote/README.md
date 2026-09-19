# S05B — MarginNote identity on real MarginNote 4 history

- **Date:** 2026-09-19
- **Question (KI-020):** Is the OPML reconciler safe and usable on real MarginNote notebooks, where no
  exported node ID is trusted?
- **Data:** the maintainer's own MarginNote 4 backup store, read-only and authorized. Only aggregate
  counts leave memory; `results/` contains counts and no note content.
- **Run:** `PYTHONPATH=src .venv/bin/python spikes/s05b_marginnote/replay.py --json OUT`, about 12 s.

## Method

MarginNote 4 stores notebook backups in `BackupSnapshots_v4.sqlite`. Note objects there are
zlib-compressed JSON in `BackupStorage`. Every note carries its internal `noteid` (ground truth)
and `mindlinks`, an ordered list of child UUIDs. From these, the mind-map tree can be rebuilt.

**Snapshots are incremental.** Only 488 of 998 snapshots store every note. The others store just the
changed notes, while `note_count` holds the true total. An earlier analysis (Codex, 2026-09-19,
`temp/`) treated each snapshot as a full tree. That is why it reported 21,749 "removals"; they are
artifacts. The harness rebuilds each full state by overlaying deltas in order. A delta cannot say
which note was deleted, so a notebook's chain is evaluated only while the overlay size equals
`note_count`, and it stops at the first deletion it cannot resolve (24 of 108 chains).

Each rebuilt state is rendered as OPML. A node's text is its card title, or its excerpt when there
is no title. Children follow `mindlinks` order, and roots are sorted by note ID. States are fed
through the **production** `aptuni.sources.opml.scan_opml`, chained as repeated syncs would be.
No vendor attribute is trusted. The true ID travels as an untrusted attribute that the matcher never
reads, so each identity decision is scored against ground truth:

- **false link:** a subject continued across two different real notes;
- **false link, changed content:** one of those whose text differs. This is the safety metric,
  because only this case can attach one note's evidence history to another;
- **false split:** a real note got a new subject (silent add/remove churn);
- **review items:** ambiguous changes held for the user.

## Results (108 notebooks, 298 valid transitions, 131,902 rendered nodes)

| Metric | S05A matcher (baseline) | Adopted matcher (S05A + R1 + R3) |
|---|---:|---:|
| Correct links | 90,460 | 103,178 |
| **False links across different content** | **0** | **0** |
| False links, identical content (2,603 empty-text cards, 75 duplicate labels) | 0 | 2,678 |
| Review items | 25,534 (≈86 per sync) | 10,048 (≈34 per sync) |
| of which indistinguishable duplicates | 25,470 | 9,922 |
| of which same-position text change | 64 | 126 |
| Removals of notes that still exist | 10 | 9 |
| Silent splits (note re-added under a new subject) | 23 | 28 |

Raw counts: `results/replay-summary-s05a-baseline.json` and `results/replay-summary.json`.

## Findings

1. **No cross-content link on real data.** Neither matcher continued a subject across different
   content in 298 real transitions. No exported vendor ID is needed, and none is trusted.
2. **Review burden is the blocker to shipping.** S05A's ≈86 review prompts per sync come almost
   entirely from indistinguishable duplicates (repeated labels, image-only cards).
3. **Adopted (ADR-0006 amendment 2026-09-19):**
   - **R1:** identical siblings keep identity when they stay in the same slot under the same parent
     (`parent_slot_content_match`). This cuts review items by 61% without new removals.
   - **R3:** a parent matched only by its children signature may not change both its own text and
     its parent (`weak_structural_match` review). It is a precaution: it never fired on this data.
4. **Rejected: resolving moved duplicates as add/remove (R2).** It cut review further, but
   proposed 5,886 removals of notes that still existed and reversed an accepted ADR-0006 rule.
   Review 22 blocked it, and it was withdrawn.

## Limits (what this does not prove)

Review 22 audited the harness. These limits apply:

- The history is thin where identity is hardest. It contains 14 real moves and 26 real in-place
  edits, no edit-plus-move cases, and no evaluated deletions. No link came from children matching.
- Root order is sorted by note ID, not canvas position. 99.4% of all 10,048 reviews sit at the top
  level, so the ≈34-per-sync figure is mostly a harness artifact, not a UX measure.
- The hidden truth attribute causes attribute-only modify operations, which inflates the no-op
  count.
- The OPML is rendered by this harness, not by MarginNote's exporter. The exporter's text choice
  and branch-export shape still need **one real OPML export** from the maintainer: a full notebook
  plus one focus-branch export of the same notebook.
- Chains stop at the first unresolvable deletion (24 of 108) and are not restarted at later full
  snapshots.

**Conclusion:** KI-020 stays open. The reconciler is safe on this history, but review burden and
real-export shape must be addressed before MarginNote sync ships.
