---
name: release
description: This skill should be used when the user asks to "prepare a release", "run a release dry-run", or verify Aptuni release readiness.
---

# Prepare an Aptuni Release

## Goal

Produce a local, reviewable release-readiness bundle without publishing or changing remote state.

## Boundaries

- Read `docs/dev/STATE.md`, `docs/dev/HANDOFF.md`, `CHANGELOG.md`, `SECURITY.md`,
  `docs/dev/COMPATIBILITY.md`, and `docs/dev/plans/09-ci-and-supply-chain.md` first.
- This skill never publishes packages or attestations, creates or pushes tags, pushes commits,
  creates a GitHub release, enables repository settings, or consumes release credentials.
- Stop before public release until the maintainer confirms the version, changelog, name/package
  collision re-check, license/brand decision, supported matrix, hosted Ubuntu evidence, and real-host
  probes recorded in `STATE.md`.
- Never release from a dirty tree or treat a local macOS run as Linux evidence.

## Workflow

1. Confirm `git status --short` is empty and the intended version agrees across `pyproject.toml`,
   changelog, compatibility/security text, and the maintainer's authorization.
2. Run the full tests, developer checks, lint, strict type check, relay check, frozen evaluations,
   notice/secret/workflow checks, and locked vulnerability audit.
3. Build twice with `SOURCE_DATE_EPOCH=315532800`, compare wheel and sdist bytes, check their legal
   files, and install the wheel into a clean environment for CLI smoke tests. Follow the exact locked
   commands in `.github/workflows/ci.yml`.
4. Collect the SBOM, runtime requirements, vulnerability report, evaluation manifest, artifact
   hashes, test results, review verdicts, migration/rollback evidence, and compatibility evidence.
5. Present the bundle and all blockers to the maintainer. Publishing is a separate explicitly
   authorized action.

## Completion evidence

Report the proposed version, source commit, clean-tree check, artifact hashes, SBOM/eval binding,
test and audit results, hosted evidence, review verdicts, and a clear `ready` or `blocked` result.
