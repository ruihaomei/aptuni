# Review 84 — Focused re-review of the Review 83 B1 fix (purged derived Fact)

This is a focused, independent re-review under `AGENTS.md`, because the change touches privacy
purge and deletion lineage. The reviewer did not modify production code, tests, ADRs, STATE/HANDOFF
or `STATUS.json`; this report is the only file written. All probes ran against disposable
`Workspace(tmp/"state")` Vaults in a scratch directory.

## Scope

The fix covers these files:

- `src/aptuni/domain/evidence_profile.py`: `EvidenceLineage(records, purged)`. `owner_decided`
  treats a ledgered derived-Fact id anywhere in the Evidence lineage as a permanent withdrawal.
- `src/aptuni/policy/evidence_profile.py`: `EvidenceProfileWriter(records, purged)`, and
  `derive_evidence_profile(..., *, purged)` with a required keyword.
- The three callers pass `frozenset(self.vault().ledger_digests())`:
  - `source_commands._commit_evidence_profile` (normal and duplicate sync paths);
  - `review_commands.refresh_profile`;
  - `source_authority.grant_source_authority`.
- The three new regressions in `tests/integration/test_evidence_profile_lineage.py`.
- The Review 83 N4/N6 copy changes, and the BACKLOG entries for N1–N3, N5 and N7.

## Checks run

| Check | Result |
|---|---|
| Full `pytest` suite | 1043 passed, 3 skipped, 62 subtests passed (113 s) |
| `ruff check .` | All checks passed |
| `mypy src` (strict) | Success: no issues in 111 source files |
| `python3.13 tools/check_relay.py` | relay check passed |
| `git diff --check` | clean |
| Review 83 B1 repro: purge one derived Fact, then no-op sync, `profile refresh`, changed sync | all succeed; the purged lineage is not recreated; no `*.pending.json`; `doctor` ok |
| Unrelated lineages after a Fact purge | renaming the purged card *and* another card in one sync: the other card (and re-pathed descendants) derive normally; only the purged lineage stays withdrawn |
| Purge of an Evidence item (expands to the whole source), then re-approve the same store | new source id, new Evidence ids (`delta_id` is source-scoped), no ledger collision; sync forms 5 Facts; `doctor` ok |
| Grant flow: grant, purge one derived Fact, then no-op/refresh/changed sync | all succeed, purged lineage stays withdrawn; re-derived Evidence ids are seeded by the fresh grant event id, so no collision |
| Grant → removal → re-approve the same store → sync → second grant | all succeed; `doctor` ok |
| Crash at `after_segment_rename` in the first post-purge sync, then a fresh service syncs twice | recovery succeeds; the new card derives; no pending journal remains; `doctor` ok |
| Crash at `after_segment_tmp` (pending journal, no commit) after a purge | resync succeeds; no pending journal; `doctor` ok |
| Expose off → purge → expose on → no-op backfill | writes 0, no failure |
| Backup before purge, then restore after purge | restore reapplies the ledger; the purged Fact is absent; sync/refresh write 0; `doctor` ok |
| Scale at 27k, one-commit purge of 500 derived Facts | preview 0.16 s, confirm 2.68 s; no-op sync 3.41 s (0 written), refresh 0.31 s, changed sync 2.31 s, `doctor` 2.56 s — same envelope as Review 83 |

## Blocking findings

None.

The fix is correct for the failure mode. The ledger check runs before any id is emitted. It walks
the full Evidence ancestry, which is the same walk used for owner reject and edit decisions. It
matches only the exact deterministic Fact ids of that lineage, so it cannot suppress an unrelated
lineage. The event id needs no separate check: promotion events are not directly purgeable and are
always purged together with their Fact (`_required_by_selected`). A purged Evidence item always
expands to its whole source, so a purged ancestor can never leave a live descendant behind. The
required `purged` keyword means a future caller cannot silently omit the ledger.

## Non-blocking notes

1. **The ledger check is writer-side only.** The Vault invariant never sees the ledger (consistent with Review 83 N1, which is already in BACKLOG), and `Vault.commit` still refuses any ledgered id as a backstop.
2. **Re-approving the same store after a whole-source purge re-forms the purged claims under a new lineage.** This matches ADR-0027's "approve it again" and is covered by the BACKLOG entry for Review 83 N7; the owner-facing purge/removal copy could say so.
3. **The N6 grant copy lists only two exceptions.** It names "automatic promotion is off or the knowledge module is hidden", but not the sensitive-module exception (`_module_allows`). This is a copy-only gap.
4. **The new regressions do not cover crash recovery after a purge or restore after a purge.** Both passed in the probes above. One test for each would pin them.

## Verified sound

- Review 83 B1 is resolved: no path re-derives a ledgered Evidence-derived Fact. Sync (normal,
  duplicate and crash-recovered), `profile refresh` and the authority grant all read the ledger.
- Owner withdrawal semantics are uniform: reject, edit, `retract` and purge each permanently
  withdraw every later version of the source subject.
- There are no new deterministic-id collisions. Evidence ids are source/delta-scoped. Grant and
  removal re-derivations are seeded by fresh event ids. Re-approval gets a new source id.
- The Review 83 N4 setup message now suggests `source authorize` only for a MarginNote source whose
  missing authority is exactly `knowledge.studied`; other mismatches fail closed with a neutral
  message.
- Cost is unchanged at 27k: one ledger read and one `sha256` per lineage version per candidate.

_Verdict line normalized to the relay's anchored spelling by the implementing agent; the reviewer's verdict is unchanged._

**Verdict:** **APPROVE WITH NON-BLOCKING NOTES**
