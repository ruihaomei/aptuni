# ADR-0001: Make the open-format vault canonical

- **Status:** Accepted (2026-09-19, Gate 0 exit review 15)
- **Date:** 2026-09-18
- **Deciders:** maintainer (final say) · proposing agent · reviewing agent(s)
- **PRD refs:** §4–§7, §16, §22–§23, §52
- **Research refs:** `docs/research/upstream/graphiti.md`, `docs/research/upstream/source-identities-and-deltas.md`
- **Needs maintainer confirmation:** no

## Context

The product must preserve identity, evidence, and history while allowing storage/retrieval backends
to change. Graph databases and search indexes cannot round-trip every required field.

## Decision drivers

- User ownership and backend portability
- Bi-temporal history, provenance, review, and conflict handling from Day 1
- Inspectable, diffable, repairable data

## Options considered

### A — A backend database is authoritative

**+** Simple writes. **−** Provider lock-in; lossy export; poor human repairability.

### B — Open-format canonical vault with rebuildable projections

**+** Portable and auditable. **−** Requires schemas, migrations, and projection ledgers.

## Decision

Choose **B**. Versioned YAML/JSON/JSONL/Markdown records in the Profile Vault are authoritative.
SQLite, embeddings, Mem0, Graphiti, and caches are projections.

The canonical Fact contract includes stable `id`, `module`, `type`, `statement`, `valid_from`,
`valid_until`, `observed_at`, `ingested_at`, immutable `recorded_at`, `supersedes`, `change_kind`,
`source`, `episode`, `confidence`, and `review_status`. Evidence uses stable source locators and discrete signals
(`exposure`, `studied`, `applied`, `demonstrated`). Corrections append or supersede records; they do
not silently rewrite history. Schema records carry an explicit version and migrations are tested.

Valid time (`valid_from`/`valid_until`) says when the claim applies in the user's world. System time
(`recorded_at`) says when this immutable record version entered canonical history; “as known at”
queries filter append-only versions by it. `ingested_at` is source-pipeline timing, not transaction
history. Only the forward `supersedes` link is authoritative; `superseded_by` is derived. A
`world_change` starts a later valid interval, a `correction` replaces what the system believed about
an earlier interval, and a `retraction` withdraws without asserting a replacement. Same-valid-time
conflicts remain parallel reviewed claims unless an explicit decision links them.

Every projection must declare field loss. A provider that cannot preserve canonical IDs or
provenance keeps an adapter-owned mapping ledger. Deleting and rebuilding a projection must not
alter canonical files.

## Consequences

- **Positive:** Provider changes cannot erase the user's history; files remain inspectable.
- **Negative / risks:** File transactions and referential integrity require deliberate handling.
- **Follow-ups:** Specify vault layout, JSON Schemas, atomic write protocol, and migrations before
  broad ingestion.

## Verification

Golden-record schema tests including out-of-order observation, correction, later world change,
same-valid-time conflict, and historical “as known at”; append/supersession invariants; crash-safe
write spike; delete/rebuild projection tests; export/import round-trip equality excluding declared
derived fields.

## Amendments

### 2026-09-19 — Gate 0 acceptance

Accepted with the S01 protocol. Layout: `HEAD.json` manifest (seq, segment list with SHA-256 and count, hash chain) plus immutable `records/seg-NNNNNN-*.jsonl` segments; commit under an exclusive `flock` with `expected_seq`, `F_FULLFSYNC` and directory fsync at each rename; readers take no lock. The chain detects uninformed edits only (HEAD is self-attesting). S01 F1: commits validate incrementally (new records against the full index) and segment compaction is required; full revalidation lives in `doctor`. S01 F2: a hash mismatch becomes an out-of-band-change path (quarantine and propose), never a permanent read refusal. `episode` is carried in `provenance`; `observed_at`/`ingested_at` are record-type fields (Evidence/Fact). Still-untested verification items (same-valid-time conflict, out-of-order observation, projection delete/rebuild, export/import round-trip) are M1.1 work.

### 2026-09-20 — HEAD format 2 (`chain_base`)

The M1 privacy/restore slice adds `chain_base` to the `HEAD.json` manifest and moves the format from
1 to 2. Before this, a purge re-anchored `chain` onto the pre-purge value without recording the
anchor, so the chain of a purged Vault could not be verified and `verify()` had to excuse the check
whenever the deletion ledger was non-empty (Review 16 F6). Recording the anchor makes a purged
Vault's chain verifiable again, and `restore_from` publishes the replacement as a new generation
anchored at the live chain instead of re-baselining it (ADR-0010 amendment, ADR-0013 item 5).

Compatibility is explicit, not silent. Format 1 stays readable. `recover()` migrates it on open: a
HEAD that verifies from GENESIS is restamped as format 2 unchanged, and a legacy *purged* HEAD --
whose anchor is unrecoverable by construction -- keeps its recorded chain as the new anchor, which
is the same re-anchoring the current purge performs, except now written down. `restore_from` accepts
a format-1 backup with that artifact so a backup taken after a legacy purge stays restorable; every
segment is still hash-verified and every record invariant still checked. A chain mismatch with no
purge in the ledger remains a reported problem: that is corruption, not the legacy artifact
(Review 31 F2).

### 2026-09-20 — The deletion ledger moves into the Vault (ADR-0016)

This ADR originally placed `deletion-ledger.jsonl` in the state directory, "outside the Vault and
its backups". KI-021, reproduced 2026-09-20, showed that contradicts ADR-0010's own acceptance
requirement: restoring a pre-purge Vault copy with a fresh state directory re-admitted a record the
owner had purged (ledger entries seen 0, purged Fact restored), because the state directory is
disposable while a deletion is not. The canonical layout now includes
`<vault>/deletion-ledger.jsonl`. Entries remain one-way digests of record ids and never content, so
the portable Vault discloses nothing new. `ledger_digests()` reads the union of the Vault ledger and
any not-yet-migrated legacy file, so an old Vault is protected from the first read; `recover()` folds
the legacy file in, durably before unlinking it, idempotently, tolerating a torn tail. ADR-0016 has
the full rationale, the rejected alternatives and the verification.
