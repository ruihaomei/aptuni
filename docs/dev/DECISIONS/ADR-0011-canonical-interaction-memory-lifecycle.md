# ADR-0011: Keep the interaction-memory lifecycle canonical

- **Status:** Proposed
- **Date:** 2026-09-18
- **Deciders:** maintainer (final say) · proposing agent · reviewing agent(s)
- **PRD refs:** §13–§16, §23, §46, §52
- **Research refs:** `research/01-mem0.md`, `research/03-graphiti.md`
- **Needs maintainer confirmation:** no

## Context

Raw interactions are discarded by default, but their structured lifecycle must survive backend
replacement: Interaction → Observation → Candidate Memory → Memory → optional Profile Fact.

## Decision drivers

- No canonical memory hidden inside a derived provider
- Fast memory formation but slow, reviewable Profile promotion
- Idempotent retries, contradiction history, forget, and privacy purge

## Options considered

### A — Encode every stage as an overloaded Fact

**+** Fewer record types. **−** Conflates quarantine, reusable memory, and stable Profile truth.

### B — Typed canonical records sharing one envelope

**+** Explicit lifecycle with common provenance/temporal/policy semantics. **−** More schemas/links.

## Decision

Choose **B**. A versioned canonical envelope supplies `id`, `schema_version`, `recorded_at` (system
time), valid-time bounds, module, provenance/episode, trust/retention, policy epoch, confidence,
review state, and forward lifecycle/supersession links. Reverse links are derived.

- `Observation`: bounded structured statement from a source/interaction. It is quarantined and never
  exposable by itself; `idempotency_key` makes identical submission retry-safe.
- `CandidateMemory`: proposal derived from one or more Observation/Evidence IDs, with contradiction
  links and proposed scope. It remains quarantined until a review decision.
- `Memory`: accepted reusable context referencing its candidate and evidence. In MVP only the
  ADR-0013 confirmation can accept it; later auto-promotion needs a new accepted ADR.
- `Fact`: slower stable Profile claim promoted from Memory and/or Evidence, preserving all lineage.
- `ReviewEvent`: append-only accept/reject/revoke/promote decision with actor, action digest, policy
  epoch, rationale code, and timestamp; no source/model content can act as the reviewer.

Canonical writes are Observation/Candidate/Memory/Fact/ReviewEvent append or supersession. A
`MemoryProvider` only projects these records. Provider output returns a CandidateMemory proposal;
it never writes Memory or Fact directly. Rebuild from the Vault reproduces the accepted memory view.

Contradictions create candidates and explicit forward links; they do not overwrite. `forget` appends
a revocation ReviewEvent and makes Memory ineligible for exposure while preserving history. Privacy
purge follows ADR-0010 and removes authorized content/links across managed copies. Rejection and
revocation are idempotent and never expose quarantined content.

## Consequences

- **Positive:** Builtin/Mem0/Graphiti can change without losing lifecycle or review history.
- **Negative / risks:** More cross-record invariants and migrations.
- **Follow-ups:** S01 freezes all five record schemas and valid transitions before M1.1.

## Verification

Golden transitions cover retry, rejection, acceptance, contradiction, revocation, promotion,
provider rebuild, retention expiry, and purge. Invalid/missing/cyclic links fail. Hash the canonical
view, rebuild every provider, and assert the same accepted/quarantined/exposure sets.
