# M1 Interaction-Memory Review Remediation

- **Date:** 2026-09-20
- **Responds to:** `26-m1-memory-lifecycle-review.md`
- **Status:** all blocking findings fixed test-first; focused re-review requested

| Finding | Remediation |
|---|---|
| B1 nonce was post-hoc and never consumed | Action previews now issue a random mode-0600 nonce with a ten-minute expiry. The digest binds action, target, statement, module, current policy epoch, nonce and expiry. The ReviewEvent commits that nonce atomically with the Memory/decision and is the authoritative single-use consumption record. Tests cover expiry, stale epoch, wrong digest, canonical nonce recording and replay. |
| B2 `memory forget` revoked immediately | Forget now renders statement, module, origin, effect, nonce, expiry and digest; it requires typed `FORGET` or the exact digest before appending a revocation. Cancellation and exact retry are tested end to end. |
| B3 idempotency key was global and unbound | Stored keys are namespaced by principal/episode. Reuse succeeds only for the same module, normalized `about` and statement; a different payload returns `idempotency_conflict` without an existing candidate ID. Cross-principal, cross-module, same-payload retry and conflict cases are tested. A concurrent identical writer re-reads and returns the winner. |
| B4 host proposal stored obvious credentials/raw control text | A fixed pre-commit host-only policy rejects recognizable access keys/tokens/private keys, credential assignments, transcript role prefixes and instruction-shaped control text with one content-free error. Tests prove representative rejected bytes never enter a Vault segment. The MCP description and ADR state the enforceable narrow guarantee rather than claiming complete secret detection. |

Additional coverage binds the adapter plan digest to the opt-in `memory.propose` scope and verifies
that the persisted grant carries it. Owner-authored CLI observations remain separate from the
untrusted MCP content filter.

Validation before re-review: focused memory, adapter, MCP and export suites pass; Ruff and strict
mypy pass.
