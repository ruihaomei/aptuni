# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project will use
[Semantic Versioning](https://semver.org/) from its first release.

## [Unreleased] — Milestone 1 (pre-alpha)

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

### Security

- Deletion-ledger torn-tail repair before append; unsafe-state failures never print tracebacks or
  content.
