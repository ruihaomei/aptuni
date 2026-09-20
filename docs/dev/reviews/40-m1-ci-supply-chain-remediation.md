# Review 40 remediation — locked build/audit inputs and credential coverage

**Date:** 2026-09-20

- **Responds to:** `40-m1-ci-supply-chain-review.md`

## Changes

- Added exact `supply` lock roots for Hatchling 1.27.0, Editables 0.5 and pip-audit 2.10.1.
- CI first installs every locked group without the project, then installs the project with build
  isolation disabled. Reproducibility builds disable both network access and build isolation.
- The fixed build epoch is 1980-01-01, the earliest ZIP-representable timestamp; epoch zero fails
  correctly under the now-pinned backend.
- pip-audit runs from the locked environment. Clean-wheel installation consumes the audited
  hash-locked runtime export, then installs the built wheel with `--no-deps`.
- Added ASIA, `github_pat_` and `sk-proj-` patterns plus mutation-sensitive regressions.
- Kept Ubuntu evidence explicitly pending; no Linux support claim was added.

## Validation

- Fresh two-stage sync built Aptuni and exposed `pip-audit 2.10.1` without isolated build resolution.
- Offline/no-isolation builds were byte-identical; artifact legal checks and clean-wheel smokes
  passed.
- Full gate: 457 tests plus 47 subtests; ruff, strict mypy, 26 developer tests and relay passed.
