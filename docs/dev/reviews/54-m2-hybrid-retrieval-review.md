# Milestone 2 opt-in hybrid retrieval preview review

**Reviewer:** independent Claude subagent review of the uncommitted hybrid-retrieval slice

## Scope

Reviewed the rank-fusion contract (`src/aptuni/retrieval/hybrid.py`), the hybrid service path
(`AptuniService._stable_hybrid_search` / `_semantic_search`), the provider read boundary
(`Mem0Projection.search`), the `LocalMem0Client.close` change, the `--hybrid` CLI surface, the
`retrieval.hybrid` catalog maturity flip and its bilingual strings, the evaluation harness changes
in `tools/run_evals.py`, the new frozen fixture, the ADR-0004 amendment, both READMEs, the
CHANGELOG, and focused unit/integration coverage. The review checked the change against
`AGENTS.md`, the accepted plan `docs/dev/plans/10-m2-hybrid-retrieval-tdd.md`, ADR-0003, ADR-0004
and Review 53, and additionally read the pinned upstream `mem0ai==2.0.20` source.

## Blocking findings

None. Every invariant in the review charter held under direct attack.

## Correctness, privacy and contract boundaries

- The semantic lane returns canonical IDs and a diagnostic float only. All text is hydrated from
  `final_records.exposable()` in `AptuniService.search`, so no provider value can become canonical.
  Every error message on the search path is a static literal and the provider module holds no
  logger, so provider content cannot reach an error, a log or the CLI.
- The `allowed_memories` filter is strictly stronger than the rebuild's `_decided` set: it adds
  `exposable()`, `record_type == "memory"`, accepted review status and the module filter on top of
  the same revocation set. `accept`/`reject` events target candidate IDs and only `revoke` targets a
  memory ID, so the two revocation computations are semantically identical.
- The final-snapshot recheck genuinely applies to semantic IDs, twice. Because the loop only returns
  when `final_seq == seq`, the first-snapshot accepted/revoked/module filter is provably still
  valid at return time. A policy or Vault change during either lane retries or fails closed.
- Lock usage is correct. `snapshot()` — which may trigger `Vault.open() -> recover()`, itself taking
  `source_operations_lock` — always completes before `_semantic_search` takes the lock, so the
  non-reentrant `flock` cannot self-deadlock. Rebuild and purge remain serialized against it.
- `LocalMem0Client.close` matches upstream: `Memory.close()` closes only `self.db` and never the
  Qdrant client, and `_telemetry_vector_store` is the real attribute name. Both stores are closed,
  every store is attempted after a failure, and the first failure is re-raised.
- `LocalMem0Client.search` matches the real 2.0.20 signature. It uses the embedder only and makes no
  LLM call, so the "constructed but never called" LLM boundary from Review 52 still holds.
- Fusion is deterministic and score-independent: mirrored input scores produce identical output,
  duplicate IDs within one lane fail closed, ties break lane-count then lexical-lane then canonical
  ID, and `limit` is bounds-checked.
- Default `search`, the Context API and MCP are untouched; `hybrid` is reachable only from the
  explicit CLI flag. Absent, stale, invalid and cleanup-required provider state each raise a bounded
  remediation error rather than falling back silently to lexical.
- The frozen S03 corpus, judgments, thresholds and holdout are unchanged. The new fixture is purely
  additive and checksum-bound, and the manifest additions are additive-only at evaluator version 2.
- The `planned -> preview` catalog flip only moves the advisor reason to `advisor.reason.evidence_gate`,
  so the plugin stays deferred and the "not selected automatically by setup or Recipes" claim in
  both READMEs remains true. The English and Chinese strings are parallel and honest.

## Non-blocking notes and their disposition

| Note | Disposition in this checkpoint |
|---|---|
| N1 — semantic lane has no relevance floor (`threshold=0.0`); an unmatched query can still return exposable memories up to `--limit` | Recorded as **KI-021**, documented in the ADR-0004 amendment and in both READMEs |
| N2 — `candidate_limit` pool truncation can change the fused top-`limit`; the ADR read as if fusion were exact | ADR-0004 amendment now states the bounded per-lane pool explicitly |
| N3 — the canonical-ID final tie-break was implemented but untested | Regression added (`test_fusion_breaks_a_full_tie_on_the_canonical_id`) |
| N4 — plan case 6's "semantic-only matches remain bounded by the requested limit" was untested | Regression added (`test_hybrid_semantic_only_results_stay_within_the_requested_limit`) |
| N5 — three service-level hybrid tests monkeypatch `_semantic_search`, bypassing the lock, the freshness gate and `Mem0Projection.search` | Backlogged. The CLI test already drives the real path, and the reviewer wrote factory-level equivalents for the revoked-memory and expose-disabled races and found no defect |
| N6 — double `close()` on the close-failure path | Fixed; the client handle is cleared before the close so `finally` cannot re-close |
| N7 — `score` changes scale between lexical and hybrid with no marker | Documented in the ADR amendment and both READMEs as comparable only within one invocation |
| N8 — the new frozen fixture was not registered in `EVALUATION_PLAN.md` | Registered alongside the context-noise fixture |
| N9 — upstream `Memory.search` can reach `spacy.cli.download` if spaCy is importable without `en_core_web_sm` (unreachable under the current pins, pre-existing on the `add` path) | Recorded in `docs/research/upstream/mem0.md` as a pitfall to re-check on any dependency change |
| N10 — the `Mem0Client` Protocol gained `search`, widening the surface ADR-0003 describes | ADR-0003 gained a cross-referencing amendment |
| N11 — `STATE.md` / `HANDOFF.md` still opened the slice | Updated in this checkpoint |

Also note that `..._rechecks_policy_after_semantic_lane` asserts an empty result, but in production
a policy change bumps the Vault sequence, so the real second iteration raises
`hybrid_projection_unavailable`. Both are fail-closed; the test simply documents a different
observable. This is folded into the N5 backlog item.

## Evidence

Executed by the reviewer: full `pytest`, `ruff check .`, `mypy src`, `tools/check_relay.py`, the
fixture checksum, four adversarial probes against the real `_semantic_search` ->
`source_operations_lock` -> `Mem0Projection.search` path using factory-level doubles (semantic-only
bounded by limit; revoked memory present in a fresh projection excluded; expose-disabled module
excluded; over-limit provider rows fail closed), two fusion probes (canonical-ID tie-break and the
truncation counterexample), and a read of the pinned upstream `mem0ai==2.0.20` sources.

Read but not executed by the reviewer: the real-runtime cases in
`tests/integration/test_mem0_projection.py`, including the new `Mem0Projection.search` assertion,
because `mem0`/`ollama` are not in the product `.venv`. **That gap was closed after the review**:
the hash-locked isolated runtime (`spikes/s10_mem0/requirements-lock.txt` plus `ollama==0.6.2`) ran
`tests/integration/test_mem0_projection.py`, `tests/unit/test_mem0_local.py`,
`tests/unit/retrieval/test_hybrid.py` and `tests/integration/test_retrieval.py` with **55 passed**,
including the real Mem0 2.0.20 rebuild-then-search through the production boundary.

## Conclusion

The slice meets every exit criterion in the accepted plan. Hybrid retrieval is strictly opt-in, the
canonical Vault remains the only authority, provider output is reduced to IDs before it can
influence anything user-visible, exposure policy is rechecked against the final stable snapshot, and
the default lexical path and Context API are unchanged. The remaining notes are honesty,
documentation and test-fidelity improvements, all either applied in this checkpoint or backlogged.

**Verdict:** **APPROVE WITH NON-BLOCKING NOTES**
