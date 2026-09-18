# Architecture Decision Records

Architecture decisions live here, not in chat history (PRD §37). Every agent (Claude Code, Codex,
community contributors' agents) must read the ADRs relevant to its task before editing code.

## Rules

1. **One decision per ADR.** File name: `ADR-NNNN-kebab-title.md`, numbered sequentially.
2. **Lifecycle:** `Proposed` → `Accepted` (after independent review + maintainer sign-off where
   flagged) → optionally `Superseded by ADR-XXXX` or `Deprecated`. Never delete an ADR.
3. **Accepted ADRs are immutable.** To change a decision, write a new ADR that supersedes it and
   update the old one's status line only. Typos/clarifications go in an `## Amendments` section
   with a date.
4. **Architectural contract changes require an ADR** (PRD §38/§40): public schemas, plugin
   contracts, Context API/MCP tool semantics, vault layout, new heavy dependencies, license policy.
5. Keep ADRs short (aim ≤ 150 lines). Link research notes instead of copying them.
6. Use [TEMPLATE.md](TEMPLATE.md).

## Index

| ADR | Title | Status |
|-----|-------|--------|
<!-- ADR-INDEX:START (keep sorted; one row per ADR) -->
| [ADR-0001](ADR-0001-canonical-vault-and-temporal-facts.md) | Make the open-format vault canonical | Proposed |
| [ADR-0002](ADR-0002-mvp-package-and-plugin-boundaries.md) | Start with one distribution and explicit plugin activation | Proposed |
| [ADR-0003](ADR-0003-memory-provider-boundary.md) | Keep memory providers replaceable projections | Proposed |
| [ADR-0004](ADR-0004-sqlite-retrieval-projection.md) | Use SQLite as the builtin retrieval projection | Proposed |
| [ADR-0005](ADR-0005-mcp-tools-and-progressive-disclosure.md) | Make MCP tools the portable agent baseline | Proposed |
| [ADR-0006](ADR-0006-source-snapshots-and-candidate-deltas.md) | Ingest immutable snapshots through candidate deltas | Proposed |
| [ADR-0007](ADR-0007-permissions-retention-and-telemetry.md) | Enforce privacy policy before persistence and exposure | Proposed |
| [ADR-0008](ADR-0008-cross-host-development-relay.md) | Put cross-host relay state in the repository | Proposed |
| [ADR-0009](ADR-0009-project-license.md) | License the project under Apache-2.0 | Proposed — confirmation needed |
| [ADR-0010](ADR-0010-retention-destruction-and-restore.md) | Model retention, destruction, and restore across every copy | Proposed |
| [ADR-0011](ADR-0011-canonical-interaction-memory-lifecycle.md) | Keep the interaction-memory lifecycle canonical | Proposed |
| [ADR-0012](ADR-0012-application-services-and-inference-boundary.md) | Put interfaces behind application services and inference ports | Proposed |
| [ADR-0013](ADR-0013-honest-host-trust-boundary.md) | Treat shell-capable hosts as inside the trust boundary; require host confinement | Proposed — maintainer accepted residual risk |
<!-- ADR-INDEX:END -->
