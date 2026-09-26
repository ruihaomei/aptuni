# Review 70 — Beta Agent Activation Contract

**Date:** 2026-09-27
**Scope:** ADR-0025; canonical Profile/Memory/Full activation; activation-required MCP surfaces;
Claude Code and Codex native skills; task/session reset; live grant and module-policy revalidation;
the accepted capable-host transcript limitation; tests and user-facing Agent UX documentation
**Reviewer:** independent agent (`code-reviewer`)

## Findings

The first review blocked on four implementation defects and one product-contract ambiguity. OFF
still permitted memory proposals; Full lacked direct Fact/Memory/Evidence coverage; the static gate
was not clean; and the verification matrix omitted identity/review denial and live module narrowing.
Those defects were fixed test-first. OFF now denies identity, search, review and capture; task Full
directly covers all three record classes; grant revocation and module exposure changes are
revalidated live; and generated host bundles have no automatic personal-context hook.

The remaining ambiguity was not enforceable inside Core: a model-visible MCP server cannot prove a
human invoked a skill, and Aptuni cannot erase context already returned into a capable host's
transcript. The maintainer explicitly accepted the bounded contract on 2026-09-27. ADR-0025 and the
user documentation now say that OFF prevents new retrieval, capture and disclosure; manual-only
skills are UX safeguards rather than a security boundary; and strict transcript isolation requires
a new host task, chat or session. A documentation regression rejects stronger future claims.

No release-blocking findings remain.

## Verification

- Reviewer focused gate: 88 tests passed.
- Ruff and strict mypy: passed.
- Claude plugin validation: passed during the initial/review-remediation cycle.
- OFF denial, task Full, process reset, session disable, live module narrowing and live grant
  revocation regressions: passed.

**Verdict:** **APPROVE**
