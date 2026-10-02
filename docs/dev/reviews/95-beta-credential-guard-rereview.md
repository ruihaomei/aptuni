# Review 95 — Credential guard re-review: Review 94 remediation (ADR-0031 amendment)

- **Scope:** commit `606e722` ("fix(privacy): close Review 94 findings in the credential guard")
  against its parent `ff3e396`: `src/aptuni/policy/secrets.py` (`_FIELD` decoration after the
  separator, named groups `bare`/`value`, `_BARE_MIN`, `_VERSION`/`_ATTRIBUTE`, `_table_has_secret`
  on flattened text), `src/aptuni/application/privacy.py` (`credential_history_scope`,
  `refuse_pending_sources` in `create_purge_preview` and `_load_or_commit_intent`), the CLI wording
  fix, the new tests, ADR-0031 "Amendment 2026-10-02" and the BACKLOG rows. Narrow re-review of
  Review 94 B1, B2-new and B3-new, plus the notes the commit claims to close. The untracked
  `.agents/skills/` directory, the untracked Chinese-named `.txt` file and the concurrent change to
  `tests/integration/test_activation_guidance.py` are unrelated and were not reviewed.
- **Policy:** AGENTS.md. A finding BLOCKS only for correctness, security/privacy, contract or
  milestone-exit failures. Everything else is a non-blocking note for `docs/dev/BACKLOG.md`.
- **Probes:** throwaway scripts in `/private/tmp/claude-501/rr95/` against temporary Vaults created
  there, with synthetic secret values only; a `git archive` of `ff3e396` was unpacked there for
  side-by-side comparison. The owner's Vault and `~/Library/Application Support/aptuni` were not
  read. No source or test file was modified (probes monkeypatched in-process only).

## Commands and results

| Command | Result |
|---|---|
| `.tools/bin/uv run pytest` | exit 0; 1252 passed, 3 skipped, 62 subtests passed |
| `.tools/bin/uv run ruff check .` | All checks passed |
| `.tools/bin/uv run mypy src` | Success: no issues found in 122 source files |
| `python3.13 tools/check_relay.py` | relay check passed (before and after registering this review) |

## Probes

