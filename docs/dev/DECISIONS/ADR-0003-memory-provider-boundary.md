# ADR-0003: Keep memory providers replaceable projections

- **Status:** Accepted (2026-09-19, Gate 0 exit review 15)
- **Date:** 2026-09-18
- **Deciders:** maintainer (final say) · proposing agent · reviewing agent(s)
- **PRD refs:** §13–§16, §30–§32, §48–§49
- **Research refs:** `docs/research/upstream/mem0.md`, `docs/research/upstream/graphiti.md`
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

## Amendments

### 2026-09-19 — Gate 0 acceptance

Accepted. No spike contradicts it; S01 supports the canonical lifecycle with quarantined proposals. Mem0 (M2) and Graphiti (M3) stay gated by their own admission spikes; verification is an M1 conformance obligation.

### 2026-09-22 — Mem0 2.0.20 conditional admission

S10 admits Mem0 only as a disposable, local derived projection populated from accepted canonical
records with `infer=False`. Mem0-owned interaction inference is rejected because the exercised path
retains raw messages in its history store. Record-level `Memory.delete()` is not an Aptuni privacy
deletion primitive: the adapter must close and remove the entire managed provider root, then rebuild
the active projection from the Vault. The adapter must force telemetry off before importing Mem0,
keep every provider path inside one managed root, expose the limitation through capabilities and
health, and never treat Mem0 enumeration or history as a portable backup. S10 Review 52 is
**APPROVE WITH NON-BLOCKING NOTES**.

### 2026-09-22 — Rebuild-only preview adapter

The first production adapter is deliberately narrower than the original generic upsert/delete
shape. It projects only current accepted canonical `Memory` records, writes a fresh generation,
checks exact public enumeration, closes the provider, and atomically selects that generation.
Revocation and privacy deletion never call Mem0 record deletion; they invalidate the whole managed
root and require a canonical rebuild. The optional `mem0` extra pins `mem0ai==2.0.20` and
`ollama==0.6.2`; neither is part of the default installation. Activation remains an explicit preview
command and is not selected by setup, Advisor recommendations, or Recipes. Only a plain loopback
Ollama endpoint is accepted, Aptuni never pulls a missing model, and telemetry is disabled before
the first Mem0 import.

### 2026-09-22 — Read path for the opt-in hybrid preview

The Mem0 provider boundary gains one read-only method, `Mem0Projection.search`, and a matching
`search` member on the `Mem0Client` Protocol. It returns canonical Memory IDs plus a diagnostic
score and never returns provider text. The rebuild-only write boundary, the inference ban and
whole-store-rebuild deletion are unchanged. The retrieval semantics, fusion contract and exposure
rechecks are specified in ADR-0004's 2026-09-22 amendment.
