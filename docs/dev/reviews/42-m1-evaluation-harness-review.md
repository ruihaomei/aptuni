# Review 42 — M1 versioned evaluation harness review

**Date:** 2026-09-20

**Reviewer:** independent correctness and evaluation-discipline review agent (read-only)

**Scope:** the first Slice 16 production retrieval evaluator, frozen inputs, manifest, CI wiring,
and task-language-gated fallback.

## Verified

- The harness scores production `SqliteProjection`, keeps dev and holdout separate, and emits
  deterministic ranked outputs plus hashes, versions, thresholds and runtime facts without corpus
  text or private profile data.
- The production run passes frozen retrieval thresholds: dev recall@5 about 0.992, dev MRR 1.0,
  holdout recall/MRR 1.0, every short-CJK case found, and zero false positives on both splits.
- Compact-query regressions catch restoration of broad any-term fallback while the motivating task
  queries remain covered.

## Blocking findings

1. A threshold failure stopped the job before the later artifact upload, losing the written failure
   manifest.
2. Frozen input verification worked under direct fault injection, but no regression neutralized it
   or mutated every file protected by `FREEZE.json` through the full evaluator.
3. `EVALUATION_PLAN.md` called the already-opened S03 holdout “untouched”; it needed to distinguish
   sealing until first score from immutable regression use afterward.

**Verdict:** **BLOCK**
