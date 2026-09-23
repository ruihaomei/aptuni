# M2 Obsidian Human Interface — bounded TDD plan

## Outcome

Ship the smallest first-class local Obsidian workflow for inspecting Profile, Memory, Evidence,
recent changes, pending reviews and promotion state, then acting through existing canonical owner
services. Keep `source.obsidian` ingestion completely separate from `interface.obsidian`.

## Contract

- A versioned owner-only JSON bridge exposes one bounded snapshot plus `show evidence`; it never
  scans the Obsidian vault, changes source scope or creates a second canonical store.
- Accept/Edit/Reject/Pin call the existing retrospective-review services. Forget keeps the existing
  preview/digest/confirm protocol. Unsupported record/action combinations fail closed.
- The desktop plugin uses `execFile` with argument arrays, never a shell, never stores returned
  Profile/Memory/Evidence content, and renders external text through DOM text APIs only.
- A local installer copies three fixed bundled assets into an exact `.obsidian/plugins/aptuni`
  directory, refuses non-vaults, symlinks and existing targets, and never enables the plugin for the
  owner.
- The plugin reads Aptuni owner data; this is local display, not host/model egress. Module exposure
  flags constrain agents, not the owner interface. Every mutation still enforces ingest/review and
  current-record rules in the application layer.

## Red → green sequence

1. Application tests for bounded Profile/Memory/Evidence/Recent/Pending views, promotion state and
   evidence lineage over facts, promoted facts and memories.
2. Action tests for type/action allowlists, idempotent accept/reject/pin, edit correction, Profile
   accept/reject and two-phase Forget with stale-digest refusal.
3. JSON CLI tests for snapshot/evidence/action and untrusted human rendering.
4. Installer/static plugin tests for exact assets, no overwrite/symlink traversal, `execFile`
   argument arrays, no shell/`innerHTML`, no durable content cache and required flows.
5. Catalog/i18n/README docs, independent public-plugin/security review, full gate and local
   checkpoint. Do not add backlinks, Canvas, editing notes, graph views or automatic installation.

## Verification

Run focused interface/review/privacy tests during implementation, then full pytest, Ruff, strict
mypy, relay, supply-chain and frozen evaluations. Obtain independent review because this is a
public plugin interface with canonical mutations and local process execution.
