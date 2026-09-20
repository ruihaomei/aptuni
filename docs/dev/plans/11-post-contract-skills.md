# Slice 18 — Post-contract skills

**Status:** Complete locally (2026-09-20; Review 46 APPROVE)
**Owns:** M1.5 repository skills `add-source-provider`, `run-evals`, `audit-licenses`, and `release`.

## Runnable outcome

Four repository-local skills guide coding agents through the contracts that stabilized in Slices
14–16. A fixture-driven developer test validates each skill's trigger metadata and local references,
then executes its bounded smoke command against synthetic or repository-owned inputs.

## Acceptance

1. Every skill has a matching directory/name, third-person trigger description, explicit boundaries,
   a short workflow, and no dead local reference.
2. `add-source-provider` preserves the snapshot/delta boundary, requires synthetic privacy and
   failure fixtures, and treats a common contract or extension-version change as ADR/review work.
3. `run-evals` executes the frozen production harness, retains a manifest, refuses frozen-input
   edits, and keeps dev/holdout and synthetic/real-world claims distinct.
4. `audit-licenses` checks the lock/notices, tracked secrets, workflow, built artifacts and the
   locked vulnerability audit without claiming that scanners prove safety.
5. `release` is a local dry-run only: it proves a clean tree, version/changelog readiness,
   reproducible artifacts, install smoke and evidence collection, but cannot publish, tag, push or
   infer maintainer approval.
6. `tests/dev/test_skills.py` loads one fixture per skill and executes its declared smoke command;
   release artifacts are compared byte-for-byte and checked for required legal files.

## Non-goals

- Creating a new source-provider implementation or changing a public plugin contract.
- Publishing a package, Git tag, GitHub release, or attestation.
- Replacing CI, independent review, or the full repository gate with a skill smoke.
- Claiming Linux or real-host support without the separately required hosted evidence.
