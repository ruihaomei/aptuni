# Aptuni 0.1.0 release-candidate review

**Reviewer:** independent Claude Code 2.1.87 / Claude Haiku, non-persistent read-only temporary clone

## Scope

The reviewer inspected the 0.1.0 version and metadata surfaces, changelog, citation and security
policy, bilingual public installation instructions, compatibility matrix, locked dependency state,
the tag-triggered PyPI OIDC workflow, its supply-chain checker, and the checker regressions.

## Evidence assessed

- 459 tests plus 47 subtests, 35 developer checks, ruff, strict mypy and relay passed.
- Lock, notice, tracked-secret and workflow checks passed; the locked vulnerability audit reported
  no known vulnerabilities and the frozen evaluation passed.
- Two fixed-epoch offline builds were byte-identical. Wheel and sdist legal-file checks passed, as
  did isolated import/version, CLI and MCP EOF smokes.
- The workflow is tag-only, immutable-action-pinned and read-only by default. The build job has no
  OIDC authority; only the isolated `pypi` environment publish job receives `id-token: write`.

## Findings

No blocking or non-blocking findings were reported. Package version, Python requirement, license,
public URLs and install commands agree on Aptuni 0.1.0.

**Verdict:** **APPROVE**
