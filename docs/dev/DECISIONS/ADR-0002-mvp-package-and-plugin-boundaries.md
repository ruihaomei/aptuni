# ADR-0002: Start with one distribution and explicit plugin activation

- **Status:** Proposed
- **Date:** 2026-09-18
- **Deciders:** maintainer (final say) · proposing agent · reviewing agent(s)
- **PRD refs:** §11–§12, §35, §42–§43, §48–§49
- **Research refs:** `research/02-llamaindex.md`, `research/07-local-retrieval-and-packaging.md`
- **Needs maintainer confirmation:** no — temporary namespace fixed by S00; public brand remains later

## Context

The PRD requires independent integration contracts, but the MVP does not need a release topology
like LlamaIndex's hundreds of distributions. Python already provides package metadata and entry-point
discovery.

## Decision drivers

- Clear dependency direction without premature repository complexity
- Third-party extensibility and conformance
- Explicit trust, privacy, and activation decisions

## Options considered

### A — Separate distribution for every component immediately

**+** Strong physical isolation. **−** High release/test/versioning overhead before ecosystem demand.

### B — One distribution, internal provider boundaries, external entry-point seam

**+** Fast MVP with a real extension path. **−** Internal boundaries rely on tests and review.

### C — Framework-specific runtime registry

**+** Rich hooks. **−** Extra dependency and lifecycle surface without demonstrated need.

## Decision

Choose **B**. Ship one installable `src/` Python distribution for MVP. Keep `core` independent of
concrete sources, memory, retrieval, inference, host adapters, and interfaces. Builtins live in the
distribution but implement the same versioned contracts as external plugins.

External plugins are discovered with `importlib.metadata.entry_points`. Discovery does not activate
them. Activation is explicit in configuration and validates a versioned manifest containing ID,
category, contract version, capabilities, requirements, privacy/retention behavior, setup effort,
and maturity. Duplicate IDs, incompatible contracts, missing metadata, or import failures are
isolated and reported. A conformance suite is mandatory for every category.

An activated in-process plugin is trusted code with the process's privileges; a manifest is not a
sandbox. MVP activates only builtin or explicitly reviewed packages, records package/version/hash
and approval, injects narrow service ports instead of Vault objects or ambient secrets, and never
claims containment of malicious plugins. Untrusted community code requires a later isolation ADR.
Approval binds the manifest hash and the complete resolved lock/SBOM closure: every distribution's
name, version, artifact hash, source/index, relevant extras, and dependency edges. Drift anywhere in
that closure disables activation until renewed review/approval.

Split packages or a uv workspace only when components need independent releases, dependency
isolation, or owners.

For development, use distribution `personal-context-core` and import namespace
`personal_context_core` (S00). Treat both as temporary and keep them out of user-facing brand copy.

## Consequences

- **Positive:** Small install surface and fast iteration without closing the ecosystem seam.
- **Negative / risks:** Accidental imports can blur boundaries; use dependency checks.
- **Follow-ups:** Re-run collision/trademark review and plan any import migration before stable public
  API or release.

## Verification

Contract tests for builtins and a fixture third-party package; discovery/activation failure tests;
honest trust warning/approval records; import-boundary check; affected-component plus dependant test
selection. Change a transitive artifact and prove activation denies or requires renewed approval.
S02 proves failure isolation, not a security sandbox.
