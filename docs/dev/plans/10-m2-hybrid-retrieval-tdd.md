# Milestone 2 Hybrid Retrieval Preview Plan (TDD)

**Status:** Accepted (2026-09-22)

## Objective

Ship an explicit, local-only hybrid search preview that improves recall for accepted memories while
preserving SQLite/FTS as the default retrieval path and the canonical Vault as the final authority.

## Vertical slice

- Add deterministic reciprocal-rank fusion over SQLite lexical rows and the selected Mem0
  generation. Provider similarity values are diagnostic only and never affect ordering.
- Add `aptuni search --hybrid`; default `aptuni search` and the Context API remain lexical.
- Require a fresh, valid Mem0 projection at the same Vault sequence. Missing, stale, invalid, or
  cleanup-required provider state fails closed with a bounded remediation message.
- Treat the semantic lane as memory-only. Hydrate and expose results only from the final stable
  canonical snapshot, reapplying module, review/revocation, and exposure policy.
- Add a new versioned hybrid evaluation fixture without changing the frozen S03 lexical corpus,
  judgments, thresholds, or holdout.

## Failing-first cases

1. Rank fusion is deterministic, deduplicates IDs, ignores provider scores, and uses canonical IDs
   as its final tie-break.
2. Default search never opens Mem0 and retains existing lexical behavior.
3. Hybrid search refuses absent, stale, invalid, or cleanup-required provider state and never falls
   back silently while claiming hybrid behavior.
4. Malformed provider rows, duplicate semantic IDs, and non-memory/foreign canonical IDs fail
   closed or are excluded before hydration.
5. A policy or Vault change during either lane retries and never exposes the now-hidden or revoked
   record.
6. Module filters apply consistently to both lanes and semantic-only matches remain bounded by the
   requested limit.
7. Optional runtime failures and local model failures return content-free errors; the query uses
   only the already-confined numeric-loopback Ollama transport.

## Verification

Run focused fusion, service, CLI, provider, and frozen hybrid-evaluation checks; then pytest, Ruff,
strict mypy, relay/developer checks, and an independent retrieval/privacy-contract review.

## Exit

The slice is complete when an owner can opt into hybrid search end to end, measured hybrid cases
pass their precommitted threshold, lexical defaults and Context API are unchanged, all returned IDs
survive the final canonical policy check, and independent review approves the boundary.
