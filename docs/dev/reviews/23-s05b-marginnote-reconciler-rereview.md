# Review 23 — S05B MarginNote OPML reconciler focused re-review

**Date:** 2026-09-19

**Reviewer:** independent Claude subagent (did not write the code under review)

**Scope:** a focused re-check of Review 22 B1 against
`22-s05b-marginnote-reconciler-remediation.md`. It covers the uncommitted working tree on `main`
(base `e3dbd2e`):
- `src/aptuni/sources/opml.py`
- `tests/unit/sources/test_opml_real_history.py`
- the ADR-0006 amendment "2026-09-19 — S05B real-history refinements"
- `spikes/s05b_marginnote/{README.md,replay.py,results/*.json}`
- the related `docs/research/` edits, reviewed for consistency only

**Privacy:** the harness and the count-only scorers ran read-only on the maintainer's authorized
MarginNote 4 store. This report contains aggregate numbers only. No note text or IDs were printed,
copied or quoted.

## Method

- Read the remediation note, the full `git diff HEAD` for `opml.py` and ADR-0006, the rewritten
  README, and the new test file.
- Re-ran the Review 22 shim, which runs the S05A spike `test_opml.py` unchanged against production.
- Regenerated both replay summaries and compared them with the committed JSON.
- Re-ran the Review 22 count-only scorers (`temp/review22/extended_score.py`,
  `review_breakdown.py`, `move_audit.py`).
- New synthetic fixtures and a 3,000-seed fuzz compared against the HEAD (S05A) reconciler:
  `temp/review22/test_review23_recheck.py`. Extra removes were audited with
  `temp/review22/remove_audit.py`.
- Ran `.tools/bin/uv run pytest`, `ruff check .` and `mypy src`.

## Checklist

| # | Check | Result | Evidence |
|---|---|---|---|
| 1 | B1: R2 withdrawn in code | PASS | `opml.py`: the `duplicate_content` branch is restored, with the same candidate set as S05A. The only change is that R3-demoted subjects are excluded too, as partial demotions already were. `_edited_in_place` is now logically identical to the S05A slot condition: no content filter and no empty-text exemption. `EMPTY_HASH` is gone. |
| 2 | S05A shim test passes against production | PASS | `temp/review22/shim/test_s05a_opml_on_production.py`: 16 passed, 0 failed. That includes `test_indistinguishable_duplicate_moves_are_ambiguous`. |
| 3 | Duplicate moves reviewed with no `remove`, in full and branch mode | PASS | Production test `test_indistinguishable_duplicates_that_move_still_go_to_review`. Fixture `test_duplicate_move_is_ambiguous_without_remove_full_and_branch` covers both scopes and a rescan. The edit-to-empty case is reviewed again (`test_edit_to_empty_is_reviewed_again`). |
| 4 | No live-note removals beyond baseline (real data) | PASS | The regenerated summaries match the committed `results/*.json` counts exactly for both matchers. `false_remove` is 10 (S05A) and 9 (now); `op_remove` is 10 and 9; `false_split` is 23 and 28. |
| 5 | Real in-place edits not lost vs S05A | PASS | 26 real in-place edits in the history. S05A reviewed 3. Now 15 are reviewed, 13 of them with the true note among the candidates. None that S05A reviewed is silent now. |
| 6 | Cross-content safety | PASS | Real data: `false_link_changed_content` = 0. Fuzz, 3,000 seeds with full and branch scans: every changed-content link is `children_signature_match`/`vendor_id_match`, and none is a move (R3). Branch scans never emit `remove` or `move`. Rescans are idempotent. Ambiguous candidates are held. The delta contract never raised. |
| 7 | Removes relative to S05A (synthetic) | PASS, with a note | In 239 of 3,000 seeds, the current matcher emits more `remove` than S05A (2,151 vs 1,954 in total). Each case is one of several identical siblings being deleted. R1 keeps the slot-matching one, and the other gets a tombstone proposal where S05A asked for review. `remove_audit.py`: removes that exceed the content-multiplicity drop are 4 now vs 4 at S05A, so no new live-note removals. See N2. |
| 8 | ADR amendment matches the code | PASS, with a note | R1 (`parent_slot_content_match`, identical text only), R3 (`weak_structural_match`), the retained duplicate review and KI-020 staying open are all stated correctly. It omits the R1 consequence in row 7 (N2). |
| 9 | README does not overclaim | PASS, with a note | The table figures match the JSON. 10,048/298 ≈ 34 per sync, and 25,534 → 10,048 is a 61% cut. The limits list my figures (14 moves, 26 edits, 0 edit-plus-move, no evaluated deletions, no signature links, R3 never fired). It states that KI-020 stays open. See N3 for one understatement. |
| 10 | Results JSON contains no content | PASS | It contains only fixed metric keys, the parser tuple, a date and numbers. |
| 11 | Existing tests kept | PASS | No existing test file was modified. The Review 22 R2 tests were replaced by the duplicate-review test. |
| 12 | `uv run pytest` | PASS | 268 passed, 47 subtests passed |
| 13 | `uv run ruff check .` | PASS | "All checks passed!" |
| 14 | `uv run mypy src` | PASS | "no issues found in 47 source files" |

## Blocking findings

None. B1 is resolved: R2 is withdrawn, the S05A duplicate contract is restored and covered by a
production test, the ADR amendment records R1 and R3, and real-data removals of live notes are at
or below the S05A baseline.

## Non-blocking notes (to `docs/dev/BACKLOG.md`)

- **N1 — Stale research memory.**
  `docs/research/upstream/source-identities-and-deltas.md` (new "2026-09-19 MarginNote S05B"
  section) still says "Refinements R1–R3 cut this to about 6.7, all genuine in-place edits." That
  describes the withdrawn R2 state and was never true, since precision was 2 of 2,003. It now
  contradicts the ADR amendment and the README. Replace it with R1 + R3, about 34 per sync, mostly
  top-level harness artifacts, and R2 rejected. Agents consult this file before re-researching, so
  fix it before the next slice.
- **N2 — R1 also changes the outcome when one identical sibling is deleted.** S05A asked for review.
  Now the sibling in the matching slot keeps its identity and the other gets a tombstone proposal.
  Content is identical, the number of removes equals the actual drop, and real data shows no
  increase (9 vs 10). Still, the ADR amendment should say so in one sentence, so the rule is not
  read as "only no-op stability."
- **N3 — The residual review count is almost entirely top-level.** 9,983 of the 10,048 reviews
  (99.4%), not only the same-position reviews, are at the top level, where the harness sorts roots
  by note ID. The README says "most same-position reviews" are top-level. It should say the
  ≈34-per-sync figure is itself dominated by this artifact. Precision: duplicate reviews list the
  true note in 6,570 of 9,922 cases; same-position reviews in 13 of 126.
- **N4 — Carried over from Review 22 N4, N6 and N7.** Children of an R3-demoted parent are emitted
  as `move` ops toward the generated parent ID. The truth attribute inflates no-op and modify
  counts. Stopped chains are not restarted. `opml.py` has an over-indented R1 comment.
- **N5 — Registration.** Register Reviews 22 and 23 in `docs/dev/reviews/STATUS.json`; the reviewer
  was restricted to editing this file only.

**Verdict:** **APPROVE WITH NON-BLOCKING NOTES**
