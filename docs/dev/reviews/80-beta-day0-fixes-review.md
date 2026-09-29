# Review 80 — Beta Day 0 fixes (`bb7b8cb..0bbed72`)

Independent review required by AGENTS.md (privacy/deletion, owner-confirmation rendering, canonical
invariants, backward compatibility). Reviewer did not modify source files.

## Scope

| Commit | Area |
|---|---|
| 41b27c2 | GitHub: skip blobs the tree reports > `MAX_BLOB_BYTES`; `GitHubApiError` during evidence fetch → `github_sync_failed` |
| b89dbb2 | setup apply continues past an unreadable source (`retry_later:`), journals and reports it; progress on stderr |
| bdb3411 | token-env line in the plan, `SETUP_TTL` 24 h, confirmed setups show no expiry |
| 06c2904 | `delimited_untrusted` shows CJK ideographs / kana / Hangul unescaped (ADR-0013 item 2 surface) |
| 027e511 | `aptuni status --lang` (moved to `cli/status_cli.py`), Agent guide text |
| 0bbed72 | ADR-0027 owner source removal: `source_removal.py`, `_check_source_removal`, `removed_source_ids`, `exposable()` filter, listing/lookup, purge scope, evaluation metric, CLI |

Consumers checked for source revocations: `revoked_ids`/`decided_candidate_ids` (memory, review,
promotion, profile promotion), `exposable()` and every search/context/identity path in
`service.py`, `export.py`, `obsidian_interface.py`, `evaluation.py`, `privacy.py`, MCP. Released
reader checked: `v0.2.0b3` source extracted outside the repo.

## Checks run

| Check | Result |
|---|---|
| `.tools/bin/uv run pytest -q` | 996 passed, 3 skipped, 62 subtests passed |
| `.tools/bin/uv run ruff check .` | All checks passed |
| `.tools/bin/uv run mypy src` | Success: no issues found in 107 source files |
| `python3.13 tools/check_relay.py` | relay check passed |
| Probe: allow-list enumeration (Python 3.13.3, Unicode 15.1) | 100 899 `Lo`, 3 `Lm`, **2 577 `Cn` (unassigned)**, **1 002 code points that NFC maps to a different allowed code point**; 0 format/space/punctuation; 0 non-wide |
| Probe: commit-time (`validate(only=…)`) after removal | new evidence superseding a retraction marker → `invariant_violation`; new subject → `invariant_violation` (sound) |
| Probe: dangling `review_event` + unrelated commit | `KeyError` escapes `_commit` (N1) |
| Probe: HEAD removes source → `v0.2.0b3` edits+syncs it → HEAD | b3 lists, syncs and exposes 2 new items; HEAD `doctor` fails, `create_backup` fails, `source remove` refuses (B2) |
| Probe: `status --json` | byte-identical keys/format to the previous `_print_json` path |
| Probe: mixin MRO | `vault`/`snapshot`/`policy_of`/`_commit` resolve to `AptuniService`, not the `SourceRemoval` stubs |

Probe scripts live only in the session scratch directory; nothing was committed.

## Findings

### B1 — BLOCK: the CJK allow-list shows 2 577 unassigned and 1 002 duplicate-identity code points unescaped and unflagged

`src/aptuni/cli/render.py:22-31` (`_READABLE`), `:34` (`_readable`), `:53` (flag suppression).

Structure cannot be forged: every allowed code point is `Lo`/`Lm`, East-Asian-Wide, not a quote,
backslash, newline, space or format character, and per-character `json.dumps` escaping is equivalent
to the old whole-string escaping. That part holds. But two sub-ranges are not "CJK ideographs, kana
and Hangul" in the sense the module docstring promises, and they bypass the ADR-0013 item 2
requirement "untrusted names, delimited and with confusables flagged":

- **Unassigned (`Cn`), 2 577 code points:** `U+FA6E-FA6F`, `U+FADA-FAFF`, `U+2A6E0-2A6FF`,
  `U+2B73A-2B73F`, `U+2B81E-2B81F`, `U+2CEA2-2CEAF`, `U+2EBE1-2EBEF`, `U+2EE5E-2F7FF`,
  `U+2FA1E-2FA1F`. They have no glyph; terminals draw an identical tofu or a blank double-width cell.
  So `"报告\U0002F000"` and `"报告\U0002F001"` render identically, and a blank rendering imitates the
  ideographic space U+3000 that the comment says is deliberately excluded. Neither gets a flag.
