# Review 22 — S05B MarginNote OPML reconciler refinements (R1–R3)

**Date:** 2026-09-19

**Reviewer:** independent Claude subagent (did not write the code under review)

**Scope:** uncommitted working-tree changes on `main` (base `e3dbd2e`):
`src/aptuni/sources/opml.py` (R1 `parent_slot_content_match`, R2 duplicate/empty handling via
`_edited_in_place`, R3 `demote_weak_structural`), `tests/unit/sources/test_opml_real_history.py`,
`spikes/s05b_marginnote/{replay.py,README.md,results/*.json}`. The root `README.md` diff is
unrelated (no MarginNote/OPML content) and was not reviewed.

**Privacy:** the harness and my count-only extensions ran read-only on the maintainer's authorized
MarginNote 4 store. This report contains aggregate numbers only. No note text or IDs were printed,
copied or quoted.

## Method

- Read AGENTS.md, ADR-0006 (Decision, Verification, 2026-09-19 amendment), S05A-sources.md, the
  S05A spike tests, and the full diff.
- Re-ran `replay.py` for the new matcher. Re-ran the same harness with the HEAD (S05A) `opml.py`
  swapped in (`temp/review22/replay_baseline.py`).
- Added count-only scorers: `temp/review22/extended_score.py` (review precision, real edits,
  attribute-only modifies), `review_breakdown.py` (where the residual reviews come from),
  `move_audit.py` (real moves and edits), and `chain_audit.py` (overlay reconstruction).
- Adversarial fixtures and a 3,000-seed differential fuzz: `temp/review22/test_review22_adversarial.py`.
- Ran the S05A spike `test_opml.py` unchanged against the production module through a shim
  (`temp/review22/shim/`).

## Checklist

| # | Check | Result | Evidence |
|---|---|---|---|
| 1 | R1 cannot link different content | PASS | `opml.py:133-135` keys on `(content_hash, parent, sibling_index)`, so R1 links identical text only. In the fuzz (3,000 seeds; full and branch scans), every modify/move whose content changed carries `children_signature_match` or `vendor_id_match`. |
| 2 | R3 is correct and its demotion is consistent | PASS | `opml.py:144-153`. The fuzz never saw a `move` with changed content under `children_signature_match`. Order dependence between a demoted parent and a signature-matched child cannot occur: a child whose text changed alters the parent's signature. Children of a demoted parent become `move` ops that point at the new generated parent ID (see N4). |
| 3 | Branch/partial guarantees | PASS | Fuzz and fixtures: branch scans emit no `remove` and no `move`. `partial_scope_relocation` still runs after R3 (`opml.py:204-206`) and sees R3's retractions. R2 duplicate moves in branch mode retain the old items instead of removing them. The existing `test_opml_branch_copy_is_not_a_silent_move` passes. |
| 4 | Held/reserved review semantics | PASS | R3-demoted subjects join `used` (`opml.py:210`), so they are carried forward `held`. The fixture's third scan is a no-op. In the fuzz, every old candidate is held, held and active sets are disjoint, and re-scanning unchanged input is always a no-op. `test_opml_review_reserved_node_is_held_not_tombstoned` passes. |
| 5 | Delta envelope contract | PASS | `CandidateDelta.build` enforces one op per subject and candidates only on `ambiguous`, and it raised on none of the 298 real transitions or 9,000 fuzz scans. Every ambiguous op has at least 2 distinct candidates. Results JSON reproduced byte-for-byte in `counts` for both matchers. |
| 6 | Real in-place edits previously sent to review | CHANGE (non-safety) | An edit to empty text (`Bayes` → `""`) was reviewed at HEAD and is now a silent add plus a remove proposal (fixture `test_edit_to_empty_was_review_now_silent_add_remove`). On real data: 26 real in-place edits under both matchers. HEAD reviewed 3; the new matcher reviews 4. None are lost. No edit-to-empty occurred in the data. |
| 7 | ADR-0006 review contract | **FAIL** | See B1. |
| 8 | Existing production tests kept | PASS | No existing test file was modified. The 3 OPML tests in `tests/unit/sources/test_hardening.py` pass unchanged. Note that most S05A OPML tests exist only in `spikes/s05a_sources/tests/`. Run against production, 15 of 16 pass. The one that fails is `test_indistinguishable_duplicate_moves_are_ambiguous` (see B1). |
| 9 | New tests | PASS (thin) | 5 new tests cover R1–R3 happy paths. None covers R2 add/remove or remove proposals in full mode, R2 in branch mode, R3 in branch mode, or R3 held behavior across rescans (the fixtures here cover these). |
| 10 | Harness reconstruction | PASS with limits | `chain_audit.py`: 998 snapshots, 488 full (matches the README), and no chain starts from a partial snapshot. 24 chains stop, all because the overlay is larger than `note_count` (an unresolved deletion); 219 snapshots are skipped. Only 1 stopped chain has a later full snapshot it could restart from. At full snapshots inside valid chains, the overlay key set always equals the snapshot key set (0 masked add+delete). |
| 11 | Scoring definitions | PASS with caveats | `false_link_changed_content` is the correct safety metric. However, the untrusted truth attribute enters `unknown_attributes`, so the 2,677 `op_modify` are all `attributes_changed` artifacts of identical-content swaps, and the "no-op syncs 3 → 85" row depends on this artifact. Review precision is not scored (see N1). |
| 12 | README claims follow from the numbers | **PARTIAL** | Headline counts reproduce. Labels and inferences overclaim (N1–N3). |
| 13 | Results JSON contains no content | PASS | Both files contain only fixed metric keys, the parser tuple, a date, and numbers. |
| 14 | `uv run pytest` | PASS | whole suite green |
| 15 | `uv run ruff check .` | PASS | "All checks passed!" |
| 16 | `uv run mypy src` | PASS | "no issues found in 47 source files" |

