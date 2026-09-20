# Review 31 — M1 privacy purge second-remediation final re-review

**Date:** 2026-09-20

**Reviewer:** independent privacy/security final re-review agent (read-only except for this report)

**Scope:** the second remediation round for Review 30's R1/R2/R3, in the uncommitted working tree on
top of `0b0eabf`, including the untracked `src/aptuni/vault/locks.py` and
`tests/integration/test_privacy_purge.py`. The re-review read Reviews 29 and 30 and the full diff,
reproduced Review 30's three adversarial cases, fault-injected every restore boundary reachable
through `crash_hook` and the surrounding seams, re-probed Review 29's B1–B7, and swept the purge
flow for content leakage. Every probe ran in `tempfile.TemporaryDirectory()`; nothing was written to
the repository except this file, and no personal data was written anywhere. The tree also carries
uncommitted `README.md` / `README.zh-CN.md` edits documenting the two new commands; they were
checked against the shipped parser and are accurate (`cli/main.py:121-135`), claim no secure erasure,
name the copies Aptuni cannot delete, and stay in sync between the two languages — no finding, beyond
the copy nit that both say "Two commands" above a three-command block.

## Validation

- `.tools/bin/uv run pytest`: **332 passed, 47 subtests passed** in 34.26s.
- `.tools/bin/uv run ruff check .`: **All checks passed!**
- `.tools/bin/uv run mypy src`: **Success: no issues found in 58 source files**.
- Restore fault-injection matrix: **8 boundaries injected**; 7 reach one unambiguous generation,
  1 (staged segment removed out of band) leaves the Vault unopenable — see N1.
- Deadlock smoke (`sync` + `confirm_privacy_purge` + `doctor` + `privacy_inventory` + `search`
  concurrently): all five returned, no reverse acquisition observed.
- Content-leak sweep over stdout, `state/` and the Vault: **0 hits** for the note body and Fact text.

## Review 30 finding disposition

| Review 30 | Result | Evidence |
|---|---|---|
| R1 post-preview managed copy under a complete receipt | **Verified** | `retrieval_projection` is now an unconditional token (`src/aptuni/application/privacy.py:289-290`). Review 30's exact sequence now deletes the raw SQLite file and reports `deleted`. The adjacent copy classes are content-free; see the argument below and N3. |
| R2 destructive pre-publication window | **Verified** | The replacement segment is durable and the restore journal is written before any live state is touched (`src/aptuni/vault/store.py:460-486`); `_recover_restore_locked()` replays it from `recover()` (`store.py:296-297,322-362`). Review 30's `after_segment_tmp` case now preserves both HEAD and source replay state. |
| R3 untrusted-name / data-class contract | **Verified for the confirmation surface and receipt** | Provider, destination and data class are shown; destinations render through `_delimited_untrusted()` (`src/aptuni/cli/main.py:627-657`) and the persisted receipt keeps `provider`/`destination`/`data_class` structured (`src/aptuni/domain/records.py:299-306`). Other owner surfaces remain raw; see N2. |

### R1 — reproduction

Review 30's exact sequence (private Fact, no search, preview, then search, then confirm):

```text
projection_in_preview True
projection_exists_at_preview False
projection_created True
terminal complete_managed_external_action_needed
projection_survives False
projection_result deleted
```

The SQLite file is absent before the terminal receipt is published, so the receipt is honest.

I then probed the classes Review 30 flagged as sharing the gap. An adapter grant, bundle and pending
plan created after preview do survive the purge, and a memory confirmation created after preview
would too. **Leaving them out is defensible**, not an honesty defect: none of those files carries
record content. A grant holds `grant_id`/`host`/`destination`/`modules`/`scopes`, a bundle holds
`AGENTS.md` boilerplate plus an `mcp_servers` stanza, a pending plan holds the same authorization
fields, and a memory confirmation holds `kind`/`target_id`/`policy_epoch`/`nonce_id`/`expires_at`.
A sweep for a unique marker across the whole state directory after applying a grant post-preview
returned `state_files_with_marker_after_apply []`. They are authorization and nonce state, not
copies of the purged text, and the deletion ledger blocks resurrection of any record they name. The
exact-snapshot semantics chosen in the first remediation are therefore coherent. The generic prose
line "adapter grants/bundles/pending plans: revoke and delete" (`privacy.py:325`) over-claims
relative to that exact set; that is N3.

