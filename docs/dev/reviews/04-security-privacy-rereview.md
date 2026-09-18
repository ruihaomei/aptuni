# Security and Privacy Focused Re-review

- **Reviewer:** independent security/privacy re-review agent
- **Date:** 2026-09-18
- **Scope:** original review, remediation response, threat model, ADR-0002/0005/0006/0007/0008/0010,
  roadmap, spikes, and Phase 0/Foundation plans
- **Verdict:** **BLOCK**

The remediation is substantive. It converts most earlier recommendations into ADR language, spike
acceptance criteria, and negative tests. This review does not accept two remaining trust-boundary
gaps: the party allowed to mint a mutation confirmation is not defined, and “local-only” ignores the
mandatory agent host/model data path.

## Original-finding disposition

| Original | Re-review status | Evidence |
|---|---|---|
| B1 untrusted content/instruction injection | **Closed at planning level, dependent on B2 fix** | `THREAT_MODEL.md` lines 16–48 defines taint flow and data-only rendering; ADR-0005 lines 54–57 and ADR-0006 lines 48–59 carry it into interfaces/providers; S04/S05 have canaries. |
| B2 MCP authorization/confirmation | **Open — Blocking** | Risk classes, principals, epochs, nonces, and replay tests exist, but no trusted confirmation issuer/channel is specified. |
| B3 copy-wide retention/destruction | **Closed at planning level with High/Medium follow-ups below** | ADR-0010 inventories managed copies, separates operations, defines journal/receipt/restore ledger, partial-failure recovery, and marker tests; S01/Foundation carry schemas and fault tests. |
| H1 plugin trust | **Closed** | ADR-0002 lines 48–51 explicitly says in-process plugins are trusted code and S02 proves failure isolation, not sandboxing. |
| H2 parser hardening | **Closed** | ADR-0006 lines 54–59 plus S05 cover roots/origins, symlinks/TOCTOU, bombs, XML/external references, secrets, redirects, pagination, and rate limits. |
| H3 credentials/egress | **Partially closed; host-model path is Blocking** | ADR-0007 covers provider destinations and secret references, but not data handed by MCP to a cloud-backed host/model. |
| H4 snapshot minimization/at-rest | **Partially closed — High** | Full bytes are opt-in and permissions/plaintext are documented, but “versioned parser output” remains unbounded. |
| H5 MCP resources | **Closed** | ADR-0005 lines 46–48 requires bounded policy-mediated views and final policy recheck. |
| H6 L0 lifecycle | **Closed** | ADR-0008 lines 42–48 plus S12/M1.4 define permissions, epoch, invalidation, content allowlist, purge, and ship gating. |
| H7 supply chain | **Closed at planning level** | Roadmap M1.1 and Foundation Slice 1 move lock/review, isolated builds, SBOM/license/vulnerability/secret checks, and network canary to first scaffold. |
| M1–M4 | **Closed at planning level** | ADR-0007 covers transitive egress, diagnostics, and policy races; ADR-0010 covers restore resurrection and partial purge. |
| L1–L2 | **Scheduled appropriately** | Roadmap M1.5 schedules `SECURITY.md`; M1.3 schedules the privacy inventory. |

## Blocking findings

### B2-R1 — Confirmation has fields, but no trusted issuer or non-MCP issuance path

**Evidence:** The threat model names a “user/maintainer confirmation channel” and binds digest,
principal, scope, expiry, and nonce (`THREAT_MODEL.md`, lines 27–30 and 60–64). ADR-0005 requires a
single-use confirmation (`ADR-0005`, lines 39–44). S04 tests stale/replayed/mismatched confirmation
(`SPIKES.md`, lines 51–61). None of these documents states which component can mint the confirmation,
how human presence is established, whether the MCP host can invoke the issuer, who canonicalizes the
action digest, or whether nonce consumption is atomic with the mutation.

**Why this remains blocking:** If the same model-facing MCP surface can obtain both preview and
confirmation, prompt injection can complete the entire flow. Conversely, the current acceptance test
“injected-content-to-write denies” is not deterministically implementable from a normal MCP call: the
server cannot infer whether the model decided to call a tool because of malicious retrieved text.
Delimiters and warnings reduce model risk but are not an authorization boundary.

**Required planning fix:**

1. Choose the MVP confirmation channel explicitly, for example a core-owned interactive CLI/OS
   prompt that is not exposed as an MCP tool. Separate the human confirmer principal from the host
   principal; MCP may request a preview but cannot mint approval.
2. Specify that the core canonicalizes the action, computes the digest, stores or authenticates the
   grant, and atomically consumes its single-use nonce in the same transaction as the mutation.
3. Define which “reversible writes” may proceed without human confirmation. `observe` must at minimum
   remain quarantined as an untrusted candidate that cannot become exposable Profile/Memory truth;
   any direct canonical or exposed-content change requires the stronger flow.
4. Rewrite the injection test as enforceable assertions: source/model text cannot mint confirmation,
   unconfirmed consequential calls deny, a confirmed digest cannot be changed/replayed, and
   observation candidates cannot auto-promote. Keep model-behavior probes as defense-in-depth, not a
   claimed deterministic security guarantee.

