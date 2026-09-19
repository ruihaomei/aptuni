# Review 18 — M1 GitHub Standard Source focused re-review

**Date:** 2026-09-19

**Scope:** read-only re-review of every Review 17 blocker and the follow-up concurrent-journal race.

## Verification

- The per-source lock path is a hash outside user-controlled source paths; the lock begins before the
  canonical snapshot and spans recovery, provider access, journal, commit, state, and cleanup. OS
  lock semantics release it on exceptions and process death.
- Pending-state recovery covers pre-commit, post-commit, post-state-save, ref-advance, and concurrent
  two-service execution without duplicate or orphaned Evidence.
- Secret, hidden, VCS, and cache paths are excluded before selection/fetch, and an excluded rename
  withdraws previously admitted Evidence.
- Userinfo, explicit/invalid ports, mismatched origins, cross-origin redirects, and hidden final
  redirects are denied; stored origins are canonical and credentials remain references.
- Recursive and subtree entries fail closed on malformed identity, invalid paths, and duplicates.
- Blob response SHA/size and recomputed Git object identity must all match before persistence.
- The full test suite, Ruff, and strict mypy pass.

Review 16 was not assessed and remains pending with verdict `BLOCK`.

**Verdict:** **APPROVE**
