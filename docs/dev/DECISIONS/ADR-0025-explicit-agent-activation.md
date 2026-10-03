# ADR-0025: Keep Agent personalization OFF until a canonical activation intent is invoked

- **Status:** Accepted
- **Date:** 2026-09-27
- **Deciders:** maintainer (requested Beta UX) · implementing agent · independent reviewer
- **Builds on:** ADR-0005, ADR-0007, ADR-0013, ADR-0024
- **Needs maintainer confirmation:** yes — explicitly accepted on 2026-09-27

## Context

The first Claude Code adapter injected a small identity card at every SessionStart, while Codex
offered on-demand MCP tools. The Beta product direction instead requires ordinary Agent tasks to
start Aptuni-OFF. Literal mention or slash syntax cannot be canonical because host-native extension
mechanisms differ. A model-visible MCP server also cannot authenticate that a tool call originated
from a human skill invocation, and Aptuni cannot erase information already delivered to a capable
host. The maintainer explicitly accepted this enforceable boundary on 2026-09-27.

## Decision

Core defines three activation intents: `aptuni.profile`, `aptuni.memory`, and `aptuni.full`.
Profile retrieves relevant current exposed Facts; Memory retrieves relevant current exposed
Memories; Full retrieves relevant permitted Facts, Memories and minimized Evidence. Every path
continues to use ordinary retrieval relevance, exact host grants, module policy, exposure checks,
provenance and response-unit budgets. Full is progressive disclosure, never a Vault dump.

Task scope is the default. A task activation performs one bounded retrieval and creates no durable
or session authorization state. Only `aptuni.full` may be explicitly activated for the current host
session. Session state lives only in the MCP server process, starts OFF, can be inspected without
personal content, and can be disabled. A new process starts OFF. This state never widens the
persisted host grant and live permission checks still run on each retrieval.

OFF means no new Profile, Memory or Evidence retrieval, no new Aptuni memory capture, and no further
Aptuni disclosure through the activation-required interface until it is reactivated. Task scope
controls only new Aptuni disclosure; it cannot erase or revoke personal context that the external
host has already placed in its conversation transcript. Users who require strict isolation between
personalized and non-personalized work must start a new host task, chat or session.

The adapter marks activation skills user-only or disables implicit invocation where the host
supports it. These controls are activation/UX safeguards, not a security boundary or proof that a
human initiated the underlying MCP call. Aptuni makes no claim that OFF retroactively deletes host
transcripts or restrains a capable host that is inside the accepted ADR-0013 trust boundary.

Official adapters run the MCP server in activation-required mode and expose the intents through
native user-invocable skills. Claude Code uses user-only plugin skills; Codex Agent Skills set
`allow_implicit_invocation: false`. The old
Claude SessionStart identity hook is removed. Host skill names and mention-like text are adapter UX,
not Core authorization.

The existing unrestricted MCP construction remains available as a compatibility seam for direct
application tests and explicitly managed integrations; official generated Claude/Codex bundles use
activation-required mode.

## Compatibility

This adds tools and adapter files without changing canonical schemas, stored host grants or Context
response semantics. Existing adapter bundles continue to load but retain their documented older
behavior until regenerated. Beta setup and upgrade guidance must tell owners to regenerate them.

## Verification

Task-reset and no-new-disclosure regressions; OFF identity/context/review/capture denial; process
reset, status and disable tests; exact mode record-type tests; grant/module/policy adversarial tests;
generated Claude/Codex skill parity and absence of automatic personal injection; documentation
checks that reject retroactive-erasure or authenticated-human-invocation claims; real-host
clean-environment probes and independent privacy review.

## Amendments

### 2026-10-01 — Actionable refusals and content-free grant status

Dogfooding Day 1 showed Agents could not recover from refusals: a multi-module activation failed
with a bare `mcp_module_denied`, and a memory proposal after a task-scoped Full failed with a bare
`aptuni_activation_required` while the grant also lacked `memory.propose`. Without changing any
boundary: (1) `mcp_module_denied`, `mcp_scope_denied` and `aptuni_activation_required` now carry a
fixed message built only from module and scope names (other codes stay bare, so an error can never
carry personal content); module denial names the denied and the granted modules and is still
all-or-nothing. (2) `aptuni_activation_status` adds `granted_modules` and `memory_proposals`
(`not_granted` | `needs_session_full` | `available`). (3) `aptuni_propose_memory` checks the grant's
`memory.propose` scope before the session state, so the Agent is not sent to ask for session Full
when the grant cannot save at all. Task scope still leaves no state and OFF still captures nothing.
(4) The generated Full skill tells the Agent to read the status first, to use distinctive keywords
as the query, and that saving needs session Full. Regenerated bundles pick up (4); the MCP changes
apply on upgrade. Regressions: `tests/integration/test_activation_guidance.py`.


## 2026-10-03 owner clarification — ordinary prompts inside Full

The owner explicitly keeps OFF / Profile / Memory / Full under user control.
An ordinary prompt never authorizes an automatic OFF-to-Full transition. Inside an
already explicitly enabled Full session, the host may autonomously decide whether
personal context materially helps, derive concepts, retrieve within the existing
grant and answer the original task. No manual keyword/search request is needed.
Generic tasks continue without retrieval. This clarifies the existing session
contract; it adds no grant or activation state. Real frozen ordinary-prompt runs
verify the path, with answer-quality failures recorded separately.
