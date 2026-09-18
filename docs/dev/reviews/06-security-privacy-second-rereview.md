# Security and Privacy Second Focused Re-review

- **Reviewer:** independent security/privacy re-review agent
- **Date:** 2026-09-18
- **Scope:** `04-security-privacy-rereview.md`, `04-security-privacy-remediation.md`, and the cited
  threat model, ADRs, spikes, roadmap, and Foundation plan
- **Baseline:** `python3 -m unittest tests/dev/test_check_relay.py` — 3 tests passed
- **Verdict:** **BLOCK**

The second remediation closes five of the six earlier items at planning level and materially improves
the sixth. It correctly stops claiming that a process network canary observes host/vendor traffic,
binds plugin approval to a dependency closure, classifies reconstructive parser output as full
content, specifies raw-buffer encryption choices, and defines purge terminal states. One authorization
claim remains unsound for the actual Claude Code/Codex environment: a TTY is not proof of a human when
the host agent can execute local commands and allocate a PTY.

## Finding-by-finding disposition

| Prior finding | Result | Evidence and judgment |
|---|---|---|
| B2-R1 trusted confirmation issuer | **Open — Blocking** | The CLI-only issuer, canonical digest, quarantine, and nonce transaction are explicit (`THREAT_MODEL.md` lines 67–78; ADR-0005 lines 46–50; ADR-0012 lines 33–45). Direct MCP approval is excluded and testable. However, “attached to a human TTY” is not a human-presence boundary against a shell-capable host agent. |
| B4-R1 host/model egress | **Closed at planning level** | `host_model_egress` is distinct, remote/unknown denies in strict-local, external retention/deletion is disclosed, and the server canary explicitly disclaims host coverage (`THREAT_MODEL.md` lines 103–120; ADR-0007 lines 42–48 and 63–68; S04/S12). |
| H4-R1 reconstructive parser output | **Closed** | ADR-0006 lines 54–61 applies full-content consent, labels, size accounting, purge, export/diagnostic exclusion, taint, and retention propagation to parser output, unknown attributes, extracted text, parse trees, and summaries. ADR-0010 lines 59–61 matches. |
| H7-R1 dependency closure | **Closed** | ADR-0002 lines 48–54 binds approval to manifest plus complete resolved lock/SBOM closure and fails drift; S02 and Foundation Slice 5 require transitive-artifact drift tests. |
| M1-R1 raw-buffer encryption | **Closed** | ADR-0010 line 41 and Foundation lines 77–79 require OS-backed encryption or encrypted-disk placement, otherwise an explicit high-friction plaintext warning with no silent enablement and crash/restart marker tests. |
| M2-R1 purge terminal state | **Closed** | ADR-0010 lines 54–57 defines three machine-readable terminal states plus per-copy results and forbids a bare “deleted” when managed or external copies remain. |

## Blocking finding

### B2-R2 — A TTY-only CLI is reachable by the same shell-capable agent it is meant to exclude

**Evidence:** The threat model calls the core CLI attached to a human TTY the sole issuer and says
source/model/MCP text cannot obtain approval (`THREAT_MODEL.md`, lines 67–73 and 134–146). ADR-0005
repeats that only this CLI can approve (`ADR-0005`, lines 46–50). S04 proves only that MCP cannot issue
approval (`SPIKES.md`, lines 58–74; `plans/00-phase-0-spikes.md`, lines 54–67). Claude Code and Codex,
the mandatory MVP hosts, are coding agents with local command execution. A process can allocate a PTY,
launch the CLI, and send the required typed phrase; `isatty()` does not establish human presence.

**Concrete failure path:** malicious retrieved content convinces the host model to create a pending
action, invoke `personal-context review <id>` through its shell tool under a PTY, and type the visible
confirmation. The request did not traverse an MCP approval tool, yet model text caused the same final
mutation the gate claims to prevent.

