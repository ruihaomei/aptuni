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
| [ADR-0001](ADR-0001-canonical-vault-and-temporal-facts.md) | Make the open-format vault canonical | Accepted |
| [ADR-0002](ADR-0002-mvp-package-and-plugin-boundaries.md) | Start with one distribution and explicit plugin activation | Accepted |
| [ADR-0003](ADR-0003-memory-provider-boundary.md) | Keep memory providers replaceable projections | Accepted |
| [ADR-0004](ADR-0004-sqlite-retrieval-projection.md) | Use SQLite as the builtin retrieval projection | Accepted |
| [ADR-0005](ADR-0005-mcp-tools-and-progressive-disclosure.md) | Make MCP tools the portable agent baseline | Accepted |
| [ADR-0006](ADR-0006-source-snapshots-and-candidate-deltas.md) | Ingest immutable snapshots through candidate deltas | Accepted |
| [ADR-0007](ADR-0007-permissions-retention-and-telemetry.md) | Enforce privacy policy before persistence and exposure | Accepted |
| [ADR-0008](ADR-0008-cross-host-development-relay.md) | Put cross-host relay state in the repository | Accepted |
| [ADR-0009](ADR-0009-project-license.md) | License the project under Apache-2.0 | Accepted |
| [ADR-0010](ADR-0010-retention-destruction-and-restore.md) | Model retention, destruction, and restore across every copy | Accepted |
| [ADR-0011](ADR-0011-canonical-interaction-memory-lifecycle.md) | Keep the interaction-memory lifecycle canonical | Accepted |
| [ADR-0012](ADR-0012-application-services-and-inference-boundary.md) | Put interfaces behind application services and inference ports | Accepted |
| [ADR-0013](ADR-0013-honest-host-trust-boundary.md) | Treat shell-capable hosts as inside the trust boundary; require host confinement | Accepted |
| [ADR-0014](ADR-0014-plugin-catalog-recipes-and-advisor.md) | Describe plugins and Recipes as bundled TOML and advise without side effects | Accepted |
| [ADR-0015](ADR-0015-marginnote4-local-source.md) | Read MarginNote 4 directly and store a knowledge digest, not its text | Accepted |
| [ADR-0016](ADR-0016-owner-backup-format-and-ledger-location.md) | Make the owner's backup a verified format and keep the deletion ledger in the Vault | Accepted |
| [ADR-0017](ADR-0017-obsidian-vault-source.md) | Read an Obsidian vault as topology, not as a folder of Markdown | Accepted |
| [ADR-0018](ADR-0018-automatic-promotion-and-retrospective-review.md) | Promote stable memories automatically and review them retrospectively | Accepted |
| [ADR-0019](ADR-0019-github-deep-authored-activity.md) | Model GitHub Deep as an additive authored-activity source | Accepted |
| [ADR-0020](ADR-0020-conservative-memory-to-profile-promotion.md) | Promote only pinned owner-declared Memories into stable Profile Facts | Accepted |
| [ADR-0021](ADR-0021-official-notion-mcp-source.md) | Ingest explicitly scoped Notion entities through the official hosted MCP server | Accepted |
| [ADR-0022](ADR-0022-content-free-longitudinal-dogfooding.md) | Measure longitudinal quality without retaining evaluation content | Accepted |
| [ADR-0023](ADR-0023-obsidian-owner-interface.md) | Keep the Obsidian owner interface behind a local versioned bridge | Accepted |
| [ADR-0024](ADR-0024-versioned-public-developer-api.md) | Expose task-oriented extensions through a versioned least-privilege SDK | Accepted |
| [ADR-0025](ADR-0025-explicit-agent-activation.md) | Keep Agent personalization OFF until a canonical activation intent is invoked | Proposed |
| [ADR-0026](ADR-0026-top-down-portable-learning-context.md) | Make the portable verified learning context the Top-Down Learning continuity layer | Accepted |
| [ADR-0027](ADR-0027-owner-source-removal.md) | Let the owner remove an approved source by revoking it and retracting its evidence | Accepted |
<!-- ADR-INDEX:END -->
