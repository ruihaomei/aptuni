# Review 17 — M1 GitHub Standard Source

**Date:** 2026-09-19

**Scope:** the uncommitted GitHub Standard Source vertical slice. The independent reviewer was
read-only and focused on origin/redirect confinement, credential handling, response bounds,
snapshot/delta correctness, privacy exclusions, crash replay, and compatibility.

## Blocking findings

| # | Finding |
|---|---|
| 1 | A ref advance after canonical commit but before source-state save could orphan active Evidence because replay rebuilt from stale state. |
| 2 | GitHub selection did not default-exclude secret, hidden, VCS, or cache paths. |
| 3 | Enterprise repository/API URLs accepted and persisted embedded userinfo; explicit ports were not rejected. |
| 4 | A malformed subtree could be silently dropped while coverage was reported complete, permitting false removals; recursive entries also lacked strict path/duplicate validation. |
| 5 | Blob responses were decoded without verifying response identity, size, or the Git object hash. |

A first remediation added a durable pending source-state journal and fixed findings 2–5. Focused
re-review then found one further blocker: concurrent syncs could overwrite the single per-source
pending journal. That concurrency defect is included in the remediation record and Review 18.

Review 16 was outside this review and remains pending with verdict `BLOCK`.

**Verdict:** **BLOCK**
