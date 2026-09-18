# ADR-0012: Put interfaces behind application services and inference ports

- **Status:** Proposed
- **Date:** 2026-09-18
- **Deciders:** maintainer (final say) · proposing agent · reviewing agent(s)
- **PRD refs:** §11, §19–§20, §43, §48–§49
- **Research refs:** `research/04-mcp-sdk-and-hosts.md`, `research/06-codex-instructions.md`
- **Needs maintainer confirmation:** no

## Context

CLI, MCP, and hosts need one policy/transaction implementation. Extraction may be performed by a
host agent, local model, or future provider without making model execution a storage dependency.

## Decision drivers

- No interface bypass of policy, confirmation, retention, or transaction rules
- A usable Core API independent of MCP
- No required model/API key for builtin operation

## Options considered

### A — Each interface calls repositories/providers directly

**+** Fewer layers. **−** Duplicated security and inconsistent semantics.

### B — Versioned application services with a thin in-process SDK

**+** One use-case boundary and error model. **−** Requires deliberate command/query contracts.

## Decision

Choose **B**. Domain records and ports sit below application services for source configuration/sync,
observation/candidate lifecycle, review/confirmation, context retrieval, policy/privacy inventory,
purge, export, and health. The services own principal/scope lookup, action canonicalization/digest,
confirmation verification (ADR-0013), nonce-or-journal transaction, policy epoch checks, out-of-band
edit detection, unit of work, and public error codes. Confirmation guards only this service path;
host confinement, not core, is the control against a same-user shell (ADR-0013).

MVP exposes the services through a versioned Python in-process SDK. CLI and MCP are thin adapters and
never access Vault, indexes, credentials, or providers directly. REST/remote service is post-MVP and
requires S21.

`InferenceProvider` is a narrow proposal port: it receives a policy-approved bounded input and
returns typed, tainted Observation/CandidateMemory proposals with provenance and capability metadata.
The builtin no-model path accepts already structured host proposals. Inference never persists,
approves, promotes, or exposes records; absence/failure leaves canonical state unchanged.

## Consequences

- **Positive:** All interfaces share deterministic security and transactional behavior.
- **Negative / risks:** Service contracts are public API and require versioning/conformance tests.
- **Follow-ups:** Freeze command/query/error envelopes in S01/S04; draw them in the dependency graph.

## Verification

Run the same conformance cases through direct SDK, CLI, and MCP adapters; outcomes and error codes
match. Static/import tests prevent adapters from importing filesystem Vault implementations or
provider internals. A fake inference provider cannot persist or approve.
