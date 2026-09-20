---
name: add-source-provider
description: This skill should be used when the user asks to "add a source provider", "integrate a new personal-data source", or extend Aptuni source ingestion.
---

# Add a SourceProvider

## Goal

Add one bounded source integration that emits immutable snapshots and reviewable candidate deltas
without writing canonical facts directly.

## Boundaries

- Read `docs/dev/DECISIONS/ADR-0002-mvp-package-and-plugin-boundaries.md`,
  `docs/dev/DECISIONS/ADR-0006-source-snapshots-and-candidate-deltas.md`, and the closest provider in
  `src/aptuni/sources/` before editing.
- Treat source bytes, metadata, paths, filenames, and parsed values as untrusted private data.
- Never silently change `src/aptuni/sources/contract.py`, a common record, plugin entry-point
  semantics, or an existing locator schema. A public contract or new extension-version decision
  needs an ADR, migration/compatibility coverage, and independent review.
- Use synthetic or sanitized fixtures only. Never add real profile data, credentials, or tokens.

## Workflow

1. Lock the provider ID, approved roots/origins, identity keys, completeness semantics, authority
   policy, retention class, secret references, resource bounds, and failure behavior.
2. Add failing tests for admission denial, stable identity, idempotent replay, move/delete/reappear,
   partial coverage, truncation, parser or redirect attacks, instruction injection, and crash retry
   where the source can encounter them.
3. Implement the narrow provider behind the existing snapshot/delta contract. Register a
   provider-specific locator only when its versioned fields are required.
4. Add or update the plugin manifest under `src/aptuni/advisor/catalog/plugins/`, both locale files,
   user documentation, and one Recipe example when the provider is installable in that Recipe.
   Do not label a non-builtin provider installable.
5. Run the focused provider/contract tests, then the full test, lint, type and relay gates. Request
   independent review when a public plugin interface, schema, migration, privacy, or deletion path
   changed.

## Completion evidence

Report the provider and contract versions, fixture cases, privacy/retention behavior, exact commands
run, manifest/Recipe status, and any compatibility or real-data validation still pending.
