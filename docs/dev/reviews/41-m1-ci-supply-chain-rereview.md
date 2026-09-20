# Review 41 — M1 CI and supply-chain focused re-review

**Date:** 2026-09-20

**Reviewer:** independent correctness and supply-chain re-review agent (read-only)

**Scope:** Review 40's three local blockers and any defect introduced by their remediation. Hosted
Ubuntu execution was assessed as an external evidence item, not inferred from workflow text.

## Review 40 closure

- **Build backend — closed.** Hatchling and Editables are exact lock members. A fresh environment
  successfully performed the two-stage no-project then no-isolation sync; two offline builds at the
  ZIP-safe epoch were byte-identical and contained every required legal file.
- **Audit/smoke input mismatch — closed.** pip-audit runs from the exact locked group. The clean
  environment installs the hash-locked runtime export and only then the wheel with `--no-deps`;
  both CLI smokes passed against that set.
- **Credential formats — closed.** Independent mutations reverting each ASIA, `github_pat_`, or
  `sk-proj-` expression made its regression fail.

## Non-blocking pending evidence

The workflow is structured to exercise the real filesystem, concurrency, Vault crash and backup
suites on Ubuntu 24.04, but there is no configured remote or recorded Actions run. Record a passing
hosted run for the checkpoint commit before marking Ubuntu/ext4 durability complete or claiming
Linux support.

No code blocker remains in the reviewed scope.

**Verdict:** **APPROVE WITH NON-BLOCKING NOTES**
