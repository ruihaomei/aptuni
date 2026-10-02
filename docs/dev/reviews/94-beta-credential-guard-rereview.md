# Review 94 — Credential guard re-review: Review 93 remediation and targeted credential-history purge (ADR-0031 amendment)

- **Scope:** commit `ff3e396` ("fix(privacy): close Review 93 credential guard gaps (ADR-0031
  amendment)") against its parent `94c025d`: `src/aptuni/policy/secrets.py`,
  `src/aptuni/application/credential_guard.py`, `source_removal.py`, `source_authority.py`,
  `source_commands.py`, `ingest.py` (`SyncReport.withheld_items`), `privacy.py`
  (`credential_history_scope`, `_expand_purge(source_scope=False)`, `create_purge_preview`),
  `service.py` (`privacy_purge_preview(credential_history=True)`, identity card, `retract`,
  `_credential_records`), `cli/main.py`, `mcp/server.py`, the new tests, ADR-0031 "Amendment
  2026-10-02" and the CHANGELOG entry. Narrow re-review of Review 93 B1–B3 and N1/N3, plus the new
  targeted purge. The untracked `.agents/skills/` directory and the untracked Chinese-named `.txt`
  file are unrelated user files and were not read.
- **Policy:** AGENTS.md. A finding BLOCKS only for correctness, security/privacy, contract or
  milestone-exit failures. Everything else is a non-blocking note for `docs/dev/BACKLOG.md`.
- **Probes:** throwaway scripts in `/private/tmp/claude-501/rr94/` against temporary Vaults created
  there, with synthetic secret values only. The owner's Vault and
  `~/Library/Application Support/aptuni` were not read. No source or test file was modified (one
  probe monkeypatched `_FIELD` in-process through a `-p` plugin outside the repository).

## Commands and results

| Command | Result |
|---|---|
| `.tools/bin/uv run pytest` | exit 0; 1240 passed, 3 skipped (1243 collected) |
| `.tools/bin/uv run ruff check .` | All checks passed |
| `.tools/bin/uv run mypy src` | Success: no issues found in 122 source files |
| `python3.13 tools/check_relay.py` | relay check passed (before and after registering this review) |

## Probes