| Probe | Result |
|---|---|
| `credential_kinds` on 24 synthetic positive layouts, each raw and whitespace-flattened (`" ".join(text.split())`) | Review 94 B1 layouts all hit in both forms: `- **Password:** v`, `**密码：** v`, `**Password:** `` `v` ``, header-column tables (English, CJK, with a heading and intro text before them, second data row, bold/colon header cells, compact `\|a\|b\|`, `API Key`/`Token` columns). Missed: `_Password:_ v` (underscore emphasis is blocked by the label's `(?<![A-Za-z0-9_])` look-behind), a table **without outer pipes** after flattening, a table with an empty cell or empty header cell (raw and flat), `<b>Password</b>:`, and short values after `client_secret` / `access_token` / `refresh_token` / `*_TOKEN` / `*_SECRET` (N1) |
| Same detector on 27 synthetic negatives (ML/tokenizer notes, results tables, code, shell pipes, placeholders under `**Password:**`), raw and flat | Review 94 N1 cases (`token: GPT-4o`, `token: v2.1.0`, `eos_token = tokenizer.eos_token`, `secret: x86_64`) are clean. New/remaining false positives: table cells holding prose with a digit or ≥ 16 characters (`\| bank \| rotated 2025 \|` under `Password`, `12+ chars`, `signs session cookies` under `Secret key`), a vocabulary table `\| Token \| … \|` with `internationalization`, `token: SentencePiece`, and (flat only) a later unrelated table in the same note read against the earlier credential header's column index (N2) |
| Worst case: 110k–400k characters (wide flattened header × rows, 30k rows, `\| \|` runs, `\|\|` runs, label cells, `password:**` chains, 64+ cell headers) | Linear; ≤ 0.18 s for raw + flat at 400k characters (Review 94 N2 closed) |
| Folder sync, 7 notes: English login table with heading, CJK login table, `- **Password:** v`, a results table, a tokenizer-ID table, a budget table, and a password-*policy* table | All three credential notes withheld, no Evidence holds the secret, `context(…, include_evidence=True)` returns no secret; the results, tokenizer and budget tables are ingested. The policy table (`\| bank \| rotated 2025 \|`) is withheld as a false positive (N2). `doctor` ok |
| Owner Fact holding a credential, module `expose=False` | Refused `nothing_to_purge`; after `retract` (still hidden) the Fact + retraction are erased; `doctor` ok |
| Credential Fact corrected to a clean statement | Refused; after the clean successor is retracted, all three versions are erased; `doctor` ok |
| Owner CLI memory (`observe`, auto-promoted) holding a credential, active | Refused (correct) |
| **Same memory after `forget`** | Preview selects 2 records (memory + its revoke event). `PURGE` → canonical `failed_retryable` (`InvariantError: candidate promotion must admit exactly one root memory`), receipt `incomplete_retryable`, the committed intent stays and **every later Vault write fails `privacy_action_in_progress`** until `cancel`; retry fails the same way. `ff3e396` erased all 5 records cleanly (B1-new) |
| Legacy host proposal holding a credential: pending → rejected; accepted → forgotten | Pending: refused (correct, Review 94 B2-new). Rejected: candidate + event erased, the **observation keeps the secret** and is never selectable again. Accepted then forgotten: memory + event erased, candidate and observation keep the secret (B1-new) |
| MarginNote studied card titled with a credential, pre-ADR derived Profile Fact → sweep → purge → clean edit → credential edit | Purge takes 2 assert + 2 sweep retractions + 2 derived Facts + 2 promotion events; clean edit re-derives both Facts (5 Facts); a renewed credential is withheld with no record written; `doctor` ok at every step |
| C1: sync crashes after canonical commit (pending state left), then `--credential-history` | Preview refused `source_sync_pending`; `sync` recovers; preview + `PURGE` succeed; two later syncs (one with an edit) succeed; 0 holders; `doctor` ok (Review 94 B3-new closed) |
| C3: preview, then a sync interrupted before its commit, then confirm | Confirm refused `source_sync_pending` before the intent is written; `sync`; new preview + `PURGE` succeed; next sync ok |
| C4: confirm crashes after the intent is committed (in `_purge_canonical`, and in `_run_cleanups`), a sync runs in between, then resume | The in-between sync is refused `privacy_action_in_progress` and leaves a pending state whose ids were never committed; resume skips the pending check (intent exists) and completes; the next syncs clear the stale pending state and succeed; `doctor` ok |
| Removed source with a leftover pending state (sync interrupted, then `remove_source`) | `sync` → `source_removed`; `--credential-history` → `source_sync_pending` permanently, advising a sync that cannot run (N3) |

## Blocking findings

### B1-new — The "current" predicate makes `--credential-history` select half of a forgotten memory; the purge cannot commit and blocks every Vault write

`credential_history_scope` (`src/aptuni/application/privacy.py:271-285`) now treats every
non-superseded, non-revoked `candidate_memory` and `observation` as current, whether or not it was
decided. A memory chain is `observation → candidate_memory (+ promote/accept event) → memory`, and
only the memory carries the owner's `revoke` when it is forgotten. After `forget`:

- the memory's own closure (memory + events targeting it) contains nothing "current", so it is
  selected; the candidate and observation closures contain themselves, which count as "current", so
  they are not;
- for an owner CLI memory (auto-promoted), deleting the memory without its candidate violates
  `candidate promotion must admit exactly one root memory`, so `_purge_canonical` returns
  `failed_retryable`. The receipt is `incomplete_retryable`, the committed intent remains, and
  `AptuniService._commit` refuses every write (`remember`, sync commits, reviews) until the owner
  finds `aptuni privacy purge cancel`; retrying fails identically. Reproduced end to end; `ff3e396`
  erased the same chain (5 records) cleanly, so this is a regression introduced by the B2-new fix;
- for host proposals (accept → forget, or reject), the purge commits but leaves the candidate and/or
  observation holding the credential, and later previews report `nothing_to_purge`, so the tool can
  never finish the job.

The scenario is reachable today: owner CLI memories are not filtered (only host proposals are), and
"forget the memory, then erase its credential history" is exactly the remediation the ADR and
`doctor` lead the owner to. The preview shows only ids and counts, so the owner cannot tell that the
scope is incomplete before typing `PURGE`.

Required: judge memory chains as a unit — a `candidate_memory` is current only while it is undecided
and not withdrawn, or while it admitted a memory that is still current; an `observation` is current
only while some candidate derived from it is current (an observation with no candidate stays
current). Also validate the
kept set (`RecordSet(kept).validate()`) at preview time and refuse with a content-free error rather
than letting confirm commit an intent that cannot apply. Add tests: CLI memory forgotten → purge
erases observation, candidate, memory and events, `doctor` ok, writes still work; host proposal
rejected → nothing holding the secret remains.

## Non-blocking notes

- **N1 — `bare` is set for qualified underscore labels.** The env-style prefix `(?:[A-Za-z0-9]{1,32}_){0,4}`
  consumes `access_`, `refresh_`, `auth_`, `client_`, `GITHUB_`, `DB_` …, and the alternation then
  matches the `bare` `token|secret` branch, so `client_secret: <9 chars>`, `access_token=…`,
  `refresh_token=…`, `GITHUB_TOKEN=…`, `DB_SECRET=…` (and a `client_secret` table column) now need
  ≥ 12 characters; `ff3e396` detected them. ADR-0031 item 1 says only *bare* labels need 12. Real
  values of these fields are almost always longer, so the practical loss is small; set `bare` only
  when nothing precedes `token`/`secret` (or check the matched label text), or document it.
- **N2 — Table false positives now fire in real syncs.** Table cells are judged by
  `_looks_like_secret_value` without the `\S+` restriction `_FIELD` has, so prose cells with a digit
  or ≥ 16 characters under a credential header are withheld (`rotated 2025`, `12+ chars`,
  `signs session cookies`). After flattening, `columns` never resets, so a later unrelated table in
  the same note is read against the credential column. Require a whitespace-free cell value and reset
  the columns when a segment's cell count differs from the header's (or on a new header-separator
  pair).
- **N3 — Removed source with leftover pending state.** `refuse_pending_sources` refuses forever for a
  removed source (sync is impossible) and its message says to run `aptuni sync`. For a removed source,
  include `source_state:<id>:pending` in the managed copies (it can never replay) or point the owner
  to the explicit-ID purge.
- **N4 — Residuals to add to ADR-0031:** tables without outer pipes after flattening;
  underscore-emphasis labels (`_Password:_`, `__Password__:`). The empty-cell residual now also
  applies to raw multi-line text (owner `remember`, proposals), not only to flattened sources,
  because the row split also matches `| |` inside a line.
- **N5 — Test coverage.** The new pending-sync test writes `{}` as the pending file; a test that
  interrupts a real sync after its canonical commit (as in C1) would pin the recovery path the ADR
  relies on.

## Verified as correct

- **Review 94 B1 closed.** `_FIELD` tolerates emphasis/code on either side of the separator
  (`- **Password:** v`, `**密码：** v`, `**Password:** `` `v` ``) while `**Password:** ********`,
  `*see vault*` and `_TBD_` stay clean. `_table_has_secret` splits flattened rows on the `| |`
  boundary and skips text before the first pipe, so login tables (English and CJK, with a heading
  before them, compact or with alignment colons) are withheld through a real folder sync and never
  reach Context, while results, tokenizer-ID and budget tables are ingested. The ADR states the
  remaining table residual (empty cells).