The residual-risk statement that a compromised host has powerful access (`THREAT_MODEL.md`, lines
148–155) does not resolve this mismatch. The abuse case is an ordinary model using an authorized
shell tool after instruction injection, not necessarily native-code compromise. Calling the channel
“human TTY” and treating it as deterministic authorization is therefore a false guarantee.

**Required fix before approval:** choose and document one honest contract:

1. **Real out-of-band approval:** use a confirmer outside the agent/host's authority, backed by an OS
   secure-attention/authentication mechanism or separate trusted UI/device. MCP and host shell must
   lack the capability needed to invoke or satisfy it. Add an adversarial PTY/shell test that cannot
   approve, while the trusted confirmer can.
2. **Narrower threat claim:** explicitly trust the configured host and all of its shell/process
   authority, remove claims that the core confirmation gate stops source/model-driven shell actions,
   and describe CLI confirmation as an accidental-action/UX guard only. Then require the host's own
   user approval/sandbox policy for shell execution and obtain maintainer acceptance of that residual
   risk. Tests must assert only what the core can enforce.

The current hybrid—treating the host/model as untrusted for mutation while trusting any TTY it can
spawn—cannot pass security review.

## High-priority finding

### H1 — “Nonce and mutation are atomic” is too broad for purge/provider/network side effects

The contract says core consumes the nonce “in the same Vault transaction as the mutation”
(`THREAT_MODEL.md`, lines 67–73; ADR-0005 lines 46–50). This is executable for a Vault-only candidate
approval or policy change. It cannot be atomic with deletion in an optional provider, managed-backup
rotation, or other external side effects. ADR-0010 correctly models those operations as a journal with
retryable partial failure, so the documents currently make two different atomicity promises.

**Action:** split the contract:

- Vault-only action: nonce consumption and final mutation commit atomically.
- Multi-system action: nonce consumption commits atomically with creation of the exact, durable,
  idempotent operation journal; workers perform side effects from that journal and receipts expose
  partial/terminal state. A retry never requires or accepts a second confirmation unless the action
  digest/scope changes.

Add concurrency and crash tests for two confirmers on one pending action, failure immediately before
and after journal commit, side-effect success before receipt update, and restart/retry. Exactly one
durable intent may exist and the same side effect must not execute twice unless its adapter contract is
idempotent.

## Medium-priority finding

### M3 — “Proven-local host” needs an admission authority, not host/config self-assertion

Strict-local is fail-closed for remote or unknown hosts, which is safe. The remaining term
“proven-local” is not defined beyond adapter metadata and a fake-host test (`THREAT_MODEL.md`, lines
113–120 and 145–146; S04/S12). Earlier text correctly says host annotations are untrusted.

**Action:** define who may assign `proven_local` and the admission evidence. For MVP, classify Claude
Code and Codex as remote/unknown unless a reviewed built-in adapter can demonstrate local model
execution; user- or host-supplied labels cannot elevate the class. Any future local-host admission
should pin the adapter/runtime and pass an end-to-end egress test that includes model execution, not
only the MCP server. Unknown or unverifiable remains denied.

This is non-blocking because the current default is denial, but it must be fixed before any real host
is allowed as local.

## Re-review gate

- [ ] Confirmation either uses a boundary unavailable to host shell/PTY, or its guarantee is narrowed
      and the host-shell residual risk is explicitly accepted.
- [ ] S04 includes an adversarial host-shell/PTY confirmation attempt matching the chosen contract.
- [ ] Atomicity language distinguishes Vault-only commit from durable multi-system operation intent.
- [ ] Concurrent/crash/idempotency tests cover nonce, journal, side effect, and receipt boundaries.
- [ ] `proven_local` has a trusted admission authority and real-host evidence requirements.

**Final judgment:** **BLOCK.** B4-R1, H4-R1, H7-R1, M1-R1, and M2-R1 are closed at planning level.
B2-R1 is improved but remains blocking because TTY presence is not human authentication against the
mandatory shell-capable hosts. One High and one Medium follow-up also remain.
