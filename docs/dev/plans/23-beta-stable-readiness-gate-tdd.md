# Plan 23 — Machine-Readable Stable Readiness Gate TDD

## Goal

Produce one content-free JSON report that evaluates every Stable requirement without converting
missing automated evidence, owner labels, elapsed dogfood time or owner approval into PASS.

## Contract

- `tools/stable_gate.py` consumes a versioned, content-free evidence document bound to one candidate
  commit and emits an atomic JSON report.
- Automated categories A–J use the exact Beta contract checklist. Missing or false automated checks
  are FAIL; no checklist item can disappear silently.
- Retrieval quality is calculated from counts with thresholds frozen at 30 scored real owner trials,
  useful precision >= 0.80, noise <= 0.20 and zero exposure violations. Missing/undersized samples
  are `INSUFFICIENT REAL-WORLD DATA`, not PASS.
- Longitudinal stability requires at least 14 elapsed dogfood days, zero unresolved P0/P1 blockers
  in the final seven days and zero privacy/data-integrity blockers. Missing time/evidence is
  `INSUFFICIENT REAL-WORLD DATA`.
- The subjective UX Gate passes only with the exact phrase `Aptuni User Experience Gate: PASS`
  bound to the candidate commit. Stable publication remains `OWNER ACTION REQUIRED` until its later
  explicit authorization.
- A stale evidence commit, malformed values, failed clean-room audit or failed automated check is
  FAIL. Reports contain reasons and counts only, never queries, labels, Profile content or paths to
  private sources.

## Failing-first matrix

1. An empty evidence document lists all A–J categories and cannot pass.
2. Missing real trials and dogfood time report `INSUFFICIENT REAL-WORLD DATA`.
3. Threshold boundary values pass; one-less sample, lower precision, higher noise or any exposure
   violation does not.
4. Casual UX wording cannot pass; the exact phrase with a mismatched commit is invalidated.
5. Every named automated check is required; missing, false and non-boolean values fail closed.
6. A fully green A–J evidence set yields Automated Stable Gate PASS while release readiness still
   requires UX, clean-room audit and explicit Stable publication authorization.
7. Output is deterministic, atomic, schema-versioned and content-free.

## Exit evidence

Focused unit/CLI tests; Ruff and strict typing; a real current report showing honest blockers; full
repository/developer gates; independent release-contract review; durable state and local checkpoint.
