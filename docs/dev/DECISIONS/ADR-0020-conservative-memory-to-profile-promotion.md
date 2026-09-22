# ADR-0020: Promote only pinned owner-declared Memories into stable Profile Facts

- **Status:** Accepted
- **Date:** 2026-09-22
- **Deciders:** maintainer (priority and invariants) · implementing agent · independent reviewer
- **PRD refs:** §3, §14–§16, §21, §23, §46
- **Builds on:** ADR-0001, ADR-0011, ADR-0013, ADR-0018
- **Needs maintainer confirmation:** no — this is the conservative implementation of the explicit
  M2 priority; any broader inference policy remains a separate decision.

## Context

ADR-0018 closes `CandidateMemory → Memory` but deliberately leaves `Memory → Fact` separate.
Canonical data currently has no calibrated semantic equivalence model, repeat-observation counter,
or trustworthy confidence estimator. Treating age, string similarity, or a model score as stability
would silently invent a weaker policy and could turn transient interaction material into Profile.

The ledger does have one strong, explicit stability signal: the owner can pin a reviewed Memory.
It also retains the exact Candidate and Observation lineage, permissions, contradictions,
supersession, provenance, temporal fields, and review events needed for a fail-closed decision.

## Decision

### 1. Eligibility is conjunctive and deliberately narrow

A Memory is promoted only when all of these hold in one stable canonical snapshot:

1. it is current: not revoked/rejected and not superseded;
2. the owner has appended a `pin` event targeting it;
3. its Candidate exists and every supporting record is an Observation with
   `trust="user_declared"` and episode `cli`;
4. no unresolved Candidate currently contradicts it;
5. its module currently has both `ingest_enabled` and `expose_enabled`;
6. ADR-0018 automatic promotion is enabled; and
7. no historical Fact already names it in `memory_ids`.

Pinning is therefore necessary but not sufficient. Host-proposed, source-inferred, contradictory,
hidden, disabled, replaced, or already-promoted material never crosses this boundary. There is no
age, frequency, embedding, or language-model shortcut.

### 2. Promotion is atomic and preserves exact lineage

The policy appends, in one Vault commit:

- `ReviewEvent(decision="promote", actor="policy_auto", target_id=<memory id>)`; and
- one `Fact` with the exact bounded Memory statement, module, provenance and temporal bounds,
  `memory_ids=(<memory id>,)`, and its source evidence ids.

The Fact uses the deliberately generic `type="profile.promoted_memory"`, `subject="self"`, and
`predicate="stable_memory"`; `object` is null. These labels express only the transition and do not
infer expertise, identity, preference strength, or a new time range. Trust remains `system`, review
status remains `auto_derived`, and the Fact is active immediately as PRD §16 requires.

`ReviewEvent.promote` now has two type-safe meanings: targeting a Candidate admits a Memory
(ADR-0018); targeting a Memory admits exactly one Fact whose `memory_ids` contains that Memory.
The target prefix and linked record type make the transition unambiguous. No schema field widens.

### 3. Review state is derived and history is append-only

A policy-promoted Fact is `auto_promoted_pending_review` until a user event targets the Fact.
`accept` settles it. `reject` withdraws the Fact from exposure while preserving it, its source
Memory, evidence, and every event. Repeated decisions are idempotent. Fact review never mutates or
withdraws the source Memory. Rejection is not an invitation to recreate the same claim: any
historical promoted Fact permanently makes refresh a no-op for that Memory.

### 4. Trigger and recovery

Pinning an eligible Memory creates its promotion records in the same commit, so a crash cannot
leave a pin without the resulting Fact. `aptuni profile refresh` applies the same deterministic
policy to older pinned Memories and is idempotent. This command is also the explicit daily/periodic
hook; read-only commands do not acquire a hidden write side effect.

### 5. Interface and permission boundary

Owner CLI gains `aptuni profile refresh` and `aptuni profile review list|accept|reject`. MCP is
unchanged: it cannot pin, promote, accept, or reject a Profile Fact. Promotion requires both ingest
and expose permission to prevent either hidden canonical growth or exposure widening.

## Consequences

- Profile formation is slower than Memory formation and cannot be driven by a host proposal,
  source mention, elapsed time, similarity score, or opaque model confidence.
- The first policy is intentionally low recall: stable but unpinned memories remain Memories. Real
  longitudinal dogfooding may justify a future calibrated criterion, but only through a new ADR.
- A pinned Memory created by an older build needs one `profile refresh`; future pins are atomic.
- Review and rejection remain cheap, attributable, reversible, and history-preserving.

## Verification

Test every eligibility clause independently; promotion/pin atomicity; refresh and decision
idempotence; invalid target/link combinations; disabled ingest/expose; unresolved contradiction;
superseded/revoked Memory; context/export visibility before and after rejection; provenance,
temporal and `memory_ids` preservation; no MCP mutation path; and 0.1.0 fail-closed readability.

## Amendments

### 2026-09-22 — Review 59 acceptance

Accepted after the independent review's incremental/full-validation blockers were remediated.
Canonical validation binds the exact copied claim and one transition event at commit time; a
rejected historical promoted Fact cannot be silently recreated by refresh.
