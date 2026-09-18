# ADR-0009: License the project under Apache-2.0

- **Status:** Proposed
- **Date:** 2026-09-18
- **Deciders:** maintainer (final say) · proposing agent · reviewing agent(s)
- **PRD refs:** §33–§34, §40–§41
- **Research refs:** `research/01-mem0.md`, `research/02-llamaindex.md`, `research/03-graphiti.md`, `research/06-codex-instructions.md`
- **Needs maintainer confirmation:** yes — public repository license

## Context

The project aims for an open integration ecosystem. Key references and likely dependencies include
both Apache-2.0 and MIT projects. The repository needs an explicit license before public release or
outside contribution.

## Decision drivers

- Permissive commercial and community adoption
- Explicit patent grant and contribution clarity
- Compatibility with dependencies without copying their source

## Options considered

### A — MIT

**+** Short and familiar. **−** No explicit patent grant language.

### B — Apache License 2.0

**+** Permissive with explicit patent terms and NOTICE mechanism. **−** Longer obligations.

### C — No license until release

**+** Defers choice. **−** Others have no permission to use or contribute safely.

## Decision

Choose **B**, subject to maintainer confirmation. Dependencies remain under their own licenses.
Prefer dependencies/adapters over copied code; any direct copying needs per-file attribution review.
Maintain `THIRD_PARTY_NOTICES.md` and automated dependency-license checks before public release.

## Consequences

- **Positive:** Clear permissive terms and patent protection.
- **Negative / risks:** NOTICE/source-distribution obligations must be maintained.
- **Follow-ups:** Add the official license text only after maintainer approval; define contribution
  sign-off policy before accepting external changes.

## Verification

Repository license scanner; dependency inventory; source-copy audit; release checklist fails when
required notices or incompatible licenses are unresolved.