### R2 — fault-injection matrix

Live Vault at seq 2 (one purge applied), a valid backup at seq 1, and a live
`Aptuni/sources/src_...001.json` marker. After each injected failure the Vault was reopened with
`Vault.open()` (which runs `recover()`), then `head()`, `verify()` and `read_all()` were checked.

| Injected at | Journal after fault | Source state after fault | After reopen |
|---|---|---|---|
| `after_segment_tmp` | absent | present | seq 2 (old generation), verify ok, no journal, source state intact |
| `after_segment_rename` | absent | present | seq 2 (old generation), verify ok, no journal, source state intact |
| after journal write | present | present | seq 3 (restored), verify ok, journal removed, source state cleared |
| mid `_clear_source_state` | present | partially cleared | seq 3 (restored), verify ok, journal removed, source state cleared |
| `after_head_tmp` | present | cleared | seq 3 (restored), verify ok, journal removed |
| `after_head_rename` | present | cleared | seq 3 (restored), verify ok, journal removed |
| before journal unlink | present | cleared | seq 3 (restored), verify ok, journal removed |
| staged segment removed out of band, journal present | present | present | **reopen fails**: bare `FileNotFoundError` (N1) |

In every reachable case exactly one generation is live, `verify()` is clean, `unexpected_files()` is
empty, and the source replay state agrees with the canonical generation: it survives when the old
generation survives and is gone when the restored generation is published. Review 30's exact case
now reports `head_unchanged True` **and** `source_state_survives True`. Non-resurrection also holds
across restore: `obs_...002`, purged before the backup was published, is absent from every restored
generation, and `recover()` re-applies the ledger after journal replay (`store.py:299-304`).

### R3 — reproduction

Folder source root containing a newline, ESC, BEL, a double quote, a backtick, a semicolon, Cyrillic
`а`, fullwidth `；`, fraction slash `⁄` and an RTL override. `aptuni privacy purge preview` printed
one bounded, JSON-delimited, ASCII-only token on a single line:

```text
External copies requiring user action: 1
  source_original:src_...  provider=folder  data_class=original_source_unmodified  destination="/.../src\n[31mFAKE Effects: \"q\" `bt` ;rm -rf ~ аpple；⁄etc‮" [control-escaped, non-ascii/confusable-escaped]
```

Both flags are present, the data class is shown, and the raw path never reaches the terminal. The
persisted receipt keeps the fields structured rather than flattened into `details`:

```json
{"copy_class": "source_original:src_...", "data_class": "original_source_unmodified",
 "destination": "/.../src\n[31mFAKE ...", "details": null, "provider": "folder",
 "result": "external_action_needed"}
```

and `_cmd_privacy_purge` prints provider, data class and the escaped destination for every external
entry (`cli/main.py:620-623`).

## Review 29 finding disposition (regression check)

| Review 29 | Result | Evidence |
|---|---|---|
| B1 parent-symlink deletion | **No regression** | `state/adapters -> external`: `terminal incomplete_retryable`, `external_marker_survives True`, `external_grants_dir True`. `vault/sources -> external`: `incomplete_retryable`, `external_marker_survives True` (`privacy.py:234-248,368-376`). |
| B2 source sync after intent | **No regression** | Durable intent then `sync`: `AptuniError privacy_action_in_progress`; the resumed purge reached `complete_managed_external_action_needed` with `evidence_left []` (`ingest.py:190-204`, `source_commands.py:185-190`). |
| B3 exact managed-copy scope | **No regression; scope now coherent** | Exact IDs and digest-bound external metadata; see R1 above and N3. |
| B4 CLI retry | **No regression** | One-shot `SqliteProjection.delete` failure: `first exit 2`, `retry exit 0` on the same action and digest. |
| B5 stale terminal intent | **No regression** | Recreated intent bytes after a terminal receipt: replay returns the receipt, `stale intent survives False`, and a later independent purge completes. |
| B6 restore traversal | **No regression** | `../../external-N.jsonl` HEAD rejected with `HEAD contains invalid fields or segment entries`; live HEAD byte-identical (`store.py:118-145`). |
| B7 restore publication ordering | **Fixed** | Superseded by R2 above. |