- **Review 94 B2-new closed for the cases it named.** A current Fact in an unexposed module, a
  Fact awaiting review, an active memory, a pending candidate, and a corrected chain with a clean
  current successor are all refused; once the clean successor is retracted the whole chain is
  erased; Evidence-derived Profile Facts whose Evidence was swept are still erased with their
  promotion events and re-derived after a clean edit (M1). "Current" uses `current_facts()`, which
  ignores exposure and review state.
- **Review 94 B3-new closed.** Preview and confirm refuse `source_sync_pending` while an affected
  source has a pending state; the confirm check runs under `source_operations_lock` before the intent
  is written, so no sync can interleave; every Evidence id a replay expects belongs to that source,
  so the check covers the wedge. An interrupted sync after commit recovers and the purge then
  succeeds with later syncs healthy (C1); crash-resume of a committed intent completes and later
  syncs clear the stale pending state (C4).
- **Notes:** Review 94 N1 cases are clean; N2 is linear (16 label columns, 64 header cells); N3/N4
  residuals and N6 wording are in the ADR; N5 CLI wording fixed; N7/N8 recorded in the BACKLOG.

## Verdict rationale

The three Review 94 findings are closed as specified: both Markdown layouts and flattened tables are
withheld end to end, current records are no longer erased because they are hidden, and an
interrupted sync can no longer be wedged by a targeted purge. The new "current" predicate, however,
treats decided memory candidates and their observations as current, so after an owner forgets a
credential-bearing memory the targeted purge previews half of the chain, fails canonically, and
leaves a committed intent that blocks every Vault write until a manual cancel — a correctness
regression in the irreversible privacy path, reproducible with the documented remediation flow. The
fix is local (a memory-chain-aware "current" predicate plus a kept-set validation at preview time); a
narrow re-review of B1-new suffices.

**Verdict:** **BLOCK**
