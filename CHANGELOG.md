# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project will use
[Semantic Versioning](https://semver.org/) from its first release.

## [Unreleased]

### Added

- Conservative automatic Profile promotion (ADR-0020): an owner-pinned Memory with exact
  owner-declared CLI lineage, current permissions and no unresolved contradiction becomes one
  lineage-linked Profile Fact atomically. `aptuni profile refresh` handles older pins and
  `aptuni profile review list|accept|reject` provides retrospective owner review; host proposals
  and semantic guessing never cross this boundary.

- Preview-only local Mem0 2.0.20 projection commands: content-free status, exact fresh-generation
  rebuild from accepted canonical memories, and whole-store deletion. Inference and raw-conversation
  ingestion are disabled; Mem0/Ollama remain an optional extra.
- Obsidian vault source: `aptuni source add-obsidian` plus the ordinary sync pipeline. Only a
  directory holding `.obsidian/` is a vault; `.obsidian/`, `.trash/` and every attachment are
  excluded before any read. Each note contributes bounded topology (note name, folder, wikilink
  targets, tags, aliases, frontmatter property *names*) in `obsidian.locator@1`, and the Evidence
  excerpt is taken after the frontmatter block is removed, so property values never reach the
  locator, the excerpt or the search index (ADR-0017).

### Changed

- **Automatic promotion (ADR-0018).** An observation you make yourself through the CLI now becomes
  an active memory immediately instead of waiting in a review queue. It is marked
  `auto_promoted_pending_review` and reviewed retrospectively with
  `aptuni memory review list|accept|edit|reject|pin`. Host proposals, sensitive modules
  (`identity`, `relationships`, `behavior`) and anything contradicting a record still standing keep
  the typed confirmation. Reminders default to ten pending or fifteen days and are never blocking;
  `aptuni memory review policy --auto-promotion off` restores the old behaviour. `ReviewEvent`
  gains schema version 2, so a Vault written after this change cannot be read by 0.1.0.
- `aptuni memory list` no longer shows a memory that a correction has replaced.
- `aptuni evidence` and `aptuni source add-folder` now render source paths as bounded, escaped,
  delimited data rather than raw terminal text, so a crafted filename cannot forge an output row.
  The `--json` output of both commands is unchanged.
- Opt-in `aptuni search --hybrid` preview with deterministic rank-only fusion across SQLite/FTS and
  the fresh local Mem0 accepted-memory projection; default search and Context API remain lexical.

## [0.1.0] — 2026-09-21

First public pre-alpha release of the Milestone 1 personal context core.

### Added

- Profile Vault: canonical open-format records with temporal facts, corrections, retractions,
  full history, crash-safe writes, recovery, and `aptuni doctor`.
- Module permissions with independent `ingest` and `expose` switches.
- Folder source with incremental snapshots, candidate deltas, provenance and a review queue.
- GitHub source (Standard mode): bounded tree traversal, verified blob identity, exact-origin
  network policy, rate-limit and crash-safe replay.
- Bilingual (English/Chinese) SQLite FTS5 search projection, rebuildable at any time, with a ranked
  any-term fallback for task-shaped queries.
- Bounded Context API with L0–L4 progressive disclosure and response budgets.
- `aptuni-mcp`: read-only, permission-checked MCP server over STDIO with no network sockets.
- Claude Code and Codex adapter bundles with an informed, terminal-confirmed egress grant.
- Plugin catalog, Recipes (Starter Lite, Researcher), and the read-only `aptuni advise` Plugin
  Advisor in English and Simplified Chinese.
- Direct read-only MarginNote 4 source with native note/notebook identity and bounded concept
  evidence.
- Quarantined interaction-memory proposals with explicit accept, reject, and forget lifecycle.
- Owner-readable Profile export plus privacy inventory and digest-bound purge receipts.
- Guided setup with exact effect previews, resumable application, and grant-aware cancellation.
- Verified owner backup and restore that carries deletion history across machines.
- Versioned production retrieval evaluations and reproducible wheel/sdist supply-chain evidence.
- Repository-local source-provider, evaluation, license-audit, and release-readiness skills.

### Security

- Deletion-ledger torn-tail repair before append; unsafe-state failures never print tracebacks or
  content.
- Module-scoped host grants, network-denied MCP STDIO, conservative host-confinement reporting, and
  tracked-secret checks in the release gate.

[Unreleased]: https://github.com/ruihaomei/aptuni/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/ruihaomei/aptuni/releases/tag/v0.1.0
