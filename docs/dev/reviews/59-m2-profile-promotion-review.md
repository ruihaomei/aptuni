# Review 59 — M2 Automatic Profile Promotion

**Reviewer:** independent code-review agent

**Date:** 2026-09-22

**Scope:** ADR-0020, canonical `Memory → Fact` transition, owner CLI review, permissions,
provenance/temporal lineage, incremental/full validation, privacy closure and Context visibility

## Findings and remediation

The first pass blocked two issues. Rejecting a promoted Fact made refresh attempt a second
historical promotion, and a policy promotion event could target an ordinary Fact or Evidence.
Both were fixed test-first: any historical promoted Fact now makes refresh a no-op, and policy
promotion targets are restricted to CandidateMemory or Memory with one linked root Memory or Fact.

The second pass found that the invariant checked cardinality but not the claim copied into the
Fact, and that counting every corrected Memory as a root broke `doctor`. The invariant now binds
the exact statement, module, provenance, temporal bounds, evidence, confidence, fixed labels,
retention, event time and policy epoch; candidate promotion counts one asserted root while allowing
append-only corrections.

The final incremental probe found that a duplicate policy event could commit and fail only during
`doctor`. Event-side validation now enforces one policy promotion event per target at commit time.
The regression proves the rejected commit leaves the Vault healthy.

The reviewer independently confirmed that rejection cannot recreate a claim, invalid and duplicate
events fail closed, ordinary Facts cannot enter the Profile-review commands, corrected Memories
remain valid, and pending Profile review state reaches the Context API.

## Non-blocking notes

- The implementation is fail-closed for disabled automatic promotion and revoked/superseded
  Memories; dedicated matrix cases would improve direct coverage.
- `facts_valid_at()` does not apply Fact rejection events. No production interface currently uses
  it; define historical rejection semantics before exposing that temporal view.

**Verdict:** **APPROVE WITH NON-BLOCKING NOTES**
