# ADR-0010: Model retention, destruction, and restore across every copy

- **Status:** Accepted (2026-09-19, Gate 0 exit review 15)
- **Date:** 2026-09-18
- **Deciders:** maintainer (final say) · proposing agent · reviewing agent(s)
- **PRD refs:** §14, §22–§23, §27, §40, §52
- **Research refs:** `docs/research/upstream/mem0.md`, `docs/research/upstream/source-identities-and-deltas.md`
- **Needs maintainer confirmation:** no

## Context

Canonical records, source snapshots, deltas, backups, indexes, L0 cards, optional providers, logs,
and temporary buffers can each retain personal data. “Delete” is unsafe unless its semantics and
partial failures are explicit across all copies.

## Decision drivers

- Raw interaction retention off by default
- Honest, recoverable privacy deletion
- Historical audit without retaining deleted content

## Options considered

### A — Delete only canonical records and rebuild later

**+** Simple. **−** Leaves recoverable copies and can resurrect data on restore.

### B — Retention classes plus coordinated purge and deletion ledger

**+** Explicit coverage and recovery. **−** More state and unavoidable backup limitations.

## Decision

Choose **B**. Every stored object declares a retention class, owner, purpose, location, expiry,
backup inclusion, encryption expectation, and purge handler.

| Copy class | Default | Purge behavior |
|---|---|---|
| Canonical Fact/Evidence/Memory | retained until explicit action | transactional remove/redact plus receipt |
| Source snapshot/delta | minimized; full bytes opt-in only | delete matching records/excerpts and replay state |
| Raw interaction buffer | no durable copy | opted-in buffer: OS-backed encryption or encrypted-disk placement, TTL, delete-on-success/startup cleanup; otherwise explicit high-friction plaintext warning |
| SQLite/cache/L0/projection | derived | invalidate/delete then verify/rebuild without target |
| Optional provider | provider-declared | adapter purge with partial-failure retry/status |
| Logs/audit | content-free, bounded | retain deletion event/receipt, never deleted content |
| Managed backup | rotation policy | expire managed generations; reapply deletion ledger on restore |
| External/synced/COW copy | user/environment controlled | disclose limitation and required user action |

APIs distinguish supersede/history, unlink source, delete derived projection, expire by policy, and
privacy purge. Purge requires an exact preview, scoped non-replayable ADR-0013 confirmation,
idempotency key, transaction journal, deletion receipt, and retryable partial-failure state. Nonce
consumption commits atomically with the exact durable journal intent; idempotent workers perform
external effects and update per-copy receipts. The minimal deletion
ledger stores only irreversible identifiers/digests needed to prevent restore/rebuild resurrection.
Uninstall runs provider/L0/temp cleanup but cannot claim deletion of unmanaged external copies.

Receipts have explicit terminal state: `complete_managed`,
`complete_managed_external_action_needed`, or `incomplete_retryable`, plus per-copy results. Never
report a bare “deleted” while a managed provider is offline or externally controlled host
transcripts/backups may remain.

Snapshots store full source bytes or equivalent full parser output only when replay cannot be
achieved from a stable source and the user explicitly enables that retention. Default snapshots
prefer content hash, locator, reproducible structural metadata, and bounded evidence excerpts.

An authorized privacy purge is the deliberate exception to ADR-0001's history-preservation rule.
Auditability never justifies retaining content the user validly purged.

## Consequences

- **Positive:** User-visible actions correspond to honest behavior across managed copies.
- **Negative / risks:** Some storage media/backups cannot promise secure erasure; UX must say so.
- **Follow-ups:** Define retention labels and receipt schema during S01; generate a privacy inventory
  showing copy locations, size, age, grants, and action effects.

## Verification

Marker tests search Vault, snapshots, deltas, temp files, backups, indexes, L0, logs, and providers
after expiry/purge/uninstall. Restore a backup predating purge and prove the deletion ledger prevents
resurrection. Fault-inject every purge step and prove safe retry/status.

## Amendments

### 2026-09-19 — Gate 0 acceptance

Accepted with S01 F3: the deletion-ledger entry is durable before any rewrite, and `recover()` runs at every process start before any read. Restore reapplies the ledger, must be atomic (never delete the live Vault before the replacement is in place) and must not re-baseline the change log (ADR-0013 item 5). Power loss was not tested (F4).
