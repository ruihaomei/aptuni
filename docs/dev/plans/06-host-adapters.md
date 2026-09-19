# Milestone 1 Slice 6 — Claude Code and Codex Adapter Bundles

**Status:** Active
**Decision basis:** ADR-0005, ADR-0007, ADR-0008, ADR-0013, S04, and bounded MCP Slice 5.

## User-visible capability

- `aptuni adapter plan HOST --module M --allow-host-model-egress` creates a bounded, inspectable
  pending plan with operator/destination/retention disclosure.
- `aptuni adapter apply ACTION_ID` is the only apply entry point; it shows the full preview and asks
  in the terminal before creating an Aptuni-owned grant and host bundle.
- Bundles register `aptuni-mcp --grant GRANT_ID`. Claude also receives a bounded SessionStart L0
  command; Codex receives static on-demand MCP guidance because an equivalent automatic L0 mechanism
  is not proven.

## Acceptance

1. Exact action IDs only; cancel/no leaves no grant or bundle; apply is idempotent.
2. Grants live outside source content with mode 0600 and bind host principal, exact scopes/modules,
   remote/unknown host class, operator/destination, retention disclosure and egress consent.
3. MCP ignores tool/env claims and loads only an exact persisted grant ID. Config cannot assign
   `proven_local`.
4. Generated JSON/TOML is deterministic, contains no personal content or secret, and points only to
   the installed interpreter/module entry points.
5. Adapter status is `unverified` by default and never `confined`; visible unsafe project settings
   may lower it to `not_in_effect` in later hardening without blocking bundle generation.

## Exclusions

No automatic edits to host-global/project config, credentials, write tools, or claim of confinement.
Guided placement/rollback and remaining real-host S12 probes remain the next interface slice.
