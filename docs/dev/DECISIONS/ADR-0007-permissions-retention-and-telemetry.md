# ADR-0007: Enforce privacy policy before persistence and exposure

- **Status:** Proposed
- **Date:** 2026-09-18
- **Deciders:** maintainer (final say) · proposing agent · reviewing agent(s)
- **PRD refs:** §6, §14, §23, §27, §40, §52
- **Research refs:** `research/01-mem0.md`, `research/04-mcp-sdk-and-hosts.md`, `research/08-source-identities-and-deltas.md`
- **Needs maintainer confirmation:** no

## Context

The product handles highly personal data. A module may allow ingestion but forbid exposure. Some
upstream defaults retain recent messages or emit telemetry, which conflicts with the PRD.

## Decision drivers

- Raw interaction retention off by default
- Independent ingest/expose controls and explicit destruction
- No secrets or personal content in telemetry/logs

## Options considered

### A — Enforce policy only in UI or retrieval

**+** Minimal plumbing. **−** Alternate interfaces and backends can bypass policy.

### B — Central policy gate plus defense-in-depth checks

**+** Consistent across providers. **−** More explicit context and test cases.

## Decision

Choose **B**. Core owns a fail-closed policy service invoked before ingestion, persistence,
projection, retrieval, and exposure. Every module has independent `ingest_enabled` and
`expose_enabled`; disabling exposure does not delete data. Deletion is a distinct, explicit,
previewable action.

Raw conversation retention defaults to off. The normal path extracts a bounded structured
observation and discards raw content. Any exception is scoped by source, purpose, duration, and
storage location, and is visible to the user.

Policy also gates `network_egress`, `host_model_egress`, and `credential_use`. Local-only mode denies
all content egress, including L0–L4/MCP results to remote or unknown host models; content-free health
is allowed. Other modes grant exact provider/host, destination, module/data class, and disclose known
or unknown transcript/cache retention and deletion control. Configuration stores only secret references;
credentials are resolved from host/OS secret storage at use time and are least-scope/revocable.
Policy has a monotonic epoch. Retrieval binds results to it and rechecks immediately before exposure;
policy changes atomically invalidate or stale derived cards/caches.

Telemetry is off by default, including transitive dependency egress. Enabling it requires explicit opt-in and a schema showing every emitted
field; never emit vault content, prompts, file paths, identifiers, secrets, or query text. Logs use
one diagnostic/redaction boundary for URLs, headers, environments, exception chains, subprocess
output, paths, queries, and content. Support bundles are bounded and previewable. Plugins declare
network, key, retention, and telemetry behavior before activation.

## Consequences

- **Positive:** Policy remains valid across CLI, MCP, adapters, and optional providers.
- **Negative / risks:** Fail-closed behavior can reduce functionality; errors must be actionable.
- **Follow-ups:** ADR-0010 owns retention/purge/restore semantics; `THREAT_MODEL.md` owns trust
  boundaries and abuse cases.

## Verification

Policy matrix/epoch-race tests at every boundary; process-level offline network canary across all
builtins plus fake local/declared remote host tests (the canary does not claim host coverage);
telemetry destination/schema snapshots on dependency upgrades; diagnostic marker tests; secret
scanning; raw-message canary tests; ADR-0010 purge/restore marker tests.
