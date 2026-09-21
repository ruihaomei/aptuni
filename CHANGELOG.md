# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project will use
[Semantic Versioning](https://semver.org/) from its first release.

## [Unreleased]

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