## Blocking findings

### F1 — A concurrent owner memory decision after the durable intent wedges the purge permanently

`confirm_purge()` commits the intent (`src/aptuni/application/privacy.py:440-442`) and then purges
exactly the record IDs frozen at preview (`privacy.py:544-547`, `store.py:405-415`). The second
remediation added a durable-intent guard for **sources only** (`ingest.py:190-204`); nothing stops
the memory lifecycle from writing new canonical records that reference an in-scope record after the
intent is durable. `Vault._unlink()` strips `evidence_ids`, `memory_ids`, `derived_from`,
`contradicts` and `supersedes` (`store.py:501-513`) but not `ReviewEvent.target_id` or
`Memory.candidate_id`, so `RecordSet(kept).validate()` (`store.py:415`) raises and never recovers.

Reproduction A — no crash at all, just a concurrent owner command landing between the intent commit
and the canonical purge. The write was interposed with a local wrapper around
`privacy._write_private_json`, the same fault-injection style Reviews 29 and 30 used:

```text
first attempt: confirmation_stale
retry 1 raised InvariantError rev_... references missing records: ['cnd_...']
retry 2 raised InvariantError rev_... references missing records: ['cnd_...']
later purge blocked: privacy_action_in_progress
```

Reproduction B — the Review 29 B2 crash model (`_load_or_commit_intent()` called directly to model a
stop right after the durable intent commit), then `memory_preview` + `decide_memory(accept)`, then
resume:

```text
intent_committed True
accepted_memory mem_...
1 raised InvariantError rev_... references missing records: ['cnd_...']
2 raised InvariantError rev_... references missing records: ['cnd_...']
3 raised InvariantError rev_... references missing records: ['cnd_...']
cli raised InvariantError rev_... references missing records: ['cnd_...']
second purge blocked: privacy_action_in_progress
records still holding the statement: ['obs_...', 'cnd_...', 'mem_...']
```

Three failures at once:

1. **The requested deletion can never complete.** The owner asked for the candidate to be purged;
   after this window every retry of the same exact action and digest raises the same error forever.
2. **Every future purge is blocked.** The surviving intent makes `_load_or_commit_intent()` reject
   all new actions with `privacy_action_in_progress` (`privacy.py:429-432`). There is no
   `privacy purge cancel` subcommand, and `_reap_terminal_intents()` only reaps intents that already
   have a terminal receipt (`privacy.py:405-417`), so the whole deletion feature is permanently
   disabled with no owner-facing remedy.
3. **No terminal receipt and no content-free error.** A raw `InvariantError` escapes the application
   service straight through `cli_run` as a traceback. ADR-0010 requires that every purge reaches an
   explicit terminal state (`complete_managed`, `complete_managed_external_action_needed` or
   `incomplete_retryable`) and that fault injection on every purge step proves safe retry/status
   (ADR-0010 lines 56-57, 79). Neither holds here.

It fails closed on confidentiality — nothing leaks and no false "complete" receipt is published —
but it is a correctness and milestone-exit failure of the slice's core capability. Remediation must
either extend the durable-intent guard to every canonical writer that can reference an in-scope
record, not only source sync, or re-expand the frozen scope under the writer lock before the
canonical purge and stale the action when the reachable set changed. In all cases an unsatisfiable
intent must map to a content-free `incomplete_retryable` (or an explicitly cancellable state)
instead of an escaping `InvariantError`. Add both reproductions above to the purge fault-injection
matrix.