## Blocking findings

### B1 — R2 reverses an accepted ADR-0006 review contract without an ADR amendment

- **Where:** `src/aptuni/sources/opml.py:172-185` (`_edited_in_place` replaces the `duplicate_content`
  branch), `opml.py:212-223`, and the module docstring at `opml.py:12-16`.
- **Contract:** ADR-0006 Decision says "Ambiguous matches become review items." Its Verification
  says "ambiguous MarginNote match stops for review." S05A-sources.md:28, which was accepted at the
  Gate 0 exit, lists "indistinguishable OPML duplicates … become `ambiguous` + `needs_review`." The
  S05A test `test_indistinguishable_duplicate_moves_are_ambiguous` also asserts `remove` is absent.
- **Behavior now:** indistinguishable duplicate moves become add plus `remove`. A `remove` is a
  tombstone proposal (`Operation.effect`) against a note that still exists. Repro:
  `PYTHONPATH=src:temp/review22/shim .venv/bin/python -m pytest temp/review22/shim/test_s05a_opml_on_production.py`
  gives 1 failed and 15 passed (`KeyError: 'ambiguous'`). Also see
  `temp/review22/test_review22_adversarial.py::test_duplicate_move_now_removes`. On real history,
  `false_remove` goes from 10 to 5,886 and silent splits (`false_split`) from 23 to 6,582, of which
  3,006 are non-empty text.
- **Why blocking:** this is a contract change to review/tombstone semantics, which AGENTS.md
  classes as high-risk. AGENTS.md says contracts "never change silently: write or revise an ADR."
  The real-data burden (about 86 prompts per sync) is legitimate new evidence under rule 5, and I do
  not object to the direction. Safety is preserved: I found no different-content link. But the
  reversal needs to be recorded.
- **Fix (small):** (a) add a dated ADR-0006 amendment. It should state that identical-content
  (and empty-text) OPML duplicates resolve to add/remove, not review; that the resulting `remove` is
  a tombstone proposal for a possibly live note; and that ingest must dedupe on content or skip
  empty-text nodes. (b) Port the S05A duplicate-move test into `tests/unit/sources/` with the
  revised expectation. It should also cover the branch case, which must retain old items and
  produce no `remove`. (c) Update the S05A-sources.md row, or add a pointer to the amendment.

## Non-blocking notes (to `docs/dev/BACKLOG.md`)

- **N1 — The residual 2,003 reviews are mostly a harness artifact and are not in-place edits.** The
  README table labels all 2,003 as "in-place text edit". Measured: 2,002 of 2,003 sit at root
  level, where sibling order is the harness's note-ID sort. Only 2 of 2,003 have the true note among
  their candidates. HEAD's 64 were likewise only 2 precise. The README should present
  `same_position_text_changed` as a reason code and not as a count of edits. It should also say the
  real-exporter review rate is unknown until a real OPML export is replayed. "Its precision should
  be measured" can now be stated as roughly 0.1% on this history.
- **N2 — The safety evidence is narrow.** The replayed history has 14 real moves (all same content),
  26 real in-place edits (none linked), 0 edit-plus-move events, 0 evaluated deletions, and 0
  `children_signature_match` links. So "0 false links across different content" was barely
  exercised on the dangerous path. Finding 1 ("safe on real data") should be scoped to this
  history. R3 never fired on real data (0 `weak_structural_match`), so calling it "learned from
  replaying" (test module docstring and README) overstates the evidence. It is a synthetic-motivated
  hardening. KI-020 should stay open until the real full plus branch OPML export is replayed, as the
  README's Limits section says.
- **N3 — The README table omits `false_remove` (10 → 5,886).** Finding 4 ("evidence churn, not
  wrong evidence") should acknowledge that these are tombstone proposals against live notes.
- **N4 — Children of an R3-demoted parent are emitted as `move` ops.** Their new parent is the
  generated subject of the ambiguous item. If review resolves the parent to the old subject, those
  moves point at a subject that no longer exists. The same pre-existing pattern applies to
  duplicate-reviewed parents at HEAD, so this is not new, but review resolution should re-parent
  children.
- **N5 — Edit-to-empty is now silent** (checklist row 6). This is acceptable if ingest skips
  empty-text nodes. Record it in the ADR amendment.
- **N6 — Harness details.** (a) After a deletion the overlay could restart at a later full snapshot
  instead of stopping; this affects 1 chain. (b) The truth attribute makes identical-content swaps
  appear as `attributes_changed` modifies. Score them separately, or strip the attribute before
  diffing attributes, so the no-op count reflects a real export. (c) An add and a delete in the same
  delta would go undetected under the size-equality rule. None was observed at full-snapshot
  checkpoints.
- **N7 — Style.** `opml.py:132` has an over-indented comment. `_edited_in_place`'s docstring puts
  the R2 rationale on the wrong function: R2's add/remove effect comes from removing the
  `duplicate_content` branch in the scan loop.
- **N8 — Registration.** Register this report in `docs/dev/reviews/STATUS.json`; the reviewer was
  restricted to editing this file only.

**Verdict:** **BLOCK**
