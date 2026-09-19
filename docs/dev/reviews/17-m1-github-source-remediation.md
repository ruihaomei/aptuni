# M1 GitHub Standard Source Review Remediation

- **Date:** 2026-09-19
- **Responds to:** `17-m1-github-source-review.md`
- **Status:** all blocking findings fixed test-first and independently re-reviewed

| Finding | Remediation |
|---|---|
| Crash/ref-advance orphan | Write a durable pending snapshot/delta/final-state journal before the canonical commit. Recovery distinguishes pre-commit, complete post-commit, partial-impossible, and post-state-save cases. The exact add → state-save crash → ref-advance removal regression now retracts both committed items. |
| Concurrent journal overwrite | A hashed per-source `flock` in the non-Vault state directory serializes snapshot, recovery, provider I/O, journal, canonical commit, state save, and cleanup. A deterministic two-service race proves the second sync cannot reach the provider until the first finishes. |
| Secret/path admission | GitHub selection now excludes secret-pattern filenames, hidden paths, VCS and cache directories before blob fetch. A serialized-Vault marker regression proves excluded bytes never enter Evidence or source state; rename into an excluded path withdraws prior Evidence. |
| URL credentials/origins | Source configuration rejects URL userinfo, explicit/invalid ports, non-HTTPS or mismatched origins, and stores canonical lowercase official/enterprise origins. Tokens remain environment-variable references resolved only at use time. |
| Malformed trees | Recursive and bounded subtree results strictly validate mappings, paths, types, 40-hex identities, and duplicates. Malformed identity fails the sync instead of proving absence. |
| Blob identity | Blob responses must echo the requested SHA and decoded size; Aptuni recomputes the Git blob SHA-1 over the bytes before creating Evidence. |

Validation after remediation: 197 tests plus 47 subtests, Ruff, strict mypy, relay checks, and
`git diff --check` pass.
