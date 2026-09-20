# Data-Flow Threat Model

**Status:** Gate 0 draft for independent re-review
**Scope:** local MVP, including Folder/MarginNote/GitHub sources, Vault, projections, CLI, MCP, and
Claude Code/Codex adapters. Streamable HTTP and untrusted community plugins are out of scope.

## Protected assets

- Canonical facts, evidence, source locators, snapshots, deltas, review state, and history.
- Module permissions, retention/egress grants, deletion receipts, policy epochs, and audit events.
- Credentials, source roots, repository identities, local paths, queries, diagnostics, and L0 cards.
- Integrity of candidate approval, supersession, purge, permission, and source configuration actions.

## Trust boundaries and data flow

```text
untrusted source bytes/metadata
  → hardened provider parser
  → tainted structured Snapshot/CandidateDelta
  → independent schema + policy + review gate
  → canonical Vault
  → policy-mediated projection
  → policy-mediated Context service
  → bounded MCP/CLI response as quoted data
  → host model (not an authorization principal)

user/maintainer confirmation channel
  → exact action digest + principal + scope + expiry + nonce
  → mutation authorization gate
  → canonical transaction + audit/deletion receipt
```

Sources, retrieved text, model output, plugin metadata, filenames, paths, HTTP responses, and host
annotations are untrusted. They can supply data and proposals; none can grant permission or confirm
a mutation. The local user/configured host principal is separate from the model and source content.

## Mandatory controls

### Instruction-injection boundary

- Source-derived strings carry `trust = untrusted_source` and provenance through snapshots,
  candidates, records, and retrieval results.
- Parsers place content only in typed data fields. Never splice it into system/developer messages,
  tool descriptions, prompt templates, policy text, or confirmation instructions.
- Render retrieved content with explicit data delimiters and length/markup normalization. Tool
  results state that embedded instructions are not authoritative.
- Candidate extraction is a proposal. Independent policy and, for consequential actions, the
  ADR-0013 confirmation (never derived from retrieved content) are mandatory.

### MCP/CLI authorization

| Risk | Examples | Default rule |
|---|---|---|
| Pure read | health, capabilities | configured principal + scope |
| Bounded personal read | L0/L1/L2 context, evidence | scope + current policy epoch + final exposure recheck |
| Reversible write | submit observation, start configured sync | scoped grant; preview/audit where content changes |
| Networked action | GitHub sync/new destination | explicit provider/destination/data-class egress grant |
| Destructive/permission action | approve promotion, purge, change module/root | core-rendered preview + ADR-0013 terminal-only CLI confirmation |

Read and write tools use separate namespaces. Unknown actions are denied. Local STDIO is transport,
not authorization. Each configured host has a local principal and explicit scopes stored outside
source content. Consequential confirmation binds principal, action type, canonical action digest,
policy epoch, expiry, and single-use nonce. Replays, stale epochs, scope widening, and mismatched
digests fail closed. Streamable HTTP remains disabled until S21 defines authentication,
authorization, tenant separation, origin/CSRF/DNS-rebinding controls, and revocation.

**Enforcement boundary (ADR-0013, maintainer-accepted 2026-09-18).** Core confirmation authorizes
mutations only through application services. It is an accidental-action and MCP-cannot-self-approve
guard, not proof of human presence. MCP tools and agents may create a pending action but never
approve it; approval happens only when the user runs the review/purge subcommand in their own
terminal, which shows the full core-rendered preview and takes only core-generated action IDs
(`[a-z0-9-]`) on its command line. A confined agent cannot commit an approval (the sandbox denies the
Vault/nonce write), so its attempt fails closed. A same-user process with unconfined shell/file access
(e.g. a host in bypass/full-access mode) is inside the user's trust boundary: it can edit
Vault/config/grant state or installed code directly, and nothing in core claims otherwise. The real
control against an injected host agent is host confinement: adapter profiles deny agent writes (and,
where supported, reads) of Vault, config/grant/state and install paths. Core can prove confinement is
`not_in_effect` from core-observed evidence but never claims it is in effect; otherwise the status is
`unverified`, session-bound, unchangeable by labels/env/config, and host-visible only as an enum plus
reason codes. Status detects misconfiguration of a cooperating session and cannot attest confinement
against an already-unconfined agent. Out-of-band edits are detected before every policy decision:
purely narrowing edits are honored; widening, mixed, and module-retag edits are quarantined. Detection
catches uninformed edits only and is not a security boundary.