### F2 — The HEAD format 1 to 2 migration breaks `doctor` and restore for any Vault purged by the previous code

`HEAD_FORMAT` moves from 1 to 2 and `chain_base` is added (`src/aptuni/vault/store.py:47-48,70`).
`_parse_head_value()` accepts format 1 and defaults `chain_base` to `GENESIS`
(`store.py:118-145`), while `verify()` dropped the old ledger excuse and now always reports a chain
mismatch (`store.py:399-400`). Under the previously shipped code a purge re-based the chain onto the
pre-purge value with no `chain_base` field, so those two changes contradict each other: format 1 is
claimed as supported, but the one case that needed the excuse is now rejected.

Reproduction — the same purge, with the HEAD rewritten to exactly the artifact the previous code
produced (format 1, no `chain_base`, chain re-based):

```text
new-code HEAD: {'format': 2, 'seq': 2, 'chain': '5c837fba...', 'chain_base': 'ceb6987a...'}
legacy format-1 purged Vault: verify.ok = False
problems: ('hash chain does not match the committed segments',)

=== restore from a format-1 backup that was purged by the previous code ===
restore REJECTED: restore backup hash chain does not match its committed segments
```

`doctor` now declares a healthy Vault corrupt, and — the serious half — a **backup taken after a
purge under the previous code can no longer be restored at all** (`store.py:449-453`). That is a
recovery failure on the exact path ADR-0010 exists to protect, and there is no migration step: no
code reads a format-1 HEAD and derives or records a correct `chain_base`.

Remediation: on open, migrate a format-1 HEAD (derive `chain_base` from the committed segments so
the recorded chain verifies, and rewrite it as format 2), or keep the format-1 ledger excuse in both
`verify()` and `restore_from()`. Add a format-1 purged-Vault fixture covering `doctor`, `recover()`
and `restore_from` — Review 29 already asked for format-1 purge and restore tests and they are still
missing. Independently of the code fix, this is a canonical-schema change, and the AGENTS.md
invariant is explicit that public schemas never change silently: nothing in `docs/dev/DECISIONS/` or
anywhere else under `docs/` mentions `chain_base` or HEAD format 2. Amend ADR-0001/ADR-0010, or add
an ADR, before the checkpoint.

## Non-blocking notes

- **N1 — A journal that cannot replay leaves the Vault unopenable with no product remedy.**
  `_recover_restore_locked()` validates the journal inside a `try` that catches
  `json.JSONDecodeError`, `KeyError`, `TypeError` and `ValueError`, but `self._read_segments(new_head)`
  (`store.py:347`) can raise `FileNotFoundError`, which escapes. Reopening then fails for every
  command, including `doctor`, which itself calls `Vault.open()`. Data is intact — the old HEAD and
  old segments are untouched — but the only way out is deleting `state/restore-intent.json` by hand.
  The staged segment is made durable before the journal, so this needs out-of-band deletion or media
  damage, which is outside core enforcement under ADR-0013 item 1; hence non-blocking. Fold
  segment-read failures into the journal validation and distinguish "journal not applicable, keep the
  old generation" (old HEAD still live) from genuine corruption (new HEAD live, segment gone). The
  same applies to the `VaultIntegrityError` path for a stale or mismatched journal.
- **N2 — Escaping is applied only on the purge surfaces.** `aptuni privacy status` prints
  `inventory_item.location` raw (`cli/main.py:590-591`), and so do `source list` and the
  `source add-folder` / `add-github` echoes (`cli/main.py:290,305,316`). With the hostile root above,
  `privacy status` emits a live ESC sequence, a BEL, a real newline that splits the row onto a second
  line, and an unflagged RTL override. ADR-0013 item 2 makes delimiting and confusable flagging
  normative for the **confirmation** surface, which is now compliant, so this is a consistency and
  defence-in-depth gap rather than a contract violation — but the inventory is what the owner reads
  to decide *what* to purge, and a forged row can hide or invent a copy. Route every owner-facing
  render of a source-controlled name through `_delimited_untrusted()`.
