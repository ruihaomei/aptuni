# M1 MarginNote 4 Source Review Remediation

- **Date:** 2026-09-20
- **Responds to:** `24-m1-marginnote4-source-review.md`
- **Status:** blocking findings fixed test-first; focused re-check requested

| Finding | Remediation |
|---|---|
| B1 card deleted during partial coverage stays current forever | While coverage is partial, every previously known card that was not observed is carried forward (`scan.py`); the next complete read removes it. Test: `test_deletion_during_partial_coverage_is_withdrawn_later`. |
| B2 card moved out of a missing notebook duplicates and wedges | Only unobserved cards are carried, so an observed card is never duplicated. Test: `test_card_moved_out_of_a_missing_notebook_does_not_wedge`. |
| N1 excerpt-derived labels | ADR-0015 now states the rule (an untitled parent is labelled by ≤32 characters of its excerpt, never its body). Test: `test_untitled_parent_label_is_a_bounded_excerpt_head`. |
| N2 probe order | Sync decides container membership from the path string (`os.path.abspath`), then probes before any filesystem access to the container. |
| N3 document accuracy | ADR-0015 status names match the code; the deep link is labelled inferred and not verified. |
| N4 schema check outside the transaction | `BEGIN` now precedes the schema gate. |
| N5 nested merged excerpts | Merge chains resolve to the final card. Test: `test_nested_merged_excerpts_count_toward_the_final_card`. |
| N6 CLI untested | `tests/integration/test_marginnote_cli.py`: discovery persists nothing, evidence `open_url`, missing library, closed pipe. |
| N7 empty read withdraws everything | A complete read with no concepts after a non-empty snapshot stops with `marginnote_store_empty`. Test: `test_an_empty_read_never_withdraws_everything`. |

Validation: full pytest (295 plus 47 subtests), Ruff, strict mypy.
