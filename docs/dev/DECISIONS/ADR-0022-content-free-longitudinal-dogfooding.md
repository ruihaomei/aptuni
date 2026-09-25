# ADR-0022: Measure longitudinal quality without retaining evaluation content

- **Status:** Accepted
- **Date:** 2026-09-23
- **Deciders:** maintainer (fixed M2 priority) · implementing agent · independent reviewer
- **Builds on:** ADR-0004, ADR-0005, ADR-0007, ADR-0010, ADR-0018, ADR-0020
- **Needs maintainer confirmation:** no; scoring and reset are explicit owner CLI actions

## Context

Frozen fixtures protect deterministic retrieval contracts but cannot show whether Aptuni becomes
useful on the maintainer's real authorized sources over time. A useful dogfood loop must retain
judgments and denominators across restarts without creating a second store of private queries,
context text or source content. One maintainer's measurements remain qualitative evidence, not a
population claim.

## Decision

Add an owner-only `aptuni evaluate` workflow over the ordinary Context API. `setup` reports
content-free readiness; `trial` returns context for immediate judgment while persisting only a
SHA-256 query digest, Vault sequence, canonical IDs and bounded context metrics; `score` records an
exact useful/noise partition; `capture` records content-free canonical lifecycle counts; `report`
computes denominated longitudinal metrics; and `reset` deletes the complete derived dataset.

State lives only under the private host state directory as bounded schema v2 JSON with mode
0700/0600, exact-field validation, same-directory atomic publication and schema-v1 additive
migration. It is neither canonical nor backed up. Any canonical purge removes the entire evaluation
root because IDs and labels can refer to purged records. Reset refuses unknown files or symlinks
rather than widening its deletion scope.

The report names retrieval usefulness/noise, traceable and unsupported useful records, useful
trials, context-unit efficiency, exposure violations, source updates/retractions, corrections,
supersession, promotion, review backlog and owner decisions. Trials use no privileged retrieval or
permission path. Raw query text, returned context, record statements, excerpts, source paths and
host output are never durable evaluation fields.

## Consequences

- Real longitudinal observations are restartable and directly tied to canonical IDs and Vault
  generations without copying source content.
- A query digest can still reveal equality and is therefore private derived state; privacy status,
  purge and explicit reset disclose and close that retention.
- Historical schema-v1 rows lack newer efficiency/source metrics and are marked unavailable rather
  than guessed; a same-generation capture can replace an unavailable snapshot with measured data.
- No automatic threshold or population-quality claim is derived from maintainer dogfooding.

## Verification

Test content-byte absence, exact field/type/bound validation, filesystem modes and symlink refusal,
schema migration, fresh-process lock order, concurrent-write rejection, ordinary exposure policy,
exact scoring partitions, promotion/correction/source-update metrics, purge invalidation, bounded
reset and the complete CLI journey. Record one content-free baseline on the maintainer's existing
authorized setup, then obtain independent privacy/deletion review and the full repository gate.

## Amendment — 2026-09-25 measuring the Evidence layer (schema v3)

Default Context is L3-only (ADR-0005), so a v2 trial could never measure a query that only source
Evidence answers. `aptuni evaluate trial --evidence` now calls the same ordinary Context path with
`include_evidence=True`; no privileged lane or permission is added. Schema v3 stores one
content-free boolean, `include_evidence`, per trial; v2 trials migrate as `false`, which is exact
because v2 could not request Evidence. `report` adds `retrieval.by_context_mode` with separate
`profile_memory` and `with_evidence` usefulness/noise denominators. Existing aggregate metrics are
unchanged; the report and state `schema_version` becomes 3, and `schema_version` must be an integer.
