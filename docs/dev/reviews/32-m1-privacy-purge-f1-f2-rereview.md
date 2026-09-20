# Review 32 — M1 privacy purge F1/F2 remediation re-review

**Date:** 2026-09-20

**Reviewer:** independent privacy/security re-review agent (read-only except for this report)

**Scope:** the third remediation round, targeting Review 31's F1 (wedged purge) and F2 (HEAD format
1 → 2), in the uncommitted working tree on top of `0b0eabf`, including the untracked
`src/aptuni/vault/locks.py` and `tests/integration/test_privacy_purge.py`. Reviews 29 and 30 are
settled and were re-probed only far enough to confirm no regression. The re-review read Review 31
first, then the full diff, re-ran Review 31's Reproductions A and B verbatim, enumerated every
canonical writer, adversarially probed `cancel_purge` (replay, corrupt intent, concurrent cancels,
crash windows, the refusal branch), re-tested the format-1 migration for legacy support, Review 16
F6 regression, downgrade laundering, crash-safety and idempotence, and ran the seven new tests
against neutralized versions of each remediation element to show they are not tautological. Every
probe ran in `tempfile.TemporaryDirectory()`; nothing was written to the repository except this
file, and no personal data was written anywhere.

## Validation

- `.tools/bin/uv run pytest`: **339 passed, 47 subtests passed** in 35.59s (Review 31 saw 332 + 47;
  +7 = the four F1 and three F2 tests).
- `.tools/bin/uv run ruff check .`: **All checks passed!**
- `.tools/bin/uv run mypy src`: **Success: no issues found in 58 source files**.
- `python3.13 tools/check_relay.py`: **5 errors**. Three are the expected pending-checkpoint
  lineage entries for reports 29/30/31. **Two are real and introduced by this diff** — see N1.
- Canonical-writer enumeration: **8 write paths probed**, 8 fail closed with
  `privacy_action_in_progress` while a durable intent exists (including the MCP propose path and an
  out-of-scope source sync); no writer bypasses the guard.
- `cancel_purge` adversarial matrix: **6 cases**; 5 behave honestly, 1 (post-purge crash window)
  is dishonest but bounded — see N2.
- Legacy-HEAD matrix: **8 cases** (doctor, restore, Review 16 F6 regression, empty-ledger mismatch,
  downgrade laundering with and without format 2, other restore checks, non-resurrection, crash at
  both HEAD crash points).
- Counterfactual test runs: **5 neutralization modes**; every new test fails when the element it
  names is removed.
- Content-leak sweep over the new paths (guard error, unsatisfiable receipt, cancel, CLI stdout,
  `state/`, Vault): **0 hits**.

## Review 31 finding disposition

| Review 31 | Result | Evidence |
|---|---|---|
| F1 wedged purge | **Verified** | Guard at `src/aptuni/application/service.py:523-527` covers every canonical writer; `_purge_canonical` maps an unsatisfiable frozen scope to `failed_retryable` (`privacy.py:466-479`); `cancel_purge` (`privacy.py:579-593`) + `aptuni privacy purge cancel` (`cli/main.py:135,601-605`) release a wedged intent. Reproductions A and B below both terminate. |
| F2 legacy HEAD format | **Verified** | `_migrate_head_format()` (`vault/store.py:329-347`) restamps an unpurged format-1 HEAD and re-anchors a legacy purged one; `restore_from` accepts that artifact (`store.py:491`); `verify()` keeps the chain check live with no ledger excuse (`store.py:426,437-438`). Review 16 F6 is **not** reintroduced. ADR-0001 and ADR-0010 now record the change. |

### F1 — Reproduction A (Review 31, verbatim)

A concurrent owner memory decision interposed on the durable intent commit, via a local wrapper
around `privacy._write_private_json` — the same fault-injection style as Reviews 29–31:

```text
=== Reproduction A: concurrent owner memory decision interposed on the intent commit ===
  interposed decide_memory blocked: privacy_action_in_progress
  first attempt: complete_managed_external_action_needed
  retry 1: complete_managed_external_action_needed
  retry 2: complete_managed_external_action_needed
  candidate still present: False
  intent survives: False
  later canonical write: OK
  later independent purge: complete_managed_external_action_needed
```

Review 31's `InvariantError` is gone, the requested record is deleted, the intent is reaped, and
deletion is not disabled.

### F1 — Reproduction B (Review 31, verbatim)

`_load_or_commit_intent()` called directly to model a stop right after the durable intent commit,
then `memory_preview` + `decide_memory(accept)`, then resume:

