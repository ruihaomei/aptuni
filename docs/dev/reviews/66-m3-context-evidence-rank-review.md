# Review 66 — Evidence Rank in Context and Evidence-Mode Dogfooding

**Date:** 2026-09-25
**Scope:** rank-preserving L3/L4 ordering and canonical `layers` in
`src/aptuni/application/service.py` and `context.py`; longitudinal evaluation schema v3
(`include_evidence`, `evaluate trial --evidence`, `by_context_mode`) in `evaluation.py` and
`cli/evaluation_cli.py`; regressions; ADR-0005 and ADR-0022 amendments; KI-018 note
**Reviewer:** independent agent (`code-reviewer`)
**Trigger:** the first real longitudinal trial returned 100% unrelated Profile/Memory for a query
only Notion Evidence answers

## Diagnosis reviewed

1. Default Context is L3-only by ADR-0005, and the evaluator could not request L4: an evaluator
   limitation.
2. With Evidence requested, a stable L3-before-L4 sort discarded retrieval rank, so a better-ranked
   Evidence unit came second and was the one truncated under budget: a product defect.
3. The residual L3 noise is the ADR-0004 any-term fallback behaving as specified; tracked under
   KI-018 and deliberately not retuned on one trial. The reviewer agreed with this classification.

## Findings

No blocking finding. Filtering (host scope, module, exposure) still precedes ordering; the order is
deterministic (`bm25`, then `record_id`); identity-card and memory-review paths are unaffected;
`layers` is unchanged for every pre-existing response shape; frozen evaluations call the projection
directly and are unaffected. Schema v3 keeps exact-field validation, chained v1→v2→v3 migration,
atomic writes and no content bytes, and adds no privileged lane. With the old sort simulated, both
new regressions fail and the exposure-guard test still passes.

Non-blocking notes: make the budget test's size precondition explicit; add v2-with-mode,
v3-without-mode and boolean-version rejection tests; reject `schema_version: true`; mention the
version bump in ADR-0022 — all applied. Stating "order is relevance, not trust" in the MCP tool
description is recorded in `BACKLOG.md`.

## Verification

- Focused context/evaluation/MCP/public-API suites: 63 passed; after note fixes 43 focused passed.
- Full gate: 749 passed, 3 optional skips, 62 subtests; Ruff and strict mypy clean.

**Verdict:** **APPROVE WITH NON-BLOCKING NOTES**