| Probe | Result |
|---|---|
| `credential_kinds` on 35 synthetic positives (decorated, quoted, env, table, URL, PIN, prose …) | 25 detected. All Review 93 B1 layouts hit (`**Password**:`, `- **密码**：`, `` `api_key`: ``, JSON, Python, YAML, TOML, `DB_PASSWORD=`, `GITHUB_TOKEN=`, `export OPENAI_API_KEY=`, `\| password \| v \|`). Missed: `**Password:** v` and `**密码：** v` (separator inside the emphasis), a header-column table **after whitespace collapsing**, `<b>Password</b>:`, `## Password⏎v`, `Password - v`, prose, lowercase words, `888888` (B1, N3) |
| Same detector on 89 synthetic negatives (Review 93 N2 cases, code, paths, dates, templates, ML/tokenizer notes, hashes, UUIDs) | Every Review 93 N2 false positive is fixed. 19 new false positives, all from the new bare `token`/`secret` labels and the unchanged value rule (N1) |
| Folder sync of 8 notes holding one synthetic secret in different layouts | 3 withheld (`**Password**:`, JSON block, `.env` block). **4 ingested as current Evidence holding the secret**: `- **Password:** v`, `**密码：** v`, `\| Site \| User \| Password \|` table, `\| 网站 \| 账号 \| 密码 \|` table. `context("password bank account", include_evidence=True)` returns 1 item holding the secret with `withheld_credentials=0` (B1) |
| Worst case: 20k/60k/120k characters against every regex (`a.a.a.`, `a_` chains, `ab_…password`, repeated labels, `\|` runs, scheme chars, `eyJ`, `Bearer`, CJK labels) | Linear; ≤ 26 ms at 120k characters. Table parser with a wide credential header and many rows is O(columns × rows): 2k×10k 0.70 s, 5k×25k 4.3 s, 10k×50k 18.5 s (N2) |
| Prototype: `_FIELD` also tolerating up to three emphasis/code characters **after** the separator | Catches both `**…:**` forms; no new false positive on the 89 negatives; `**Password:** ********` / `*see vault*` / `_TBD_` stay clean; `test_secrets.py` and `test_credential_containment.py` pass with it patched in |
| Source removal of a folder with legacy credential Evidence (M3) | Removal retractions hold no secret; only the pre-guard original does (B2 closed) |
| Authority grant on a MarginNote source with legacy credential Evidence, before any sync (M2) | 12 new records, none holds the secret; no current Fact holds it; `validate()`/`doctor` pass (B2 closed) |
| Reclassify with current legacy credential Evidence (M5); clean card edit after sweep (M4) | No new record holds the secret (holder count unchanged); no current Fact holds it |
| `aptuni retract` of a credential Fact | Writes `Retracted: [credential withheld]` |
| Owner CLI `sync` and `sync --json` | Lists `info.txt` / MarginNote note ids, never text; a file **named** with a credential is listed as the opaque `folder-<hash>` subject id (N4) |
| S1 folder: legacy credential file still present → sweep → `--credential-history` purge → unchanged sync → clean edit → credential edit | Purge takes exactly assert + sweep retraction, `source_ids=()`, managed copies = projections only. Unchanged sync writes nothing; clean edit is a fresh `assert` with `supersedes=()`; credential edit is withheld with nothing written. `validate()` and `doctor` pass at every step; no record holds the secret |
| S2 folder: file deleted → purge → same path re-created with a credential, then clean | Re-created credential withheld (no record); clean version a fresh lineage; invariants and `doctor` pass |
| S3 owner-typed credential Fact, module exposed | Preview refused `nothing_to_purge` (correct) |
| S3 same Fact after `set_module("knowledge", expose=False)` | **Selected and erased although current** (B2-new) |
| S3c credential Fact corrected to a clean statement, module not exposed | **Purge erases both, including the clean current Fact**; after re-exposing the module the Profile has no Fact left (B2-new) |
| S3b credential Fact retracted, another corrected (module exposed) | Retracted chain erased; the corrected chain with a clean current version is kept |
| M1 MarginNote studied card titled with a credential, pre-ADR derived Profile Fact → sweep → purge → clean card edit | Purge takes 2 assert + 2 sweep retractions + 2 withdrawn derived Facts + their 2 promotion events, all non-current; clean edit re-derives both Facts (ledger-aware ids, no commit refusal); `doctor` passes |
| C1 sync crashes after canonical commit (sweep retraction + clean edit of another file), then `--credential-history` purge, then sync ×2 | Purge succeeds; **every later sync fails `source_recovery_failed` ("partial canonical commit")**; `doctor` reports ok (B3-new) |
| C2 same crash, delta holding only the sweep retraction | Recovers: pending cleared, item withheld again, next sync clean |

## Blocking findings

### B1 (reopened, narrowed) — Two common Markdown credential layouts still reach Agents, and the table rule never runs on real Evidence

Review 93 B1 required decorated labels to be detected and coverage to be stated honestly. Two
layouts still pass end to end (reproduced through a folder sync and Context above):

1. **Separator inside the emphasis.** `- **Password:** <secret>` and `**密码：** <secret>` are as
   common in Markdown/Obsidian notes as `**Password**: <secret>`. `_FIELD`
   (`src/aptuni/policy/secrets.py:40`) allows decoration only between the label and the separator,
   so the captured value is the closing `**`, which is not secret-shaped.
2. **Header-column tables.** `_table_has_secret` (`secrets.py:84-97`) splits on newlines, but every
   source collapses all whitespace into single spaces before the guard sees the text (`ingest.py:270`
   folder, `:431` GitHub, `obsidian_ingest.py:36`, `notion_ingest.py:29`) and Context units carry the
   same excerpt. The rule therefore only fires in unit tests on raw multi-line strings. A password
   table `| Site | User | Password |` / `| 网站 | 账号 | 密码 |` is ingested, exposable and returned
   by Context, while ADR-0031 Amendment item 1 and the CHANGELOG ("… and Markdown tables") tell the
   owner such tables are kept out.

