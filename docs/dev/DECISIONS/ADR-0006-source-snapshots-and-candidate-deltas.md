# ADR-0006: Ingest immutable snapshots through candidate deltas

- **Status:** Proposed
- **Date:** 2026-09-18
- **Deciders:** maintainer (final say) · proposing agent · reviewing agent(s)
- **PRD refs:** §8–§10, §22–§23, §35, §48
- **Research refs:** `research/08-source-identities-and-deltas.md`
- **Needs maintainer confirmation:** no

## Context

Folder paths change, Git blobs change, and public MarginNote/OPML documentation does not promise
stable node IDs. Treating each import as current truth would cause duplicates, silent deletions, and
bad provenance.

## Decision drivers

- Exact source traceability and idempotent re-sync
- Conservative handling of rename, deletion, and ambiguous identity
- No direct source-to-Profile mutation

## Options considered

### A — Providers write canonical facts directly

**+** Simple pipeline. **−** Unsafe identity guesses and no reviewable boundary.

### B — Immutable source snapshots produce candidate deltas

**+** Auditable, replayable, conservative. **−** Additional staging model and reconciliation work.

## Decision

Choose **B**. A `SourceProvider` enumerates source items, captures immutable content/metadata
snapshots, and emits a versioned `candidate_delta` envelope. The envelope records provider/source
IDs, sync run, parser version, source locator, content hash, previous snapshot, operation, proposed
observations/facts, evidence, confidence, and ambiguity/review state.

A versioned `SourceConfig` owns approved roots/origins, semantic role, module mapping, and an
`AuthorityPolicy` such as `primary_for: [knowledge.studied]`. Authority is user policy, never
hard-coded by a provider. Conflict resolution evaluates the policy version active at candidate
system time: a sole primary may supersede within its declared dimension; equal, absent, ambiguous,
or changed authority yields parallel candidates for review. Confidence never overrides authority.
Immediately before canonical commit, the coordinator rechecks the candidate's authority-policy
version/epoch against current policy; stale candidates are invalidated or forced back to review.

Canonical identity, source identity, current path, and content hash are separate fields. Folder
renames may reconcile on exact hash plus scoped history. GitHub Standard uses repository ID,
commit/ref, path, blob identity, and API truncation signals. MarginNote uses preserved export
attributes when available; otherwise it stores generated IDs and conservative structural/content
fingerprints. Ambiguous matches become review items.

Source disappearance proposes a tombstone/staleness delta; it never automatically deletes facts.
Unknown attributes are preserved for future parser versions.

Source bytes, text, metadata, filenames, and model-extracted values are untrusted and carry taint
plus provenance into every later view. They occupy typed data fields only and cannot become host
instructions or authorization evidence. Snapshots are minimized by default: store hash, locator,
reproducible structural metadata, and bounded purpose-limited evidence excerpts. Parser output,
unknown attributes, parse trees, extracted text, and model summaries that can substantially reproduce
the source are classified as full-content retention and require the same explicit consent, label,
size accounting, purge handler, and export/diagnostic exclusion as raw bytes. Taint and retention
propagate through transformations.

Each provider must canonicalize and re-check approved roots/origins, define symlink/redirect policy,
exclude secrets/VCS/cache/binaries by default, bound count/bytes/depth/time/memory/pagination, verify
content type, and use safe parsers. XML external entities/network resolution and document/archive
external references are disabled; resource bombs and TOCTOU/loop escape are tested. GitHub uses
allowlisted API origins, least-scope secret references, bounded responses, and explicit truncation
and rate-limit handling.

## Consequences

- **Positive:** Re-sync is replayable and provenance survives reorganizations.
- **Negative / risks:** Snapshot storage can grow; retention and deduplication are needed.
- **Follow-ups:** Validate identity on real MarginNote 4 exports and publish the delta schema.

## Verification

Idempotent import; move/rename/delete/reappear fixtures; root/symlink/TOCTOU/parser-bomb/secret
exclusion tests; injection canaries in content and metadata; truncated/redirect/rate-limit GitHub
handling; parser upgrade replay; conflicting MarginNote/Folder/GitHub candidates and authority
changes over time; ambiguous MarginNote match stops for review; no fact deletion from source loss.
