# Review 15 — Gate 0 exit (S01–S03 evidence + ADR acceptance)

**Date:** 2026-09-19

**Reviewer:** an independent, read-only agent. It re-ran S02 offline (12/12) and S03 `verify` plus
its unit tests (23/23). It checked S01 statically, because the pinned venv no longer exists. It
also scanned `spikes/` and `docs/` for private data.

## Findings (all non-blocking)

1. S01 was verified by reading the code; its 46 tests and crash points match the result document.
2. S01's `restore_from` re-baselines the chain and is not atomic. Production restore must fix both
   (ADR-0010 and ADR-0013 amendments).
3. S01's hash chain only detects uninformed edits, because HEAD is self-attesting.
4. Some ADR-0001 verification items are untested in S01 (same-valid-time conflict, out-of-order
   observation, projection rebuild, export/import). They move to M1.1.
5. S02 gaps: files not listed in RECORD are uncovered, and approval-to-import is not atomic. Its
   THREAT_MODEL items had not been applied.
6. S03 numbers match its results. The "precommitted" ordering is attested, not proven by history.
   There is a "24k" vs 25,000 typo.
7. `S04-mcp.md` still contained a stale "do not begin scaffolding" sentence.
8. The tree changed during the review (the pyproject/`aptuni` scaffold). The Gate 0 closure must be
   committed before the scaffold. Pydantic as a runtime dependency needs an ADR record.
   `requires-python` must not exceed the measured baseline. The relay check must pass.
9. The rename to Aptuni is incomplete in the ADR/plans. The collision check is a release gate.
10. Fixtures are clean: synthetic data only, no private paths or credentials.

## Outcome

ACCEPT for ADR-0001 through ADR-0013, each with a dated amendment (see each ADR's `Amendments`
section). Every exit-checklist item passes. The findings above are dispositioned in the closure
commit or recorded in `docs/dev/BACKLOG.md`.

**Verdict:** **APPROVE WITH NON-BLOCKING NOTES**
