# Plan 18 — M3 Public API and Plugin Platform TDD

## Goal

Ship `aptuni.api.v1`, a small in-process Python SDK and authorization contract that gives local trusted
extensions task-oriented access to permitted Profile, Memory, Context, Evidence and quarantined
memory proposals without exposing Vault, projection or application internals.

## Ownership and boundary

- Contract owner: `src/aptuni/api/`, ADR-0024, and all authorization/grant semantics.
- The API wraps `AptuniService`; it never reads the Vault or projection directly.
- V1 authorizes only clients declaring no external egress. In-process Python is trusted code, not a
  sandbox; remote/cloud execution must use the existing informed-egress MCP grant path.
- Owner review decisions, deletion, policy changes, source access and canonical Fact writes are not
  public v1 plugin capabilities.

## Contract

- Manifest contract `aptuni.plugin@1`: exact plugin id/version, API version, entry point, requested
  capabilities/modules, egress and retention declaration; unknown fields fail closed.
- Capabilities: `profile.read`, `memory.read`, `context.read`, `evidence.read`, `memory.propose`, and
  `memory.review.read`.
- Authorization binds an owner-created grant to the exact manifest digest, capability subset and module
  subset. Drift or missing grants fail closed.
- Public results are immutable versioned DTOs carrying budgets, Vault sequence, policy epoch,
  canonical IDs, provenance source IDs, trust, taint and review state.
- `memory.propose` uses the existing host-proposal path: protected content is rejected, ingest policy
  is enforced, and the result stays quarantined pending owner review.

## Failing-first matrix

- Strict manifest validation: unknown capability/module/field, duplicate requests, inconsistent
  retention, external egress, malformed id/version/entry point.
- Exact grant: narrowed capabilities/modules work; undeclared or ungranted access fails; manifest
  drift and partial IDs fail.
- Reads: exposed permitted data only; hidden modules stay hidden; evidence requires its own
  capability; stable provenance and budget metadata are present.
- Writes: idempotent quarantined proposal only; protected content and disabled ingest fail; no public
  accept/reject/pin/forget/Profile mutation method exists.
- Packaging: clean wheel imports `aptuni.api.v1`; scaffold imports only the public namespace.

## Exit evidence

- Focused tests, Ruff, strict mypy, public import/static-boundary checks, full repository gate,
  packaged scaffold smoke, independent contract/security review, ADR/docs/STATE/HANDOFF update, and
  a local checkpoint.
