# Review 16 — M1 Slice 1 (canonical records, Vault, CLI)

**Date:** 2026-09-19

**Scope:** commit `1c4f4af`. This is high risk: it contains the canonical schema and purge. The
reviewer was independent and read-only, ran pytest, mypy and ruff, and probed adversarially from
`/tmp`, which was deleted afterwards.

## Findings

| # | Severity | Finding |
|---|---|---|
| 1 | BLOCKING | Lost update on the module policy. `_commit` used the head at commit time, not at read time, so two concurrent policy changes both became epoch N+1 and one was dropped. A "hide from agents" change could be lost, and `remember` could check ingest against a stale policy. |
| 2 | BLOCKING | `init` accepted a non-empty directory and reused its `records/` folder. On the next open, orphan cleanup deleted any unlisted file there, and a subdirectory made every later open fail. |
| 3 | NON-BLOCKING | `correct()` skipped the ingest gate. |
| 4 | NON-BLOCKING | Commit accepted a record whose id is in the deletion ledger (resurrection); this matters for deterministic source ids. |
| 5 | NON-BLOCKING | A torn last ledger line made `open()` fail forever. |
| 6 | NON-BLOCKING | The chain check is skipped permanently after the first purge. |
| 7 | NON-BLOCKING | The segment cache keeps purged content in a long-lived process. Purging a correction makes the superseded fact current again. |
| 8 | NON-BLOCKING | `exposable()` did not filter `quarantined`/`pending_review`. |
| 9 | NON-BLOCKING | The CLI leaked tracebacks for integrity, filesystem, schema and config errors. |
| 10 | NON-BLOCKING | `schema_version` accepted `true`/`1.0`; NaN was accepted in canonical JSON; locator fields could hold non-JSON types. |
| 11 | — | Privacy and permissions were acceptable. The Vault root could be 0700. |

## Remediation

Fixed test-first in the next commit (see `16-m1-slice1-core-remediation.md`): F1, F2, F3, F4, F5,
F8, F9, F10 and the Vault permissions from F11. F6 and F7 go to `docs/dev/BACKLOG.md`.

**Verdict:** **BLOCK**
