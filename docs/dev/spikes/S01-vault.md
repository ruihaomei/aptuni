# S01 Result — Canonical schema and crash-safe/concurrent Vault

- **Date:** 2026-09-18
- **Status:** PASS on the Gate 0 baseline. Awaiting independent evidence review (plan 00 exit checklist).
- **Code:** `spikes/s01_vault/` (disposable; not part of any future package)
- **Machine-readable result:** `spikes/s01_vault/results/S01-result.json`

## Reproduce

```sh
/opt/homebrew/bin/python3.13 -m venv /tmp/s01-venv
/tmp/s01-venv/bin/pip install 'pydantic>=2,<3'
cd spikes/s01_vault && /tmp/s01-venv/bin/python run_s01.py   # exits non-zero on any failure
```

The runner asserts the baseline, runs all tests, measures commit and read latency, and writes the JSON
result. Network use is limited to the one-time `pip install`. The spike itself uses no network.

## Measured facts

| Item | Value |
|---|---|
| Interpreter / SQLite | CPython 3.13.3 (`/opt/homebrew/bin/python3.13` venv) / SQLite 3.53.2 |
| OS / filesystem | macOS 26.2 build 25C56; `statfs` of the temp directory reports `apfs` with `MNT_LOCAL` |
| Validation library | pydantic 2.13.5, pydantic-core 2.46.5, annotated-types 0.8.0, typing-extensions 4.16.0, typing-inspection 0.4.4 (MIT / PSF licences) |
| Tests | 46 run, 0 failures, 0 errors (`run_s01.py`, exit 0) |
| Commit latency, 1 record | median 16.2 ms (first 50 commits) → 25.0 ms (last 50, ~300 records); p95 25.9 ms |
| Full read, 316 records | median 8.4 ms |

### What the 46 tests establish

- **Schema (9 tests).**
  - All 16 golden records round-trip exactly through canonical JSON (sorted keys, UTF-8, Chinese kept
    readable).
  - Records are immutable.
  - All 20 invalid cases fail with the expected reason: naive timestamps, reversed or malformed
    partial dates, an unknown `schema_version` (the error names the migration), Evidence without a
    locator, missing trust, retention or policy epoch, a non-quarantined Observation or Candidate, a
    model reviewer, a malformed digest or id, confidence out of range, a Fact without evidence,
    self-supersession, a world change without `supersedes`, unknown fields, modules or signals, and an
    overlong excerpt.
  - A receipt cannot use a bare `deleted` state.
  - The PendingAction digest changes when the scope widens, and the id is `act-` plus 16 hex digits of
    the digest (64 bits, exact match only).
- **Invariants and temporal views (18 tests).**
  - Current view: superseded facts are hidden.
  - "As known at" returns the pre-correction belief.
  - Valid-time queries keep a world-changed interval (rank 3 in 2024, rank 2 from 2025) but drop
    corrected claims.
  - A revoked Memory leaves exposure but stays in history.
  - Quarantined Observations and Candidates are never exposable.
  - A disabled module is hidden.
  - Rejected: dangling links, double supersession, supersession backwards in system time, supersession
    across record types, supersession cycles, a Memory without a prior accept, a knowledge signal
    without supporting evidence, mastery wording in English or Chinese ("proficient", "精通"),
    duplicate idempotency keys, and a Candidate with a missing source.
- **Vault protocol (10 tests).**
  - Exact commit/read.
  - A stale `expected_seq` is a conflict and writes nothing.
  - An invariant violation rejects the whole batch.
  - Segments are readable JSONL.
  - The hash chain detects an out-of-band segment edit.
  - A writer killed with exit 137 at each of the four durability boundaries leaves exactly the prior
    or the next state. Recovery then leaves no orphans, and the next writer proceeds.
  - Purge removes the content and returns `complete_managed`.
  - Restoring a pre-purge backup does not resurrect the purged record.
  - Purge rewrites links consistently.
  - A purge crashed at every boundary leaves no purged content after `recover()`. This case initially
    **failed** at three boundaries; see finding F3.
- **Concurrency (2 tests).**
  - 8 spawned writer processes × 6 commits race a continuous reader: 48 commits land with no lost
    update and no torn snapshot, and the final sequence number is exactly 49.
  - After a lock holder is `SIGKILL`ed, the kernel releases its `flock` and the next writer commits.