```text
  intent_committed True
  decide_memory blocked: privacy_action_in_progress
  1: complete_managed_external_action_needed
  2: complete_managed_external_action_needed
  3: complete_managed_external_action_needed
  second purge: complete_managed_external_action_needed
```

The dependent write can no longer land, so the frozen scope stays satisfiable.

### F1 — guard completeness

Every `_commit` / `vault.commit` call site was enumerated
(`service.py:122,451,461,470,479,528`, `source_commands.py:112,141,162,233`,
`memory_commands.py:166,225,255`). All but two route through `AptuniService._commit()`; the
exceptions are `vault.purge()` inside `confirm_purge` and `restore_from()`, both deliberate, plus
the bootstrap policy commit in `init()` on a brand-new Vault. MCP has one write tool
(`aptuni_propose_memory` → `propose_from_host` → `observe` → `_commit`, `memory_commands.py:177-185`);
adapters write no canonical records. Observed with a durable intent in place:

```text
  remember: privacy_action_in_progress          sync (in-scope source): privacy_action_in_progress
  observe: privacy_action_in_progress           sync (unrelated source): privacy_action_in_progress
  correct: privacy_action_in_progress           propose_from_host (MCP): privacy_action_in_progress
  set_module: privacy_action_in_progress        add_folder_source: privacy_action_in_progress
```

Source sync still fails through its own pre-commit guard for an in-scope source
(`ingest.py:190-204`, `source_commands.py:185-190`) and through `_commit` for any other, so a
committed purge cannot be raced by replay either. No self-block or deadlock: `confirm_purge` calls
`vault.purge()` directly rather than `_commit()`, and with an intent present `doctor`/`verify`,
`recover()`, `Vault.open()`, `privacy status`, `search` and `restore_from` all still work
(`verify.ok=True`, restore published seq 7 cleanly). The documented lock order
`privacy -> source_operations -> per-source -> Vault writer` is now recorded in
`src/aptuni/vault/locks.py:15-19` (Review 31 N5).

### F1 — `cancel_purge` adversarial matrix

| Case | Observed |
|---|---|
| C1 replay a cancelled action id | `privacy_action_not_found` on confirm and on a second cancel; the record survives; the pending preview was consumed at intent commit, so nothing can be replayed |
| C2 cancel after partial managed cleanup (canonical `failed_retryable`, projection deleted) | allowed; the kept receipt reads `incomplete_retryable`; the candidate survives; the only destroyed copy is the derived projection — fail-safe direction |
| C3 crash between `vault.purge()` and the intent results write, then cancel | **allowed although canonical records were destroyed** — see N2 |
| C4 corrupt intent file | cancel `privacy_action_invalid`, confirm exits 1 with a content-free message, all writes blocked, a fresh purge blocked — no in-product remedy; see N3 |
| C5 four concurrent cancels | `['cancelled', 'privacy_action_not_found', 'privacy_action_not_found', 'privacy_action_not_found']` — the privacy flock serializes them |
| C6 canonical deleted + managed copy failed | `privacy_cancel_refused`, and the retry then completes (`complete_managed_external_action_needed`) |

`vault._purge_locked()` validates the kept set *before* appending the deletion ledger
(`store.py:450-452`), so an unsatisfiable scope leaves no half-applied ledger and `recover()`'s
ledger re-application does not fire. The `failed_retryable` result is therefore honest.

### F2 — legacy HEAD matrix

```text
F2-1 format-1 purged Vault:   verify.ok=True problems=()   migrated format=2, chain_base == legacy chain
                              second open verify.ok=True (idempotent), 2 records readable
F2-2 format-1 purged backup:  restore ok, seq=5, verify=True, kept record present
F2-3 format-2 tampered chain
     with a NON-EMPTY ledger: verify.ok=False ('hash chain does not match the committed segments')
                              migration left it alone (format stays 2)
F2-4 format-1 tampered chain
     with an EMPTY ledger:    verify.ok=False (same problem); HEAD left at format 1, not migrated
F2-6 legacy backup, other checks:
       corrupt-segment       rejected (VaultIntegrityError: segment hash mismatch)
       traversal             rejected (HEAD contains invalid fields or segment entries)
       invariant-violation   rejected (segment hash mismatch)   [live HEAD byte-identical in all three]
F2-7 non-resurrection via a legacy restore: purged record resurrected False, verify True
F2-8 crash at after_head_tmp / after_head_rename during migration:
       reopen: format=2 verify.ok=True records=2 unexpected=[]   (both points)
```