- **Canonical duplicates, 1 002 code points:** `U+F900-FAD9` (the assigned CJK Compatibility
  Ideographs) and `U+2F800-2FA1D` have singleton canonical decompositions: `U+F900` *is* `U+8C48`
  (豈) under NFC and is drawn the same. They are the textbook confusable, yet they render as-is with
  no `non-ascii/confusable-escaped` flag. That contradicts the commit title ("keep confusables
  escaped") and ADR-0013 item 2.

Reproduction:

```python
from aptuni.cli.render import delimited_untrusted
delimited_untrusted("豈")       # '"豈"'  (no flag; identical to "豈")
delimited_untrusted("\U0002EE60")   # '"\U0002ee60"' shown raw (unassigned; no flag)
```

Katakana/ideograph look-alikes (ロ/口, カ/力, ー/一) are inherent to showing CJK and fall within the
maintainer's decision. The two classes above are not needed to show a real CJK name, and excluding
them is a one-line change.

Suggested fix: allow a character only if it is in the listed blocks **and**
`unicodedata.category(c) in ("Lo", "Lm")` **and** `unicodedata.normalize("NFC", c) == c`, or drop
`(0xF900, 0xFAFF)` and `(0x2F800, 0x2FA1F)` and gate the rest on `category != "Cn"`. Python's own
Unicode database is the conservative choice: a code point Python does not know is escaped. Add cases
to `tests/unit/test_render_cjk.py` for `U+F900`, `U+2F800`, `U+FA6E`, `U+2EE60`, each asserting it is
escaped and flagged.

### B2 — BLOCK: a released reader can break the new hard invariant, and HEAD then has no non-destructive repair (backups fail)

`src/aptuni/domain/invariants.py:218-233` (`_check_source_removal`, enforced by full validation in
`vault/store.py` `verify` and `application/backup.py:147`), `src/aptuni/application/source_removal.py:84-85`
(a removed source can never be previewed again).

ADR-0027 picked Option C *because* "Beta users may run mixed versions". Option C is readable by
0.2.0b3, but 0.2.0b3 does not honor it, and the new invariant turns that into a stuck Vault:

1. HEAD: approve folder, sync, `source remove` + APPLY.
2. `v0.2.0b3` on the same Vault: `source list` still shows the source; after a file edit plus a new
   file, `aptuni sync SRC` writes 2 evidence items (one supersedes a retraction marker), and b3's
   `exposable()` returns them to agents.
3. HEAD: `doctor` → `removed source src_… still has current evidence`; `create_backup` →
   `backup_write_failed … the backed-up records do not verify`; `source remove SRC` →
   `source_removed`; `sync SRC` → `source_removed`.

HEAD's own defense in depth does keep those items away from HEAD's agents. But the owner cannot back
up the Vault any more, and the only way out is ADR-0010's irreversible purge: the outcome ADR-0027
exists to avoid. Steps 2's exposure through b3 is inherent to Option C and only needs documenting;
step 3's missing repair is a defect in this change.

Suggested fix (small; no schema change):
- Let `source_removal_preview`/`remove_source` accept an already-removed source when it still has
  non-retraction current evidence. Preview only those ids, bind the digest to them as today, and
  commit **only the retractions** (no second event). This satisfies both the existing "at most one
  event" rule and the current-evidence rule, so no invariant changes. The CLI can say "finish removing".
- Add a test that forges the b3 write through `Vault.commit`-bypassing segment append (or through
  `RecordSet` + the store's low-level append), then asserts `doctor` fails, the repair succeeds, and
  `doctor` and `create_backup` pass.
- ADR-0027 **Consequences**: state that 0.2.0b3 and earlier still list and sync a removed source and
  can expose what they newly read, that all installs should be upgraded before removing sources, and
  name the repair command.

### N1 — NOTE: `_check_source_removal` raises `KeyError`, not `InvariantError`, on a dangling target

`src/aptuni/domain/invariants.py:221` indexes `self._by_id[event.target_id]` for **every**
`review_event`, but under `validate(only=…)` missing links are only checked for the new records.
In a Vault that already has a dangling review event (one `doctor` would report), every later commit
now fails with an uncaught `KeyError` (`_commit` catches only `ConflictError`/`InvariantError`),
where before it succeeded. Reproduced with a synthetic dangling event. Fix: use
`self._by_id.get(event.target_id)` and skip `None`, as `removed_source_ids()` already does.

### N2 — NOTE: the `retry_later` writer is looser than the journal reader

`src/aptuni/cli/setup_apply.py:311-314` accepts any `str(error.__cause__)` that is Unicode
`isalnum()` + `islower()` with no length limit, but `setup.py` `SOURCE_RETRY_RESULT` only accepts
`[a-z0-9_]{1,80}`. A non-ASCII or >80-character cause would be journaled, and then the intent and
receipt would be rejected as `setup_action_invalid`, so setup could not be resumed or replayed. All
current causes are ASCII provider codes, so this cannot happen today. Fix: accept the cause only
if `SOURCE_RETRY_RESULT.fullmatch(cause)`, otherwise use `error.code`.

### N3 — NOTE: B5 disclosure is adequate; README wording lags

No *approval* failure can slip past. `source_*` steps still raise (`SetupError`/`AptuniError`)
and stop the run before `adapter`/`plugin_grant`. A planned source missing at sync time still returns
`failed:source_not_found`. An `OSError` from `sync` is not caught per source and still stops the run.
Per-source read failures are journaled, survive the receipt replay, appear in `results`, in
`source_failures` (JSON) and in a localized list with the retry and remove commands. The Agent guide
covers it too. Two gaps remain. `--json` still exits 0 with `terminal_state: complete` and
`failure: null`, so an agent must read `source_failures`: consider mentioning that key in
`agent-setup.md`. Also, `README.md:84` / `README.zh-CN.md:77` still say "If a step fails, the run
stops there" without saying that an unreadable source does not.

### N4 — NOTE: the token line says only private repositories are skipped; all of them are

`src/aptuni/i18n/messages/en.toml:197` and `zh-CN.toml:197`. `--github-token-env` applies to every
GitHub step (`setup_commands.py:477-478`), and `GitHubClient._headers` raises
`github_credential_unavailable` whenever the named variable is unset (`sources/github.py:217-220`).
So an unset variable skips **public** repositories in the plan too. The guide's "private repositories
need a token: add `--github-token-env`" has the same gap. Fix the wording, or fall back to anonymous
access for a public repository.

### N5 — NOTE: 0.2.0b3 cannot replay or cancel a setup that deferred a source

The new `sync:src_…` = `retry_later:…` journal/receipt entries are rejected by the released
`_validate_progress`. So a b3 install cannot `setup apply` (replay) or `setup cancel` an action that
HEAD finished with a deferred source. This only affects state files; worth one line in CHANGELOG/ADR.

### N6 — NOTE: minor ADR-0027 surface gaps

- `aptuni status` counts still include removed `source_config` records, while `source list` hides
  them. Label them or subtract them.
- `obsidian_snapshot()` `recent_changes` shows the source-removal event as a bare `revoke` item with
  no target kind. It is owner-facing only, and ADR-0027 anticipates this.
- `privacy.py:148` duplicates what `_required_by_selected` already adds (harmless).
- `source remove` has no `isatty()` guard (unlike `backup restore`), so `echo APPLY |` works. That is
  consistent with `memory forget`, and removal is reversible, so no change is needed.

### N7 — NOTE: owner screens are no longer ASCII-only in the `en` locale

`delimited_untrusted` can now emit non-ASCII under `en`. With a non-UTF-8 stdout (e.g.
`PYTHONIOENCODING=ascii`, a Windows redirect), `print` raises `UnicodeEncodeError` on a confirmation
screen where it used to be safe. zh-CN already had this exposure, and the Beta is macOS-only, so this
is low risk.

Verified sound (no finding): removal and sync share `source_operations_lock` + `SourceSyncLock`,
re-snapshot under lock, digest over the exact evidence ids, and `expected_seq` commit, so a stale
preview is refused. `exposable()` withdraws evidence by `provenance.source_id`, and every search,
context, semantic and export path filters through `exposable()` or through current, non-retraction
evidence. Memories and facts carry no source evidence (`evidence_ids=()`, observations only), so
nothing derived survives. Re-approval creates a fresh id with no dedupe against removed configs. A
purge of a removed source deletes the event, and `doctor` passes. `review_event` v1 with
`rationale_code: source_removed` parses in 0.2.0b3. The `status --json` output is unchanged. The GitHub
oversized skip and the `github_sync_failed` mapping are correct, and their i18n reasons exist.

Required to clear: B1 (tighten the allow-list, plus tests) and B2 (non-destructive repair of a
partially removed source, a test, and an ADR-0027 consequence line). N1–N7 go to BACKLOG.

**Verdict:** **BLOCK**
