# Review 81 — Re-review of the Review 80 fixes (`eda8cd4`)

Independent re-review required by AGENTS.md (owner-confirmation rendering, deletion/privacy,
canonical invariants, backward compatibility). The reviewer did not modify any source file. The
only file written is this report. `STATUS.json` was not edited.

## Scope

Verify that fix commit `eda8cd4` resolves Review 80 **B1** and **B2** correctly and completely, and
that it introduces no new correctness, security or contract regression. The same commit also carries
the note fixes N1 (`invariants.py`), N2 (`setup_apply.py`), N3 (README) and N4 (token wording), and
these were checked too. Settled items and Review 80 notes already moved to BACKLOG (N3 remainder,
N5–N7) were not reopened.

Files reviewed: `src/aptuni/cli/render.py`, `src/aptuni/application/source_removal.py`,
`src/aptuni/cli/source_remove_cli.py`, `src/aptuni/domain/invariants.py`,
`src/aptuni/cli/setup_apply.py`, `src/aptuni/i18n/messages/{en,zh-CN}.toml`,
`docs/dev/DECISIONS/ADR-0027-owner-source-removal.md`, `README.md`, `README.zh-CN.md`,
`docs/dev/BACKLOG.md`, `tests/unit/test_render_cjk.py`, `tests/integration/test_source_removal.py`.

## Checks run

| Check | Result |
|---|---|
| `.tools/bin/uv run pytest` | 1001 passed, 3 skipped, 62 subtests passed. This is Review 80's 996 plus 4 new B1 cases and 1 new B2 test. |
| `.tools/bin/uv run ruff check .` | All checks passed |
| `.tools/bin/uv run mypy src` | Success: no issues found in 107 source files |
| `python3.13 tools/check_relay.py` | relay check passed |
| Probe: exhaustive allow-list enumeration (Python 3.13.3, Unicode 15.1) | 99 900 allowed code points (99 897 `Lo`, 3 `Lm`). **0 `Cn`**, **0 NFC-changing**, **0 NFKC-changing**. 0 in categories Z/C/P/S/M, 0 quote/backslash/newline/tab, 0 ASCII, 0 non-East-Asian-Wide, 0 readable outside `_READABLE`. 3 579 excluded points in the ranges (2 577 `Cn` + 1 002 compatibility twins); all are escaped and flagged. The only survivors in `U+F900–FAFF` are the 12 unified ideographs with no decomposition (`FA0E, FA0F, FA11, FA13, FA14, FA1F, FA21, FA23, FA24, FA27, FA28, FA29`). None survive in `U+2F800–2FA1F`. |
| Probe: specific points | `U+F900` → `"豈" [non-ascii/confusable-escaped]` while `U+8C48` → `"豈"`. `U+FA6E`, `U+2F800`, `U+2EE60`, `U+3000`, `U+30FB`, `U+3099`, `U+309B`, `U+FF21`, `U+200B` and `U+11A8` are all escaped and flagged. `か+U+3099` renders `"が" [flag]`, distinct from precomposed `"が"`. |
| Probe: end-to-end mixed version, with `v0.2.0b3` in a `/tmp` git worktree and its own venv on a shared `APTUNI_STATE_DIR` | See B2 below. Reproduces the original failure, then confirms the repair. The worktree, venv and scratch Vault were removed afterwards (`git worktree list` shows only `main`). |
| Probe: N1 dangling `review_event` → `RecordSet._check_source_removal([])` | No `KeyError` |
| Probe: N2 `_failure_reason` with causes `github_credential_unavailable`, non-ASCII, 81 chars, 80 chars, empty, `None`, uppercase, colon | Every result satisfies `SOURCE_RETRY_RESULT` (valid causes are kept; the rest fall back to `error.code`) |

Probe scripts live only in the session scratch directory. Nothing was committed.

## Findings

### B1 — RESOLVED

`src/aptuni/cli/render.py:35-40`. `_readable` now requires three things: range membership, `unicodedata.category(c) in ("Lo", "Lm")`, and `NFC(c) == c`. The flag condition at `:56` uses the same
predicate. So every character that is not rendered raw is both escaped and flagged, and the two can
never disagree. The exhaustive probe matches the brief exactly: zero unassigned, zero NFC-changing,
and no format, space, punctuation, quote or newline character is allowed. Using the runtime's own
Unicode database is conservative. A code point that the running Python does not know is escaped.
`tests/unit/test_render_cjk.py:46-55` covers `U+F900`, `U+FA6E`, `U+2F800` and `U+2EE60`, which
are the four cases Review 80 requested.

### B2 — RESOLVED

