# S05A focused review round 2 — re-review of round-1 remediation

**Date:** 2026-09-19

**Reviewer:** the round-1 reviewer, resumed with its own context. It stayed read-only and used
throwaway scripts under `/tmp`, deleted afterwards. The pinned run gave 87 tests PASS and left
`git status` clean. Every round-1 reproduction was confirmed fixed.

## Findings

| # | Severity | Finding |
|---|---|---|
| 1 | BLOCKING | Content-addressed `delta_id` cannot tell a legitimate repeated A→B from a late redelivery of the old A→B after B→A. The old delta was re-applied: the head moved to B while the source was at A, a fact was falsely flagged, and the provider got stuck. |
| 2 | BLOCKING | A held Folder/GitHub item edited while unobserved got a new identity through a silent `add` at the same key. The edit never reached dependent facts. |
| 3 | NON-BLOCKING | GitHub vanished-blob priority could be flooded by a common blob (for example 20 empty `__init__.py` files), which pushed a new manifest out of the budget. |
| 4 | NON-BLOCKING | OPML branch-export demotion cascades over a moved subtree, and the split persists until review. |
| 5 | NON-BLOCKING | Repeated OPML edits and reverts accumulate held nodes with no auto-release. |
| 6 | NON-BLOCKING | Releasing a hold can leave a queued review item stale. |
| 7 | NON-BLOCKING | `gate()` returned at the first unknown locator without validating the other one. |

## Remediation (test-first; `tests/test_round2.py`)

- **F1:** `CandidateDelta.sequence` (per source, monotonic) is part of `delta_id`, and providers
  increment it. The ledger de-duplicates by `delta_id` and requires `base == head` plus the next
  sequence. Covered by redelivery, gap and flip-flop tests.
- **F2:** a held item re-observed at its own key keeps its identity. Changed bytes emit
  `modify` + `needs_review` (`held_item_changed`).
- **F3:** priority is given only when exactly one fresh path carries the vanished blob.
- **F4–F6:** recorded as limits in `S05A-sources.md`, owned by the Slice 7 review loop.
- **F7:** the gate validates every understood locator before routing to review.

**Verdict:** **BLOCK**
