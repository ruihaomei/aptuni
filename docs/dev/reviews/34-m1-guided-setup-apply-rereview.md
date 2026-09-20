# Review 34 — M1 guided setup apply re-review

**Date:** 2026-09-20

**Reviewer:** independent correctness, security and privacy review agent

**Scope:** the current guided-setup worktree after remediation of Review 33 B1–B6 and its
follow-up crash/recovery findings. The re-review focused on the one-confirmation boundary, exact
source and host effects, resumability, adapter-bundle repair, grant ownership, cancellation, and
the plan-02 acceptance journey.

## Validation

- `.tools/bin/uv run pytest tests/integration/test_setup_apply.py -q`: **51 passed**.
- `.tools/bin/uv run pytest`: **passed**.
- `.tools/bin/uv run ruff check .`: **passed**.
- `.tools/bin/uv run mypy src`: **passed**.
- `git diff --check`: **passed**.
- A reproduced mid-bundle failure resumed to `complete` and restored the full expected Codex
  bundle.
- Apply revalidated the catalog and recommendation, then rendered the complete advisor preview and
  the exact setup plan before accepting terminal `APPLY`.
- The durable pre-effect ownership claim remained correct when a repair pass observed an existing
  grant; cancellation did not acquire ownership of reused grants.

## Findings

No remaining correctness, security, privacy, or contract findings. Review 33 remains the historical
record of the blocked implementation; this review supersedes its verdict after the findings were
remediated and independently reproduced.

**Verdict:** **APPROVE**
