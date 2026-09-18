# ADR-0003: Keep memory providers replaceable projections

- **Status:** Proposed
- **Date:** 2026-09-18
- **Deciders:** maintainer (final say) · proposing agent · reviewing agent(s)
- **PRD refs:** §13–§16, §30–§32, §48–§49
- **Research refs:** `research/01-mem0.md`, `research/03-graphiti.md`
- **Needs maintainer confirmation:** no

## Context

Mem0 offers automatic memory workflows but has retention, telemetry, and export limitations.
Graphiti offers useful temporal relationships but cannot preserve all canonical semantics. Neither
should own user truth or shape core interfaces.

## Decision drivers

- Zero-extra-key builtin path
- Portable canonical records and exact provenance
- Optional richer backends without dependency leakage

## Options considered

### A — Adopt one backend's API and schema as core

**+** Faster integration. **−** Lock-in and semantic loss.

### B — Narrow provider-neutral projection contract

**+** Replaceable and testable. **−** Backend-specific features need capability extensions.

## Decision

Choose **B**. Builtin memory is the Milestone 1 default, using canonical structured records plus
rebuildable SQLite indexes. `MemoryProvider` receives canonical Observation, CandidateMemory, Memory,
Fact, Evidence, and ReviewEvent/revocation records and supports capability discovery,
projection/upsert, lookup, deletion of its derived data, health checks, and full rebuild. Provider
output is specifically a tainted CandidateMemory proposal. Inference/extraction is a separate
`InferenceProvider` concern.

Provider output is never promoted directly to Profile truth; it becomes a candidate with evidence
and review state. Capability-specific operations use optional, typed extensions rather than widening
the portable base contract.

Mem0 is a Milestone 2 adapter after offline, telemetry, retention, and portability spikes. Graphiti
is a Milestone 3 graph projection after temporal/provenance spikes. Both maintain projection ledgers
when canonical IDs cannot be represented exactly.

## Consequences

- **Positive:** Provider choice cannot change Profile, evidence, host APIs, or vault ownership.
- **Negative / risks:** Lowest-common-denominator pressure; mitigated by capability extensions.
- **Follow-ups:** Define conformance fixtures and lifecycle/error semantics.

## Verification

Run one provider-neutral suite against builtin and fixture providers; rebuild from an empty backend;
assert identical accepted/quarantined/exposure views including revocation; switch providers without
canonical diffs; assert undeclared raw retention and telemetry are absent.
