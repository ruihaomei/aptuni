# ADR-0024: Expose task-oriented extensions through a versioned least-privilege SDK

- **Status:** Accepted
- **Date:** 2026-09-24
- **Deciders:** maintainer (requested platform) · implementing agent · independent reviewer
- **Builds on:** ADR-0002, ADR-0005, ADR-0007, ADR-0012, ADR-0013
- **Needs maintainer confirmation:** no for the bounded local/no-egress v1 contract

## Context

Aptuni has application services and several versioned interface contracts, but extension developers
still have to know internal modules. Exposing those services or canonical models directly would make
the Vault layout, temporal implementation and projections accidental public API.

## Decision

Publish `aptuni.api.v1` as the only supported Python extension namespace. It offers task-oriented
Profile, Memory, Context and Evidence reads plus quarantined memory proposals and pending-review
reads. Every operation is capability- and module-gated, delegates to the existing application
service, and returns immutable v1 DTOs with provenance, taint, policy epoch and Vault sequence.

An `aptuni.plugin@1` manifest requests capabilities; it grants none. Owner authorization writes a
private grant bound to the exact manifest digest and a narrowed capability/module set. V1 accepts
only `egress = ["none"]`. Remote/model/cloud clients use the existing informed-egress MCP path until
a separately reviewed isolation/egress contract exists.

The SDK contains no direct canonical Fact write, source access, policy change, deletion, owner review
decision, Vault or projection method. `memory.propose` reuses the host-proposal lifecycle and remains
quarantined. SDK calls and grant mutation share one cross-process authorization lock and revalidate
the persisted grant before returning. Apply is single-effect and crash-idempotent. A completed revoke
or privacy purge therefore takes effect for already-connected clients; an operation already holding
the lock completes before revocation completes.

This decision defines SDK-client authorization, not plugin activation. Aptuni v1 does not discover,
import or execute the declared entry point. A host may load reviewed code and pass it the returned
client. In-process Python remains trusted same-user code; before Aptuni itself can activate external
entry points, ADR-0002's source and complete dependency-closure review must be implemented in a
separately reviewed contract.

## Compatibility policy

`aptuni.api.v1` and `aptuni.plugin@1` are additive-only within major version 1. Removing or changing
field meaning, capability semantics or error codes requires `v2`. New optional fields/capabilities
may be added in v1 only when old consumers continue to validate and behave unchanged. Internal
modules outside `aptuni.api` have no compatibility promise.

## Verification

Strict manifest/grant tests, public DTO contract tests, permission/privacy adversarial tests, a
clean-wheel import/scaffold smoke, and a flagship extension that imports only `aptuni.api.v1`.

## 2026-09-27 amendment — plugin-declared Agent context

`aptuni.plugin@1` adds an optional `[aptuni]` declaration with disjoint `required` and `optional`
capability lists. It is an ergonomic declaration over the existing capability vocabulary and owner
grant; it is not a second permission system. A grant must contain every required capability, may
omit any optional capability, may never exceed their union, and remains narrowed independently by
exact modules. The owner preview distinguishes mandatory dependencies from the optional authority
being granted. Capability dependencies are closed within `required`: required `evidence.read`
therefore also requires `context.read` to be required, never merely optional.

Legacy `capabilities = [...]` manifests keep their exact digest and grant semantics. A manifest uses
either that legacy field or `[aptuni]`, never both. Stored v1 plans and grants without the additive
`required_capabilities` field remain valid; the field participates in integrity hashing only when
non-empty.

Plugin invocation is task/call scoped: reviewed plugin code queries the public client under its
live exact grant, so the user does not separately activate Profile/Memory/Full. This does not widen
the Agent session activation contract and does not add entry-point discovery or execution to Core.
Every public call still revalidates the grant, module exposure and privacy boundary.