**F2-3 is the critical one:** Review 16 F6 is not reintroduced. The ledger excuse is gone from
`verify()` and the migration refuses to touch a format-2 HEAD, so a genuinely corrupted chain is
still reported even when the deletion ledger is non-empty — exactly the case the old excuse hid.

**Downgrade abuse.** An out-of-band writer who rewrites `HEAD.json` as format 1 with a mismatched
chain, while the ledger is non-empty, does get `_legacy_purged_head()` to re-anchor the manifest, and
the result verifies. Probed with four committed segments, dropping the newest:

```text
  A format-1 downgrade + dropped segment:      verify.ok=True problems=() format=2 records=3
  B format-2 forgery, no downgrade:            verify.ok=True problems=() format=2 records=3
```

The same attacker reaches the identical result in format 2 without any downgrade, because
`chain_base` lives in the same attacker-writable manifest — `HEAD.json` is self-attesting by
design (ADR-0001, 2026-09-19 acceptance: "The chain detects uninformed edits only"). The migration
therefore grants no capability the format-2 manifest did not already grant, and the writer is
outside core enforcement under ADR-0013 Decision item 1 ("Direct writes by a same-user process to
the Vault, config/grant/state or installed package are *outside core enforcement*"). Not a finding.

### Are the new tests real?

Each remediation element was neutralized at runtime through a pytest plugin (no source was
modified) and the seven new tests re-run:

| Neutralized | Tests that fail |
|---|---|
| `committed_purge_intent` → `False` | `test_durable_purge_intent_blocks_every_canonical_writer`, `test_purge_cancel_releases_a_wedged_intent` |
| `_purge_canonical` without the `InvariantError` catch | `test_unsatisfiable_intent_is_retryable_not_an_escaping_invariant_error` (raises `InvariantError: rev_… references missing records`), `test_purge_cancel_releases_a_wedged_intent` |
| `cancel_purge` removed | `test_purge_cancel_releases_a_wedged_intent`, `test_cancel_refuses_after_canonical_deletion_succeeded` |
| `_migrate_head_format` → no-op | `test_legacy_purged_vault_still_verifies`, `test_unpurged_legacy_head_is_migrated_to_the_current_format` |
| `_legacy_purged_head` → `False` (+ no migration) | all three `LegacyHeadFormatTests` |

None is tautological. The one weak test is `test_cancel_refuses_after_canonical_deletion_succeeded`,
which asserts a disjunction and in practice takes the `privacy_action_not_found` branch — see N4.

## Regression sweep

| Earlier finding | Result | Evidence |
|---|---|---|
| R1 post-preview managed copy | **No regression** | `retrieval_projection` still unconditional (`privacy.py:289-290`); C2 shows the projection deleted even when canonical fails; `test_projection_created_after_preview_is_still_invalidated` passes |
| R2 destructive pre-publication window | **No regression** | All six restore fault-injection tests in `tests/integration/test_vault.py` pass; a restore taken while an intent exists published seq 7 with `verify.ok=True` |
| R3 untrusted-name / data-class contract | **No regression, and extended** | Hostile root (newline, ESC, BEL, quote, backtick, `;`, Cyrillic `а`, `；`, `⁄`, RTL override): `privacy purge preview` prints one bounded JSON-delimited token with both flags, and `privacy status` now escapes too (Review 31 N2 half-applied); `source add-folder` still echoes raw — already in BACKLOG |
| B1 parent-symlink deletion | **No regression** | `test_parent_symlinks_never_delete_outside_owned_roots`, `test_source_parent_symlink_never_deletes_external_state` pass |
| B2 source sync after intent | **No regression** | Now blocked twice over (own guard + `_commit`), in scope and out |
| B3 exact managed-copy scope | **No regression** | `test_preview_deletes_only_exact_adapter_copies_and_preserves_external_details` passes |
| B4 CLI retry | **No regression** | `test_cli_exact_retry_resumes_incomplete_intent` passes; C6 retry after an injected managed-copy failure completes |
| B5 stale terminal intent | **No regression** | `test_terminal_receipt_reaps_surviving_intent` passes |
| B6 restore traversal | **No regression** | F2-6 rejects `../../outside.jsonl` with the live HEAD byte-identical, including for a legacy backup |
| B7 restore publication ordering | **No regression** | Superseded by R2 |

## Docs

- **ADR-0001 amendment** (2026-09-20, HEAD format 2) is accurate on every claim I could execute:
  format 1 stays readable (`SUPPORTED_HEAD_FORMATS`, `store.py:48`), a GENESIS-verifying format-1
  HEAD is restamped unchanged (F2 test 3 and my probe), a legacy purged HEAD keeps its recorded
  chain as the new anchor (F2-1: `chain_base == legacy chain` is `True`), `restore_from` accepts that
  artifact while still hash-verifying every segment and validating every record (F2-6), and a
  mismatch with an empty ledger stays a reported problem (F2-4).
- **ADR-0010 amendment** (2026-09-20, implemented purge contract) is accurate on the structured
  receipt fields, the every-writer guard, and the `incomplete_retryable` mapping. Its sentence
  "it refuses once canonical deletion has succeeded" is true of the *recorded* result but not of the
  crash window in N2; the ADR wording should follow whatever fix N2 gets.
- **README / README.zh-CN**: every command in both blocks exists and behaves as described. Run
  end to end: `privacy status` (14 rows, no record text), `purge preview` (exact record list,
  effects, external copies), interactive `confirm` requiring the literal `PURGE` (declining exits 1
  and changes nothing), the receipt printing per-copy results, `doctor` exiting 0 afterwards, and a
  post-purge content sweep over `state/` and the Vault returning zero hits. Both languages stay in
  sync. Review 31's copy nit survives and is now worse: the heading still says "Two commands" above
  a three-command block, and a fourth command (`cancel`) now exists and is not mentioned. N5.

## Blocking findings

None.

## Non-blocking notes

- **N1 — `check_relay` fails on two errors this diff introduced (must be fixed in the checkpoint
  commit).** Besides the three expected pending-lineage errors for reports 29/30/31, the check
  reports `extra blank line at EOF in docs/dev/BACKLOG.md` and `extra blank line at EOF in
  docs/research/findings/pitfalls.md`. Both files end with `|\n\n` in the working tree and `|\n` at
  `HEAD`, so the diff is the cause. The gate cannot be green at checkpoint until the trailing blank
  lines are removed; the lineage-manifest step will re-run the check anyway.

  A third, unrelated point for whoever runs that step: this report's mandated filename contains
  "remediation", and `tools/check_relay.py:168-176` globs `*remediation*.md` and classifies any such
  file as a remediation note, which must declare `- **Responds to:** ...` and must **not** carry a
  verdict line. A review report that ends in an anchored verdict therefore cannot satisfy that rule
  under this name. Rename it (for example `32-m1-privacy-purge-f1-f2-rereview.md`) and register it in
  `docs/dev/reviews/STATUS.json` with reports 29–31, or the two errors it raises are permanent.
- **N2 — `cancel_purge` can abandon a purge that already destroyed canonical records.** It decides
  from `results["canonical"]` inside the intent file (`privacy.py:589-592`), and that key is written
  only *after* `vault.purge()` returns (`privacy.py:565-567`). A crash — or any write failure such
  as ENOSPC — in that window leaves canonical deleted with `results == {}`. Reproduction:

  ```text
  === C3: crash between vault.purge() and the intent results write, then cancel ===
    canonical deleted: True
    intent results (crashed before write): {}
    cancel: ALLOWED although canonical records were destroyed
    receipt exists: False
    re-preview of the purged id: record_not_found
  ```

  The CLI then prints "No canonical record was deleted by it" (`cli/main.py:603`), which is false,
  and no terminal receipt is ever published for an action that did delete. A companion probe shows
  the frozen managed copies are also left behind: `state/projections/retrieval.sqlite` still held the
  purged statement text after the cancel (it is rebuilt, and the text gone, at the next `search`).
  Bounded rather than blocking: it needs a fault in a single narrow window plus the owner choosing
  cancel over retry; the deletion ledger *was* written before the segment swap, so non-resurrection
  and the deletion audit both hold; and the stale projection self-heals on the next retrieval.
  Fix: give `cancel_purge` the Vault and refuse when any frozen record digest is already in
  `ledger_digests()` (or when the frozen IDs are absent from the Vault), rather than trusting the
  recorded result; then align the ADR-0010 sentence.
- **N3 — an unreadable intent still wedges deletion with no in-product remedy.** With a corrupt
  `act-*.json`: `cancel` refuses (`privacy_action_invalid`), `confirm` exits 1, every canonical write
  is refused (`privacy_action_in_progress`, because `committed_purge_intent` counts any `act-*.json`,
  `privacy.py:374-376`), and a new purge is refused. The only way out is deleting the file by hand —
  the same shape as Review 31 N1, and non-blocking for the same reason: `_write_private_json` is
  atomic, so this needs out-of-band corruption or media damage (ADR-0013 item 1). Worth letting
  `cancel` release an intent it cannot parse (it proves nothing about canonical deletion either way,
  and refusing leaves no remedy at all), or letting `doctor` report and offer it.
- **N4 — the refusal branch is asserted but not exercised.**
  `test_cancel_refuses_after_canonical_deletion_succeeded` (`tests/integration/test_privacy_purge.py:472-482`)
  accepts `{"privacy_action_not_found", "privacy_cancel_refused"}`; because a complete purge reaps
  its own intent, the test always takes the `not_found` branch, so `privacy_cancel_refused` has no
  coverage. My C6 probe reaches it (canonical deleted + injected managed-copy failure → refused →
  retry completes); that scenario belongs in the test instead of the disjunction.
- **N5 — README copy.** "Two commands make that concrete" / "两条命令让这一点变得具体" now sits above a
  three-command block, and `privacy purge cancel` exists but is undocumented in both languages. Say
  "these commands", and add the cancel line with its one honest caveat.
- **N6 — a wedged action id is not discoverable from any product surface.** The
  `privacy_action_in_progress` message says "retry or cancel it" without naming the action, and
  `privacy status` lists the `privacy_actions` row by directory only — the `action_id` never appears
  (`action id discoverable from status output: False`). An owner who lost the id has to read
  `state/privacy/intents/`. Either name the blocking action in the error or add it to the inventory
  row.
- **N7 — `init()` bypasses the guard.** `service.py:122` commits the bootstrap policy through
  `vault.commit()` directly, so a stale intent in a reused state directory does not block creating a
  second Vault, and the surviving intent then blocks every write to the new one until it is
  cancelled. Cancel is a sufficient remedy, so this is only an edge worth a comment.
- **N8 — content leakage: none found.** Markers in a Fact statement, an observation and a note body
  were swept across the guard error, the unsatisfiable-intent receipt, `cancel`, the CLI stdout of
  every purge subcommand, all persisted intents and receipts, and every file under the state and
  Vault directories: zero hits. Error messages on the new paths are content-free, and a corrupt
  intent surfaces through `cli_run` as a bounded "Nothing was changed; run 'aptuni doctor'" line
  rather than a traceback.
- Review 31's N1 and N6, and the remaining Review 30 notes, are recorded in `docs/dev/BACKLOG.md`
  and are not re-raised here. Review 31 N2 is half-applied (`privacy status` escapes; `source list`
  and the add-source echoes still do not) and N3/N4/N5 are applied as described.

## Overall judgment

This round fixes both blocking findings with narrow, well-placed changes and no design churn. F1 is
closed at the right seam: the guard sits on the single shared commit path rather than on the writers
someone remembered, and all eight canonical write paths — including MCP and an unrelated source sync
— now fail closed while an intent is durable, so Review 31's Reproductions A and B both reach a
terminal receipt instead of an unrecoverable `InvariantError`. The unsatisfiable-scope case degrades
to a content-free `incomplete_retryable`, and because the Vault validates before it ledgers, that
result is honest rather than half-applied. The cancel path gives the feature the owner-facing exit
it lacked, refuses correctly once a canonical deletion is recorded, cannot be replayed, and
serializes under the privacy lock.

F2 is closed without giving anything back: a legacy purged Vault passes `doctor`, a legacy purged
backup restores with every segment hash, record invariant, traversal and non-resurrection check
still enforced, the migration is idempotent and survives a crash at both HEAD crash points — and,
critically, a format-2 Vault with a corrupted chain and a non-empty deletion ledger is still
reported, so Review 16 F6 stays fixed. The downgrade path an attacker could take through
`_legacy_purged_head()` buys nothing that the self-attesting format-2 manifest does not already
concede, and that writer is outside core enforcement under ADR-0013. The ADR-0001 and ADR-0010
amendments describe what the code actually does, and both READMEs document commands that exist and
behave as written.

What is left is small: a two-line whitespace fix so `check_relay` is clean at checkpoint (N1), a
cancel that should consult the deletion ledger instead of trusting a result it may not have written
yet (N2), and the usual coverage and copy tidying. None of it is a correctness, security, contract
or milestone-exit failure, and none of it needs another review round.

**Verdict:** **APPROVE WITH NON-BLOCKING NOTES**