For Vault-only actions, confirmation verification, nonce consumption, and mutation commit are one Vault
transaction. For multi-system purge/provider/network actions, nonce consumption commits atomically
with an exact durable idempotent operation journal; workers perform effects from the journal and
per-copy receipts expose partial/terminal state. Retry reuses the durable intent without a second
approval unless digest/scope changes. Concurrent approvals create exactly one durable intent; effects
run at least once through idempotent adapters or dedupe keys. Before each disclosing network/provider
effect a worker rechecks the current grant and epoch; revocation or narrowing ends the intent in
`cancelled_policy`, while purge always continues.

`observe` may create only a quarantined, non-exposable candidate and never auto-promotes. A sync of
an already approved source may update snapshots/candidates within its existing root/origin/egress
grant. Any direct Profile/Memory exposure, candidate approval, permission/source grant change, purge,
or scope widening uses the ADR-0013 confirmation.

### Source/parser boundary

- Canonicalize and re-check approved roots; define symlink behavior and prevent loops/TOCTOU escape.
- Default-exclude VCS internals, secret/credential patterns, caches, binaries, and device/special files.
- Bound file count, bytes, depth, archive expansion ratio, parser time/memory, pagination, and response
  size. Verify content type where possible.
- XML disables external entities/network resolution. Archive/PDF/Office parsing disables external
  references and defends against resource bombs.
- GitHub allows only configured official/enterprise API origins, constrains redirects, uses bounded
  pagination, least-scope token references, and handles truncation/rate limits explicitly.

### Plugins and dependencies

An activated in-process Python plugin is trusted code running with the user's process privileges.
Its manifest is disclosure and compatibility metadata, not a sandbox. MVP permits only builtin or
explicitly reviewed packages, records package/version/hash/approval, and passes narrow ports rather
than Vault objects or ambient secrets. “Untrusted community plugin” support requires a later
subprocess/OS sandbox and signed-provenance design.

Dependencies are locked and reviewed from the first scaffold. Builds are isolated; unexpected
install-time code, new network destinations, telemetry, vulnerabilities, licenses, SBOM changes,
and hashes are review events.

Slice 15 automates that review boundary: CI installs only from `uv.lock`, checks the full
cross-platform runtime closure against `THIRD_PARTY_NOTICES.md`, scans tracked files for
high-confidence private-key/provider-token shapes, audits the exported hash-locked runtime set,
emits CycloneDX 1.5, and proves wheel/sdist byte reproducibility under a fixed ZIP-safe build epoch. The
scanner is deliberately a high-confidence gate, not a claim that arbitrary secrets are detectable;
GitHub repository secret scanning remains a release setting.

### Policy, egress, credentials, and diagnostics

- Policy actions include ingest, raw retention, projection, retrieval, exposure, network egress,
  host-model egress, credential use, permission change, unlink, and purge.
- Local-only mode default-denies all egress. Other modes grant provider + destination + data class.
- Config stores secret references only. Resolve credentials through host/OS secret storage at use
  time; prefer least-scope, revocable tokens.
- One diagnostic boundary redacts content, paths, URLs, headers, query text, environment, exception
  chains, and stable personal IDs before persistence and before any host-bound status/diagnostic.
  Support bundles are bounded and previewable.

The host application/model provider is a distinct external boundary. Adapter metadata records local
versus remote model execution, operator/destination, allowed modules/data classes, known or unknown
transcript/log/cache retention, deletion controls, and whether this project manages those copies.
Strict local-only mode returns only content-free health/capability data unless local model processing
is proven; it denies L0 and personal MCP results to a remote/unknown host. Other modes require
informed per-host/per-module `host_model_egress` consent and report that post-delivery copies are
externally controlled. A server-process network canary proves only project/provider egress, never
host/model behavior.

