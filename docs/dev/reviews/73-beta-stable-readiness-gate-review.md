# Review 73 — Beta Stable Readiness Gate

**Date:** 2026-09-27
**Scope:** `tools/stable_gate.py`, `tests/dev/test_stable_gate.py`, `docs/dev/STABLE_READINESS.md`,
Plan 23; commit binding, owner-sequence digests, content-free output and honest non-PASS states
**Reviewer:** independent agent (`code-reviewer`)

## Findings

Before review, a self-review found and fixed test-first three fail-open gaps and one hygiene gap: an
invalid current commit could "match" a missing evidence commit, a dirty working tree could still pass
the automated gate, a small sample with poor early ratios reported FAIL instead of
`INSUFFICIENT REAL-WORLD DATA`, and the commit-bound report directory was not git-ignored.

The independent review then probed metric types (bool, float, NaN), wrong shapes, uppercase and
invalid commits, pre-authorized audit/publication, stale digests after changing metrics or version,
unknown private keys and binary/non-object evidence. None produced a better status than earned or
leaked input content. It raised no blockers and thirteen notes. The following were fixed
test-first in the same slice: an output path could mask a modified tracked file (only an untracked
output line is now tolerated); a not-yet-recorded clean-room audit reported FAIL instead of
`OWNER ACTION REQUIRED`; deep nesting exited 1 with a traceback and `schema_version: true`/`1.0` was
accepted (both now exit 2); a non-bool library `worktree_clean` flag counted as clean; and the UX
gate compared against the unvalidated current commit. Worktree rules, exit 2 and the H boundary now
have direct tests. Candidate-version/package binding, records-per-trial floors, running B checks
for real, an in-repo A–J checklist, an evidence digest and parent-directory fsync moved to BACKLOG.

## Verification

- `python -m unittest discover -s tests/dev`: 56 tests OK.
- Ruff (repository) and strict mypy on the tool: passed.
- A real current report at `2bb9f44` shows FAIL for unbound evidence and a dirty tree,
  `INSUFFICIENT REAL-WORLD DATA` for G/H and `OWNER ACTION REQUIRED` for UX.

**Verdict:** **APPROVE WITH NON-BLOCKING NOTES**
