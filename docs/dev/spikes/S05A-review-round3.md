# S05A focused review round 3 — acceptance

**Date:** 2026-09-19

**Reviewer:** the same independent reviewer as rounds 1 and 2, resumed read-only. It reviewed commit
`7cb0949`: 94 tests PASS, `git status` clean after the run, relay check passing, and its `/tmp`
scratch deleted.

Every round-2 reproduction is fixed. Attacks on the new sequence and held-release mechanisms
behaved safely:
- forked histories, a scan from an older previous, sequence gaps and cross-source interleaving;
- a forged "duplicate" (integrity is checked first);
- a held-item modify sharing a delta with a same-hash add;
- a GitHub held release after truncation.

## Findings (all non-blocking)

1. Recovery after an undelivered delta was not documented, including a skipped empty no-op delta.
   A skipped delta safely makes later deltas stale, but the provider must rebase.
2. The ledger queues a `held_item_changed` modify without flagging dependent facts. That is
   conservative, but it should be documented.
3. The envelope gained `sequence` without a version bump, and a missing field raised a raw
   `KeyError`.
4. No doc overclaims found.

## Disposition

| # | Action |
|---|---|
| 1 | The delivery rule is added to contract refinement #3 in `S05A-sources.md`. |
| 2 | Documented as a limit: review-gated operations take no effect before review, and Slice 7 decides whether a pending review flags dependents. |
| 3 | `ENVELOPE_VERSION` is now 2, and missing fields map to `ContractError` (test-first; 95 tests). |

**Verdict:** **APPROVE WITH NON-BLOCKING NOTES**