Required: tolerate emphasis/code after the separator as well (the prototype above costs no
precision on the probe corpus and passes the existing tests); make the table rule work on
whitespace-collapsed text (for example, infer the column count from the `|---|---|` run and read the
following cells in groups of that size) or drop the claim from ADR-0031 and the CHANGELOG and list
header tables under Residuals. Add tests that go through a folder sync (or at least through
`" ".join(text.split())`), not only `credential_kinds` on raw text.

### B2-new — `--credential-history` erases current records that are merely not exposable

`credential_history_scope` (`src/aptuni/application/privacy.py:271-282`) treats a closure as
"withdrawn" when it contains nothing in `records.exposable()` and no current non-retraction
Evidence. `exposable()` also excludes **current** records in a module whose `expose_enabled` is off,
records in `pending_review`/`quarantined` state, and every record type outside
`EXPOSABLE_TYPES` (for example a pending `candidate_memory`). Reproduced: with the knowledge module
not exposed, a current owner Fact holding a credential is selected and erased; and a credential
Fact the owner had corrected to a clean statement is erased **together with its clean current
successor**, so the Profile loses a current, credential-free Fact irreversibly. This contradicts
ADR-0031 Amendment item 6 ("A chain with a current version … is not selected, because erasing it
would remove the clean current note") and the preview's own refusal message, and the preview shows
only ids and counts, so the owner cannot notice before typing `PURGE`.

Required: compute "current" independently of exposure and review state — every record that is not
superseded, not a retraction and not withdrawn by a reject/revoke review (current Facts including
Evidence-profile Facts with current support, current Evidence, accepted Memories, undecided
candidates and observations) — and refuse any candidate whose closure contains one. Add a test with
`expose=False` and a corrected chain, and one with a pending candidate.

### B3-new — A targeted purge after an interrupted sync wedges the source permanently

The source-wide ADR-0010 purge deletes `source_state:<id>:pending`; `source_scope=False` leaves
`source_ids` empty, so the pending replay state of an interrupted sync survives while the purge
erases some of its `expected_evidence_ids`. `_recover_pending`
(`source_commands.py:372-392`) then sees a partial commit and raises `source_recovery_failed` on
every later sync (reproduced, C1); `doctor` still reports ok. The only ways out are a source-wide
purge or removing the source — exactly what the targeted purge exists to avoid. ADR-0031 Amendment
item 6 claims the targeted purge is safe through the existing machinery.

Required: for every source of a selected Evidence record, either include its
`source_state:<id>:pending` copy in `managed_copy_ids` (the replay then simply rescans, as C2 shows)
or refuse the preview while that source has a pending state ("sync this source first"). Add a test
that interrupts a sync after its canonical commit, purges, and syncs again.

## Non-blocking notes

- **N1 — New false positives from bare `token`/`secret` labels.** Synthetic examples now withheld:
  `token: GPT-4o`, `token: v2.1.0`, `Token: NeurIPS2024`, `token: GPT2Tokenizer`, `token: Hello123`,
  `eos_token = tokenizer.eos_token`, `secret: x86_64`, `The secret: AlphaFold2 uses MSAs`,
  `api key: OpenAI-compatible`, `access token: OAuth2-flow`, `Secret: Santa2024 …`, and a git SHA,
  UUID or short hex after `token:`/`secret:`. ML and code notes use these labels often. The owner can
  now locate such items, so the cost is lower; consider requiring a stronger value for bare
  `token`/`secret` (≥ 16 characters, or digit + symbol) and skipping attribute access (`a.b`),
  version strings, UUIDs and hex digests.
- **N2 — Table parser is not linear.** `_table_has_secret` is O(credential columns × rows): 18.5 s on
  a 10k-column × 50k-row adversarial input. All callers pass ≤ 500 characters today, so this is not
  reachable from a host; cap the column list or the input, and correct "Every rule is linear" in the
  ADR.
- **N3 — Residuals to add to ADR-0031:** `<b>Password</b>:`, a label on its own heading line
  (`## Password` then the value), separator `-`/`→`.
- **N4 — A file named with a credential is unlocatable.** Its relative path is (rightly) not printed,
  so the location falls back to the opaque `folder-<hash>` subject id. Print a hint (for example the
  parent directory, if credential-free) or say "a file whose name holds a credential".
- **N5 — CLI wording.** `aptuni privacy purge preview` with neither ids nor `--credential-history`
  says "Give exact record IDs or --credential-history, not both."
- **N6 — ADR detail.** Amendment item 4 says the count stays in "the SDK response object"; the
  public v1 `ContextResult` carries no count (only the internal `ContextResponse` does). That is the
  safer behaviour; adjust the wording.
- **N7 — Preview cost.** `credential_history_scope` runs a full `_expand_purge` per candidate
  (O(candidates × records × rounds)); fine at today's 2 hits, slow on a false-positive-heavy Vault.
- **N8 — Sync during a committed targeted intent.** `source_has_committed_purge` cannot see a
  targeted intent (`source_ids=()`), so a sync scans and saves pending state before
  `_commit` refuses with `privacy_action_in_progress`. Safe today; fixing B3-new should keep this
  path covered.

## Verified as correct

- **Review 93 B1 core layouts:** `**Password**:`, `- **密码**：`, inline-code labels, JSON/Python/YAML/TOML
  quotes, env-style `*_PASSWORD=`/`*_TOKEN=`/`*_SECRET_ACCESS_KEY=` and single-row `| password | v |`
  are detected, including end to end through a folder sync. Every Review 93 N2 false positive is
  fixed. URL, label-prefix and provider rules are linear (N6 of Review 93 closed).
- **Review 93 B2 closed:** source-removal retractions (`scrubbed`), authority grant and reclassify
  (`rederive_or_withhold` retracts credential Evidence; no Evidence-derived Profile Fact is derived
  from it; reproduced end to end), guard retractions scrub credential-bearing locator strings, and
  `aptuni retract` writes `Retracted: [credential withheld]`. `record_text` and `doctor` read locator
  strings. Notion `canonical_url` is rebuilt from the page id, so it never carries a title slug.
- **Review 93 B3 closed:** `SyncReport.withheld_items` lists relative paths / note ids / page ids /
  activity keys only, in owner CLI human output and `--json`; no MCP tool returns sync reports.
- **N1/N3 of Review 93:** all four MCP context tools serialise through `_context_json`, which no
  longer carries `withheld_credentials`; the public SDK result has no count; the identity card drops
  credential statements one by one.
- **Targeted purge, where it applies:** every ingest (folder, Obsidian, Notion, MarginNote, GitHub,
  GitHub Deep) derives `supersedes` from `self.current` (current canonical Evidence), so after a
  purge a re-created or edited item starts a new lineage and a still-credential version is withheld
  with nothing written; Evidence-profile derivation is ledger-aware and re-derives Facts after a
  clean edit; no dangling `supersedes` (the supersession closure is complete and `Vault._unlink`
  strips other links); `validate()` and `doctor` pass after every probed purge; an exposed chain
  with a current version is refused; the preview, digest, typed confirmation, intent, ledger,
  receipt and projection invalidation are the reviewed ADR-0010 path; output is content-free.

## Verdict rationale

The remediation closes the copy paths (B2) and the owner's ability to locate withheld items (B3)
cleanly, and the detector now covers the Review 93 layouts with far fewer false positives. It still
does not meet its stated contract in three places: two common Markdown credential layouts reach
Agents while the ADR and CHANGELOG say tables are covered (B1), the new irreversible purge can erase
current — including clean — records whenever a module is not exposed (B2-new), and it can leave a
source permanently unsyncable after an interrupted sync (B3-new). Each fix is small and local
(one regex change plus a collapsed-text table rule or a documentation correction; a "current"
predicate independent of exposure; the pending-state token or a refusal). A narrow re-review of these
three suffices.

**Verdict:** **BLOCK**
