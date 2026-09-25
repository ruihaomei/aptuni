# Review 69 — Repeatable Owner-Labelled Evaluation Trials

**Date:** 2026-09-25
**Scope:** `evaluate discard`, `evaluate score --rest-noise`, and report additions
(`unscored_trial_ids`, `repeated_queries`, per-mode human output) in
`src/aptuni/application/evaluation.py` and `src/aptuni/cli/evaluation_cli.py`; tests; README;
ADR-0022 2026-09-25 "repeatable owner-labelled trials" amendment
**Reviewer:** independent agent (`code-reviewer`)

## Findings

No blocking finding. No new durable field (schema stays v3) and no query, context or record text is
stored or printed; the digest prefix reveals less than the full digest `trial --json` already
shows. Discard validates ids before the lock, is all-or-nothing, refuses contaminated state, leaves
snapshots and the state file untouched on failure, writes atomically, and keeps the
`privacy → source_operations` lock order; privacy inventory and purge still cover the state.
Rest-noise can label only records the trial returned and always yields a complete partition. Report
series follow creation order, separate modes and avoid division by zero; new terminal output prints
only validated ids, hex prefixes, constants and numbers.

Non-blocking notes applied: discard now refuses a trial that recorded an exposure violation, so
permission evidence cannot be erased (`evaluation_trial_protected`); the key is renamed
`query_digest_prefix`; the ADR documents how empty trials count; tests now cover both-mode series,
both-labelled rest-noise, contaminated-state discard and exact error codes. Owner-only labelling
remains a policy rule, as it already was for `score`.

## Verification

- Evaluation and privacy suites: 55 passed (reviewer); 37 evaluation tests after note fixes.
- Full gate: 801 passed, 3 optional skips, 62 subtests; Ruff, strict mypy, relay and frozen
  lexical/hybrid evaluation green.

**Verdict:** **APPROVE WITH NON-BLOCKING NOTES**