- **N3 — The generic effect prose over-claims relative to the exact snapshot.** `copy_effects`
  still promises "adapter grants/bundles/pending plans: revoke and delete" (`privacy.py:325`) while
  `managed_copy_ids` is an exact frozen set and a grant created after preview is deliberately
  preserved (asserted by
  `test_preview_deletes_only_exact_adapter_copies_and_preserves_external_details`). Reword the effect
  lines to say "exactly the copies listed below", so the prose and the enumerated set cannot disagree.
- **N4 — A `state/projections` alias makes preview raise a bare `OSError`.**
  `_snapshot_copy_scope()` calls `_owned_child()` outside any handler (`privacy.py:289`), so
  `aptuni privacy purge preview` surfaces `OSError: owned_parent_is_symlink` instead of a
  content-free `AptuniError`. It fails closed and the external directory survives, but the error
  shape is wrong on a user-reachable path. Review 30's note about consistent alias rejection for the
  privacy root still stands.
- **N5 — Lock ordering is consistent and no deadlock was found.** The observed order is
  `privacy -> source_operations -> per-source -> Vault writer`: purge (`privacy.py:530,535`), sync
  (`source_commands.py:187`), restore and `recover()` (`store.py:296,456`). `SourceCommands.sync()`
  and `AptuniService.confirm_privacy_purge()` both open the Vault before taking
  `source_operations_lock`, which is what keeps `Vault.open() -> recover()` from re-entering it on a
  second descriptor. That ordering requirement deserves a comment beside `source_operations_lock` in
  `src/aptuni/vault/locks.py` so a later refactor does not lose it.
- **N6 — `_delimited_untrusted()` flags all non-ASCII as confusable** (`cli/main.py:652-653`), so an
  ordinary CJK or accented folder name is labelled `non-ascii/confusable-escaped`. Conservative and
  safe, but a narrower confusable/bidi check would keep the flag's signal value.
- **N7 — Working-tree hygiene.** `notes.md` and `task_plan.md` sit untracked at the repository root
  and are not ignored; per the workspace conventions these belong under `/plan` or `/temp`, or should
  be removed before the checkpoint. Also, `tests/integration/test_vault.py` places
  `if __name__ == "__main__": unittest.main()` above `class OpenTests`, which is harmless under
  pytest but confusing.
- **N8 — Content leakage: none found.** A sweep with unique markers in a note body and a Fact
  statement across `privacy status`, `privacy status --json`, `privacy purge preview`,
  `privacy purge confirm` (human and `--json`), the persisted receipts, the durable intents, the
  inventory and every file under the state and Vault directories returned zero hits.
- Review 30's remaining notes still apply: `_preview_from_dict()` coercion and unvalidated intent
  result values (`privacy.py:92-128`), and the non-descriptor-relative `_owned_child()` TOCTOU.

## Overall judgment

The second remediation round is real work and closes all three of Review 30's findings. The
retrieval projection is now unconditionally invalidated and the receipt is honest about it; restore
stages its replacement and journals its intent before touching any live state, and every reachable
crash boundary reopens onto exactly one generation with replay state that agrees with it; and the
confirmation surface and the persisted receipt now meet ADR-0013 item 2 for provider, destination,
data class and escaped untrusted names. Review 29's B1–B7 all survive the round, lock ordering is
consistent, and nothing leaks.

The slice still cannot checkpoint. The durable-intent guard was extended to source sync only, and an
ordinary concurrent owner memory decision — no crash required — leaves a purge that can never
complete, permanently blocks every future purge with no cancel path, and surfaces a raw
`InvariantError` instead of the terminal state ADR-0010 requires. Separately, the unrecorded HEAD
format 1 to 2 migration makes `doctor` declare a legitimately purged legacy Vault corrupt and makes a
legacy post-purge backup unrestorable, which is a recovery failure on the very path ADR-0010 governs.
Both are narrow and mechanically fixable, and neither reopens the design of the remediation.

**Verdict:** **BLOCK**
