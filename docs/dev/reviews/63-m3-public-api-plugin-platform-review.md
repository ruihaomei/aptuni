# Review 63 — M3 Public API and Plugin SDK Platform

**Reviewers:** independent API-contract and plugin-security agents

**Date:** 2026-09-24

**Scope:** ADR-0024; `aptuni.api.v1`; `aptuni.plugin@1`; owner grants; privacy integration;
developer CLI/scaffold; Top-Down Learning flagship example

## Findings and remediation

The first passes blocked authority that survived revoke/purge in an already-connected client,
ambiguous empty grant subsets, forgeable public construction, post-filter Memory metadata leakage,
manifest language that implied unimplemented code activation, path/tamper weaknesses, incomplete
grant lifecycle operations, deterministic purge races, scaffold injection, capability incoherence,
and false foundation inference in the flagship example.

The remediation made the public constructor inaccessible without `connect`, rejects empty or
incoherent subsets, integrity-checks persisted plans and grants, confines storage with descriptor-
relative no-follow operations, and adds list/cancel/revoke plus expiring consumed previews. Memory
queries restrict canonical record types before retrieval and packing. The contract now explicitly
authorizes SDK clients only: Aptuni does not discover, import or execute third-party entry points.
The flagship narrows its manifest, filters negated evidence, and hashes the complete gap tuple.

Continuity review then found two race classes. Concurrent or interrupted apply could mint duplicate
authority, and revoke could interleave after a call's initial check. One deterministic grant
generation is now bound to each owner preview. Calls, apply, cancel, revoke and privacy cleanup use
one no-follow cross-process authorization lock; persisted authority is revalidated before return.
Crash recovery is covered for retry, cancel and expiry, and cancel reconciles a grant already
published by the interrupted action. Completed revoke/purge stops existing clients; an operation
already holding the lock completes before revocation completes.

The final independent contract review reproduced the focused tests and static gates and found no
remaining correctness, security, authorization-lifecycle or compatibility blocker.

**Verdict:** **APPROVE**
