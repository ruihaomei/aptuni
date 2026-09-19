# S05B MarginNote Reconciler Review Remediation

- **Date:** 2026-09-19
- **Responds to:** `22-s05b-marginnote-reconciler-review.md`
- **Status:** blocking finding resolved by withdrawal; focused re-check requested

| Finding | Remediation |
|---|---|
| B1 R2 reverses an accepted ADR-0006 rule; duplicate moves become removals of live notes | R2 is **withdrawn**. Indistinguishable duplicates that moved are ambiguous again (`duplicate_content`), and same-position edits are reviewed as in S05A, including edits to empty text. `test_indistinguishable_duplicates_that_move_still_go_to_review` ports the S05A case into production tests and asserts no `remove`. Real-history removals of live notes: 10 (S05A) vs 9 (now). R1 and R3 are recorded in a dated ADR-0006 amendment. |
| Note: README mislabels reviews and overclaims | The spike README now uses the reviewer's figures (14 moves, 26 edits, top-level harness artifacts, R3 never fired), reports removals, lists all limits, and states that KI-020 stays open. |
| Note: harness truth attribute inflates no-op count; chains not restarted | Documented as limits. |

Validation: full pytest, Ruff and strict mypy pass. The replay harness reproduces the counts in
`spikes/s05b_marginnote/results/`.