### B4-R1 — The privacy/egress model omits the Claude/Codex host and cloud model

**Evidence:** `THREAT_MODEL.md` places bounded MCP/CLI output into the “host model” (lines 16–25), but
does not classify that transfer as egress or record the host's retention/training/logging boundary.
It then says local-only default-denies all egress and that a process-level network canary proves it
(`THREAT_MODEL.md`, lines 90–98 and 119–120; ADR-0007 lines 42–48). The process canary cannot observe
the host application transmitting MCP results to its model service. Claude Code and Codex adapters
are mandatory MVP interfaces, so this is not an out-of-scope deployment detail.

**Why this is blocking:** A user selecting the PRD's “No — everything must stay local” privacy mode
could still have L0/L1/L2 personal context processed and retained by a cloud-backed host. The current
wording would give a false local-only assurance even if every provider and the MCP server makes zero
network calls.

**Required planning fix:**

1. Add the host application, model provider, host logs/transcripts/caches, and their retention/deletion
   limits to the threat model and privacy inventory. Treat MCP result delivery to a non-local model as
   a separate `host_model_egress` policy action, not as covered by the server process network canary.
2. Record host capability/privacy metadata: local vs remote model execution, destination/operator,
   data classes/modules allowed, retention controls known/unknown, and whether deletion is managed by
   this product.
3. In strict local-only mode, deny personal MCP/L0 output to a host unless local processing is proven;
   health/capability responses may remain content-free. Other modes need informed per-host/module
   consent and must state that post-delivery copies are externally controlled.
4. Extend S04/S12 with a fake local host and a declared remote host. Assert strict-local denial,
   consent-bound module release, no L0 auto-injection to a disallowed host, and honest inventory/
   purge messaging for externally retained transcripts.

## High-priority findings

### H4-R1 — “Versioned parser output” can still be a full private-document copy

ADR-0006 lines 50–52 and ADR-0010 lines 54–56 minimize snapshots to hash, locator, parser output,
and minimum evidence excerpt, but do not bound the parser output. A Markdown parse tree or extracted
PDF/DOCX text can reproduce the entire document while technically not storing source bytes. Unknown
attributes are also preserved by ADR-0006 line 46 without saying that minimization, secret exclusion,
and retention rules apply to them.

**Action:** Define parser output as either reproducible structural metadata plus bounded, purpose-
limited evidence excerpts, or classify it as full-content retention requiring the same opt-in,
retention label, purge handler, size accounting, and export/diagnostic exclusion as source bytes.
Apply this rule to unknown attributes and model-derived summaries; taint and retention must propagate.
Add marker tests that inspect serialized snapshots/deltas, not only raw-byte stores.

### H7-R1 — Plugin approval hashes do not identify the executed dependency closure

ADR-0002 records package/version/hash/approval, while the plugin executes with process privileges and
may import arbitrary transitive dependencies. Hashing only the top-level wheel or installed metadata
does not bind the code actually executed after dependency resolution.

**Action:** Define the approval record as the resolved, locked distribution closure (name, version,
artifact hash, source/index, and relevant extras), plus the manifest hash. Activation must detect
drift from that approved closure. This can reuse the Foundation lock/SBOM work; S02 should change one
transitive artifact and prove activation fails or requires renewed approval.

## Medium-priority findings

### M1-R1 — Opted-in raw interaction buffers have no explicit encryption expectation

ADR-0010 line 41 specifies local TTL, delete-on-success, and startup cleanup, but not whether raw
buffers must be encrypted, even though each object is supposed to declare an encryption expectation
(lines 34–35). Raw prompts/responses are often more sensitive than curated facts.

**Action:** Require an explicit at-rest choice for opted-in raw buffering. Prefer OS-backed encryption
or require encrypted-disk placement; if unavailable, show a blocking/high-friction plaintext warning
and never silently enable the buffer. Test crash/restart/expiry without leaking content to temp or logs.

### M2-R1 — Managed versus external purge completion needs a machine-readable terminal state

ADR-0010 correctly discloses external/synced/COW limitations and supports partial-failure retry, but
does not define when the user-visible purge is `complete`, `complete_managed_external_action_needed`,
or `incomplete_retryable`.

**Action:** Put those states and per-copy results in the deletion receipt schema. Never report a bare
“deleted” while a provider is offline or a host transcript/external backup remains outside control.

## Re-review gate

The next security re-review should require:

- [ ] A concrete confirmation issuer/channel and atomic mint/consume contract that MCP cannot invoke.
- [ ] Enforceable observation quarantine and auto-promotion denial.
- [ ] Host/model egress and externally retained host copies represented in policy, threat model,
      privacy inventory, S04, and S12.
- [ ] Parser output/unknown attributes governed by the same full-content retention rules as raw bytes.
- [ ] Plugin approval bound to the locked transitive distribution closure.
- [ ] Raw-buffer encryption expectation and explicit purge terminal states.

**Final judgment:** **BLOCK.** The remediation closes the majority of the original review, but **2
blocking**, **2 high**, and **2 medium** findings remain. The project should not mark Gate 0 security
review complete until B2-R1 and B4-R1 are resolved and independently re-reviewed.