Core policy is the only authority allowed to assign `proven_local`. Claude Code and Codex are
remote/unknown by default. Admission requires a reviewed builtin adapter and model runtime pinned by
binary/package hash plus an end-to-end model-execution egress test; user/host/config labels cannot
elevate the class. Drift — a per-session hash mismatch of the adapter or model runtime, checked
before any L0/personal release — revokes admission. Unknown or unverifiable always remains denied.

### Policy races and derived views

Policy changes increment a monotonic epoch. Retrieval binds results to an epoch and rechecks policy
immediately before serialization. Cards/caches/projections are invalidated atomically or treated as
stale. MCP resources are bounded application-service views, never direct Vault/database/file access.

### Retention, purge, and recovery

ADR-0010 inventories every durable copy. A privacy purge is not historical supersession or source
unlink. It uses preview, exact scope, ADR-0013 confirmation, idempotent receipt, projection/provider
cleanup, partial-failure recovery, backup expiry disclosure, and restore-time tombstone reapplication.

## Abuse cases and required tests

1. Source text/metadata contains fake system rules, fake tool JSON, Unicode tricks, huge markup, or
   “approve/expose” instructions → treated only as bounded untrusted data; no write or module leak.
2. Host/model forges caller scopes or reuses/stales a confirmation → denied and content-free audited.
   MCP/model text requesting approval cannot approve; MCP, hook and worker entry points cannot reach
   the approve service. With the adapter profile applied (S04 fixture), a host agent's write to
   Vault/config/grant/install paths is denied by the host; `doctor` never reports confinement as in
   effect, reporting `not_in_effect` only on core-observed evidence and `unverified` otherwise. A
   direct file edit that widens exposure is quarantined; a narrowing edit is honored.
3. Module is disabled while retrieval/card render is in flight → epoch mismatch and final recheck deny.
4. Source path uses symlink/race/archive/XML/PDF escape → parser stops without reading outside grant.
5. Offline mode executes every builtin flow → process-level network canary observes no egress.
6. Marker secret appears in filename/content/URL/env/exception → absent from logs and diagnostics.
7. Purge then rebuild/restore/uninstall → marker absent from all copy classes; deletion ledger prevents
   resurrection, while limitations of external/COW/synced backups are reported.
8. Declared remote/unknown host under strict local-only mode → no L0/personal result; fake proven-local
   host fixture (under `tests/` only, absent from wheel/sdist) succeeds. Per-module consent releases only
   granted data and inventory names external copies.
9. Egress is revoked between journal commit and worker execution → no network effect; intent ends in
   `cancelled_policy`.
10. A forged `.pyc` is placed next to an approved plugin module (S02 F1; pip RECORD does not hash
    bytecode) → plugin imports use a core-owned `sys.pycache_prefix`, so the forged bytecode is
    never executed (KI-017).

## Residual risks and explicit non-claims

- Open-format storage is plaintext unless the user provides encrypted disk/backup storage.
- Secure physical erasure cannot be guaranteed on copy-on-write filesystems, synced folders, or
  external backups; the product reports and expires managed copies instead of claiming certainty.
- A compromised host process or explicitly activated plugin has powerful local access; MVP reduces
  ambient authority but does not sandbox it.
- Host file tools (Read, `cat`, patch context) may read Vault and state files where the host cannot
  deny reads, and an agent shell can run the CLI (`doctor`, `review`) and see its full output;
  strict local-only governs only core-mediated delivery to the host (MCP, L0 hook), and the
  onboarding privacy preview says so per host.
- Approving a host escalation request (e.g. Codex on-request) for this CLI runs an agent-composed
  command unconfined; declining such requests is the user's control (ADR-0013 item 2).
- **Accepted by the maintainer (ADR-0013):** a same-user host running unconfined can change the
  local profile and policy without product approval. Hardware-backed approval is a future ADR.
- Model behavior is probabilistic; authorization correctness must remain deterministic outside it.
- Installed `.pth` files run at interpreter startup, before any Aptuni code. Plugin integrity
  checking is detection, not containment, and cannot see files that RECORD does not list (S02 F4).
