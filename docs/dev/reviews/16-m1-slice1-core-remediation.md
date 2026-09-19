# M1 Slice 1 Core Review Remediation

- **Date:** 2026-09-19
- **Responds to:** `16-m1-slice1-core-review.md`
- **Status:** blocking findings fixed test-first; independent focused re-review still required

| Finding | Remediation |
|---|---|
| F1 stale-read lost update | Every mutating application command now decides against one `(seq, RecordSet)` snapshot and commits with that exact `expected_seq`. Concurrent policy or ingest changes fail with `concurrent_write`; regression tests cover both races. |
| F2 unsafe init/orphan cleanup | `init` refuses non-empty targets, creates the Vault/state directories with mode `0700`, and recovery deletes only protocol-shaped segment/temp files. Foreign entries are retained and reported by `doctor`. |
| F3 correction skipped ingest policy | `correct()` evaluates the current module policy from the same snapshot used by its write. |
| F4 purged-ID resurrection | Commit checks new record IDs against the deletion ledger and rejects resurrection. |
| F5 torn ledger tail | A malformed final JSONL line is treated as an interrupted append; earlier durable entries remain active. Malformed non-final lines still fail closed. |
| F8 exposure filtering | Retractions, `pending_review`, and `quarantined` records are excluded from exposable views; withdrawn candidate memory cannot reappear through its memory record. |
| F9 raw CLI tracebacks | Config, filesystem, schema, JSON, integrity, invariant, and optimistic-conflict failures are mapped to stable application errors. |
| F10 weak canonical JSON/schema validation | `schema_version` must be exactly integer `1`; fact numbers and locator JSON reject non-finite/non-JSON values. |
| F11 permissions | New Vault roots, record directories, and state directories are mode `0700`. |

F6 (chain verification after purge) and the semantic part of F7 (purging a superseding record can
reactivate an older version) are recorded in `docs/dev/BACKLOG.md` for the coordinated
privacy/restore slice. Cache state is cleared after purge now, so long-lived processes no longer
serve physically purged content.

Validation after remediation and Folder Source integration: 137 tests plus 47 subtests pass; Ruff,
mypy strict, relay checker unit tests, and `git diff --check` pass. The review stream deliberately
remains `BLOCK` until an independent reviewer verifies these fixes.
