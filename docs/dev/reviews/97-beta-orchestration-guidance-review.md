# Review 97 — Consolidated Agent retrieval guidance

- **Date:** 2026-10-02
- **Scope:** working-tree guidance changes against `9520605` in
  `src/aptuni/adapters/manager.py`, `src/aptuni/mcp/server.py`,
  `tests/integration/test_activation_guidance.py`, ADR-0030's consolidated-retrieval
  amendment and `docs/dev/b10-continuation/original-e2e-grading.md`.
- **Policy:** AGENTS.md: block only for correctness, security/privacy, contract or
  milestone-exit defects. This approves the guidance checkpoint, not the b10 release.
- **Method:** scoped diff first; read activation implementation, ADR-0025/0030/0031,
  current relay/research records and Reviews 93–96. Used the code-review-excellence
  skill. No live Vault, private transcripts, source folders or unrelated untracked
  user items were read. Original-run observations were assessed from the sanitized
  grading report; their source traces were not independently regraded.

## Blocking findings

None remain in the corrected scoped diff.

**B1 — inaccurate OFF promise, corrected during review.** The initial text said a
task activation always “leaves the session OFF.” `ActivationController.activate`
preserves an already authorized Full session on task activation. A temporary,
synthetic Vault probe confirmed session Full → task Profile reports Full, permits
search and leaves memory-proposal availability unchanged. The corrected skill,
tool descriptions and ADR now state that task scope creates no session authority:
OFF stays OFF; previously enabled Full stays enabled. The new integration
regression verifies OFF task → session Full → task Full → successful search →
disable → refused search. No activation semantics were changed to accommodate the
wording.

## Non-blocking notes and release limits

1. **Host parity:** the added skill text assertions initially exercise only
   `claude=True`. The shared generator carries the same body for Codex, and the
   existing adapter tests cover its explicit-invocation metadata. Parameterizing
   the new text assertions over both host variants will protect future divergence.
2. **Guidance is not compliance evidence:** string assertions establish shipped
   instructions, not ordinary-prompt invocation, precise concept generation,
   grounded answers or a one-call product experience. Keep the fresh unseen E2E
   gate open, with positive and negative tasks, and regenerate installed bundles
   before claiming the guidance is active. The preserved harness's Full prefix
   cannot demonstrate autonomous activation. Provider exhaustion cannot count as
   a passing journey. No release approval follows from this review.

## Contract and evidence assessment

The scoped production diff changes instructions only. It does not change lexical
matching, ranking, schemas, budgets, grants, authorization guards or credential
filters. The guidance requires explicit activation, relevant granted modules,
quoted-data treatment, no scope escalation to escape refusals and grounded use of
study evidence. This is consistent with ADR-0025's accepted OFF-by-default
contract; enabling implicit ordinary-prompt activation would require a separate
policy amendment and review.

The minimal orchestration changes address the graded failures: relevance before
retrieval; one consolidated concept/module plan; usually 1–4 named concepts;
programme/role/project anchors instead of guessed courses; one justified alternate
term/language retry; and no proficiency or progress claims from mentions/titles.
The 4000-unit initial recommendation is within existing validated bounds and
changes no limit. The original report counts all ten runs, refuses to explain away
h01/h04's broad fragmented retrieval or h10's absent retrieval, and distinguishes
provider failure from unsupported concept-generation attribution. Its totals are
internally consistent (19 attempts, 15 successful, four refused; one pass with
note, nine failures).

## Verification

| Check | Result |
|---|---|
| `.tools/bin/uv run pytest tests/integration/test_agent_activation.py tests/integration/test_activation_guidance.py tests/integration/test_adapters.py -o addopts='' --tb=short` | 24 passed in 2.96 s on corrected diff |
| `.tools/bin/uv run ruff check src/aptuni/adapters/manager.py src/aptuni/mcp/server.py tests/integration/test_activation_guidance.py` | All checks passed |
| Synthetic temporary-Vault session Full → task Profile probe | Full preserved; search succeeds; proposal status remains available |

Full suite, strict mypy, relay/frozen evaluations, real-Vault post-purge checks and
fresh held-out product validation remain the implementing agent's release checks;
this narrow review does not substitute for them or re-review credential purge.

**Verdict:** **APPROVE WITH NON-BLOCKING NOTES**
