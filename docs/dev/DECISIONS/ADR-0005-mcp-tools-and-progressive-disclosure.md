# ADR-0005: Make MCP tools the portable agent baseline

- **Status:** Accepted (2026-09-19, Gate 0 exit review 15)
- **Date:** 2026-09-18
- **Deciders:** maintainer (final say) · proposing agent · reviewing agent(s)
- **PRD refs:** §18–§20, §36, §43, §48
- **Research refs:** `docs/research/upstream/mcp-sdk-and-hosts.md`, `docs/research/upstream/claude-code-instructions.md`, `docs/research/upstream/codex-instructions.md`
- **Needs maintainer confirmation:** no

## Context

MCP hosts expose different subsets of tools, resources, prompts, sampling, and elicitation. The
modern protocol is stateless and negotiates capabilities per request. Tool invocation is the common
documented surface across target hosts.

## Decision drivers

- Claude Code, Codex, Cursor, and Claude Desktop portability
- Minimal auto-injected L0 context and on-demand disclosure
- Explicit budgets, provenance, and permission enforcement

## Options considered

### A — Resources/prompts as the core API

**+** Natural browsing/UX. **−** Uneven host support and invocation behavior.

### B — Task-oriented tools as core; resources/prompts as enhancements

**+** Portable and testable. **−** Less native UX on some hosts.

## Decision

Choose **B**. The portable MCP contract is a small set of task-oriented, namespaced tools for L0
identity, scoped context retrieval, structured observation submission, candidate review, source
sync/status, and system health. Tools accept explicit module, time, provenance, and token/result
budgets and return bounded structured results with canonical IDs.

Read and write namespaces are separate and every tool has a risk class: pure read, bounded personal
read, reversible write, networked action, or destructive/permission action. Unknown actions deny.
Each configured host maps to a local principal with explicit scopes; model text, source content, MCP
annotations, and host-supplied labels are not authorization. Consequential actions require an exact
preview plus a single-use, expiring confirmation bound to principal, action digest, policy epoch, and
scope. Stale, replayed, or widened confirmations deny.

*Amended by ADR-0013 (2026-09-18):* MCP tools may request but never approve. Approval is terminal-only:
the user runs the core CLI review/purge subcommand, which renders the full preview. It guards the
application-service path only; unconfined same-user hosts are inside the trust boundary, and `doctor`
reports confinement as `not_in_effect` or `unverified`, never as proven. `observe` creates only a
quarantined, non-exposable candidate and cannot auto-promote.

For Vault-only actions, verified nonce consumption and mutation are one transaction. For purge,
provider, backup, or network effects, nonce consumption is atomic with an exact durable idempotent
operation journal; workers and receipts handle effects/partial failure. Retry uses the same intent and
requires new approval only if digest/scope changes.

Resources may expose only bounded, policy-mediated application-service views; never direct Vault
files, paths, database handles, or unfiltered indexes. They recheck canonical policy after hydration
and use the same principal, pagination, budget, redaction, audit, and epoch rules as read tools.
Prompts may provide host workflows. Neither is required for correctness. Sampling and elicitation
are optional adapter capabilities, never core dependencies. Start with local STDIO; Streamable HTTP
stays disabled until S21 defines authentication, authorization, origin/CSRF/rebinding, revocation,
and tenant boundaries.

Progressive disclosure preserves the PRD's L0–L4 vocabulary: L0 identity card; L1 context index;
L2 selected modules; L3 facts/memories; L4 evidence/raw-source expansion. A tool may combine bounded
layers but reports which layers it included. Hosts must not dump the vault into context.
All source-derived content is typed, tainted untrusted data and cannot authorize a mutation or be
spliced into instructions/tool descriptions.

Delivery of personal results to a host/model is `host_model_egress`. Strict local-only mode denies
L0–L4 to remote or unknown hosts; other modes require per-host/module informed consent. Adapter
metadata discloses operator/destination and transcript/cache retention/deletion as known, unknown, or
externally controlled.
Core policy alone assigns `proven_local`: Claude Code/Codex default to remote/unknown; elevation needs
a reviewed pinned builtin adapter/runtime and end-to-end model-execution egress evidence. Host/config
labels cannot elevate and drift revokes admission.

Budgets are portable conservative response units, not an exact promise about a host tokenizer. Core
accounts UTF-8 bytes plus fixed per-record/metadata overhead, applies deterministic ranking/tie-breaks,
and emits used/remaining units plus truncation markers. An adapter may provide a tokenizer for a
stricter host-specific ceiling, but can only reduce output.

## Consequences

- **Positive:** One reliable API and predictable context cost across hosts.
- **Negative / risks:** Host-specific features need adapters and capability probes.
- **Follow-ups:** Freeze tool names/schemas after conformance spikes; pin MCP SDK for reproducibility.

## Verification

Executable host matrix; schema snapshots; malformed/budget/permission tests; prove MCP/model text
cannot approve and a confined agent's approval attempt fails closed (an unconfined host is out of
scope, ADR-0013 item 8); ADR-0013 Verification cases;
unconfirmed calls and changed/replayed digests deny; candidates cannot auto-promote; test two
confirmers, pre/post journal crash, effect-before-receipt restart, and one-durable-intent/idempotent retry;
model-behavior injection probes remain defense in
depth rather than an authorization claim; test remote/unknown host denial in strict local-only mode;
forged caller, confused-deputy, and mid-request policy-change tests; budget assertions; STDIO
end-to-end smoke test; telemetry/network audit.

## Amendments

### 2026-09-19 — Gate 0 acceptance

Accepted. Pin MCP Python SDK 2.2.0 and protocol `2026-07-28`. Standard tool annotations are security-relevant host input (`readOnlyHint` changed Codex 0.153.4 behavior). The STDIO server runs socket-denied except CPython's internal AF_UNIX self-pipe. Real-host probes deferred from S04 are M1.4/S12 release gates (plan 00 §5 step 4).