- **Filesystem gate and migration (7 tests).**
  - The real temp volume is admitted.
  - Injected non-APFS, non-local, iCloud (`Mobile Documents`), `CloudStorage` and Dropbox paths are
    refused.
  - The v0 `facts.yaml` shape migrates deterministically to valid v1 Evidence and Fact.
  - An unknown future version fails with upgrade guidance.

## Protocol proven (write it into ADR-0001 when accepting)

- **Layout.** `HEAD.json` is the committed manifest: sequence number, segment list with SHA-256 and
  record count, and a hash chain. Commits go to immutable `records/seg-NNNNNN-*.jsonl` segments.
- **Outside the Vault**, in a local state directory: `writer.lock` and `deletion-ledger.jsonl`.
- **Commit.** Under an exclusive `flock`, the writer compares `expected_seq`, validates the union
  against the invariants, then:
  1. writes the segment to a temp file;
  2. runs `F_FULLFSYNC`;
  3. renames it and fsyncs the directory;
  4. writes HEAD to a temp file;
  5. runs `F_FULLFSYNC`;
  6. renames it and fsyncs the directory.
- **Readers** take no lock. A reader loads HEAD once, verifies each segment's hash and count, and
  retries if a purge removed a segment mid-read.
- **Purge.** The ledger entry (the SHA-256 of the id only) is made durable *first*. The purge then
  rewrites the remaining records into a new segment, commits HEAD and deletes the old segments.
  `recover()` completes any purge whose ledgered ids are still present.

## Interpretation and findings (inference, not measurement)

- **F1 — Performance scales with Vault size.** Commit latency grows because each commit re-reads and
  re-validates the entire Vault. `F_FULLFSYNC` sets a floor of about 16 ms. Extrapolated to about 10k
  records, a full read would take roughly 250 ms, and so would every commit. M1.1 must validate
  incrementally against an id/link index, with a full revalidation available in `doctor`. It must also
  add **segment compaction**: a chain-preserving rewrite, like purge, because one file per commit
  grows without bound. *Affects ADR-0001 and plan 01 Slice 3.*
- **F2 — Integrity mismatch is currently a hard read failure.** Any out-of-band edit of a segment makes
  the whole Vault unreadable. That is safe, but it conflicts with ADR-0013 item 5, under which edits
  that narrow exposure are honored and widening edits are quarantined. M1.1 must turn a mismatch into
  a structured "out-of-band change" path: keep the last good generation and diff the edited records
  into proposals. It must not refuse to read. *Affects ADR-0013 item 5, ADR-0001 and plan 01 Slice 3.*
- **F3 — The purge crash window was real.** Before the fix, a purge killed after writing its new
  segment but before committing HEAD resurrected the target, because the old HEAD was still valid.
  Ledger-first ordering plus `recover()` completion closes this. **`recover()` must therefore run at
  every process start, before serving any read**, because until then orphan segments may still hold
  purged bytes. *Affects ADR-0010 and plan 01 Slice 3 step 4.*
- **F4 — Durability scope.** Tests kill processes; they do not cut power. `F_FULLFSYNC` is the
  documented macOS primitive for durability across power loss, but power-loss behaviour was **not**
  tested. It is stated as an assumption, not a result.
- **F5 — Locking.** A kernel `flock` makes "abandoned lock recovery" automatic when a process dies.
  Because `flock` is local-only, this is safe only together with the filesystem gate: network and
  synced folders are refused, as tested.
- **F6 — Schema decisions validated.**
  - Partial ISO dates (`2024`, `2025-01`) work as half-open valid-time intervals.
  - Only the forward `supersedes` link is stored.
  - A per-type `Literal` review status keeps Observations and Candidates quarantined at the schema
    level.
  - Candidate status is derived from ReviewEvents, so Candidates are never mutated.
- **F7 — Not covered by S01 (by design).** Snapshot and CandidateDelta go to S05A. Module-policy
  default values, including the fixture's `relationships.expose_enabled: false`, are proposals that
  still need a decision.

## ADR impact

| ADR | Impact |
|---|---|
| ADR-0001 | Supported. Record the proven layout and commit protocol above, plus requirements F1 (incremental validation and compaction) and F2 (out-of-band edits become proposals). |
| ADR-0010 | Supported with an amendment: purge writes the ledger first, and `recover()` must run at startup before any read (F3). |
| ADR-0011 | Supported. All five lifecycle record types round-trip, and the transition invariants hold. |
| ADR-0013 item 5 | Hash-chain detection works. The read path must degrade to quarantine, not refusal (F2). |
