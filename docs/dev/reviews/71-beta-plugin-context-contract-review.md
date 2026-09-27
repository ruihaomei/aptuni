# Review 71 — Beta Plugin Context Declaration Contract

**Date:** 2026-09-27
**Scope:** additive `aptuni.plugin@1` required/optional context declaration; owner grant planning,
integrity and preview; legacy manifest/grant compatibility; privacy and live revocation; Top-Down
Learning declaration and optional memory-capture journey
**Reviewer:** independent agent (`code-reviewer`)

## Findings

The first review found one blocking least-privilege defect: a manifest could declare
`evidence.read` required but its `context.read` dependency optional. The manifest validated, but an
owner could not actually withhold the supposedly optional dependency. Validation now closes
dependencies inside the required set, and an adversarial regression rejects that declaration.

The final contract preserves the exact legacy manifest digest and loads stored v1 plan/grant files
that predate `required_capabilities`. New grants must contain all required capabilities, may omit
optional capabilities, bind the required set into integrity metadata when non-empty, and show the
distinction in the owner preview. Existing module, no-egress, privacy, revocation and live policy
boundaries remain in force. Top-Down Learning uses only the public API; its learning journey works
without optional memory capture, which fails closed when withheld.

No release-blocking findings remain.

## Verification

- Focused manifest/public API/Top-Down/privacy gate: 47 passed.
- Ruff and strict mypy: passed.
- Exact legacy digest and old stored plan/grant regressions: passed.

**Verdict:** **APPROVE**