`src/aptuni/application/source_removal.py:84-99`: `_preview` no longer refuses a removed source. It
computes `repair = source_id in removed_source_ids()` and still raises `source_removed` when there
is nothing left to withdraw. It binds the digest to `action: "source_remove_repair"` plus the exact
non-retraction evidence ids. `:69-72` commits **only** retractions (no event) under the same
`source_operations_lock` + `SourceSyncLock` + re-snapshot + `expected_seq` path. `_check_source_removal`
(`invariants.py:218-233`) is unchanged: exactly one removal event, and current evidence must all be
retractions. The repair satisfies both conditions, and no invariant was loosened. The retraction ids
`deterministic_id("evd", "remove:{digest}:{prev.id}")` stay unique across repeated repairs because
each `prev.id` is new. The digest domain (`source_remove` vs `source_remove_repair`) differs, so a
normal-removal digest can never apply as a repair or the reverse. `source_remove_cli.py:32` shows
`source.remove.repair`, which exists in both locales.

End-to-end reproduction (HEAD `eda8cd4` + released `v0.2.0b3`, one shared state dir):

1. HEAD: `init`, `source add-folder`, `sync` (2 items exposed), `source remove` + APPLY → 0 exposed,
   doctor ok.
2. b3: `source list` still shows the source. After editing `a.md` and adding `c.md`, `aptuni sync SRC`
   → `add=1, modify=1; evidence=2`, and b3 `search narwhal` returns the new item. This exposure is
   inherent to Option C and is now stated in ADR-0027.
3. HEAD: `doctor` fails, `create_backup` → `backup_write_failed`, `sync SRC` → `source_removed`, and
   HEAD `exposable()` stays `[]`. This reproduces the original failure.
4. HEAD: `source remove SRC` previews the repair text ("already removed … an older Aptuni version
   read it again and added 2 evidence items"). Cancelling writes nothing.
5. Stale preview: a repair preview is taken, b3 syncs a new file, and applying the old digest →
   `confirmation_stale`.
6. HEAD: `source remove SRC` + APPLY → "3 evidence items withdrawn". Now exactly **1** removal event
   exists, `doctor` ok, **`create_backup` ok**, `exposable()` is `[]`, HEAD and b3 `search` find
   nothing, and running `source remove` again → `source_removed`.
7. Second cycle: b3 syncs a new file (doctor fails again), then a HEAD repair withdraws 1 item.
   Doctor is ok, there is still 1 event, all record ids are unique, and nothing is exposed.

`tests/integration/test_source_removal.py:153-176` simulates the older build by monkeypatching
`removed_source_ids` and `_check_source_removal`. It asserts that doctor fails before the repair,
and that afterwards doctor passes, nothing is exposed, there is exactly one event, and a further
preview raises `source_removed`. `docs/dev/DECISIONS/ADR-0027-owner-source-removal.md:63-66`
records the consequence and names the repair.

### N1, N2, N3, N4 — RESOLVED

- N1 `invariants.py:221`: `getattr(self._by_id.get(...), "record_type", None)`. A dangling event no
  longer raises `KeyError`.
- N2 `setup_apply.py:316`: the writer now validates with the reader's own
  `SOURCE_RETRY_RESULT.fullmatch(RETRY_LATER + cause)`, so everything journaled can be replayed.
- N3 `README.md:84-86` and `README.zh-CN.md:77` now say that an unreadable source does not stop
  the run.
- N4 `en.toml:197` and `zh-CN.toml:197` now say that the GitHub repositories in the plan (not only
  private ones) are not read without the token.

### NOTE-1 — test gaps for B2 (non-blocking)

`tests/integration/test_source_removal.py:153`: the regression test does not assert
`create_backup` after the repair, and it does not cover a stale repair preview. Both were verified
by hand above (backup ok, `confirmation_stale`). Two assertions would pin them.

### NOTE-2 — repair screen and ADR wording (non-blocking)

`source.remove.repair` replaces `source.remove.effect`, so the repair screen drops the
`aptuni privacy purge preview` hint. The done line still says "Removed …". ADR-0027:63 says older
builds "can sync the source again". It does not say explicitly that they then expose what they read
to agents, or that all installs should be upgraded before a removal. Review 80 asked for that
sentence. The uncommitted `CHANGELOG.md` 0.2.0b4 draft in the working tree (outside `eda8cd4`)
does not mention the mixed-version caveat or the repair either.

### NOTE-3 — raw compatibility code points in test source (non-blocking)

`tests/unit/test_render_cjk.py:47-48` embeds literal `U+F900` and `U+FA6E`. An editor or tool
that NFC-normalizes files would silently turn `U+F900` into `U+8C48`. The test would then fail loudly
rather than pass falsely, but `"豈"` / `"﩮"` escapes would be sturdier.

No new correctness, security or contract regression was found in `eda8cd4`.

**Verdict:** **APPROVE WITH NON-BLOCKING NOTES**
