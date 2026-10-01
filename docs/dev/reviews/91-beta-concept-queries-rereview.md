# Review 91 — Host-structured concept queries, re-review (ADR-0030)

- **Responds to:** Review 90 (`90-beta-concept-queries-review.md`).
- **Scope:** `c50f6bf` ("fix(context): fold plural forms and make concept count dominate
  (Review 90)") on top of `3df9ad0`: `_english_forms` / `_term_expression` / `_group_expression`
  in `src/aptuni/retrieval/lexical.py`, de-duplication, scoring and the `module` filter in
  `src/aptuni/retrieval/sqlite.py`, `_check_concepts` and `_stable_search` in
  `src/aptuni/application/service.py`, the MCP comment order, the new tests, ADR-0030, CHANGELOG and
  the research note. The untracked `.agents/skills/` directory and the untracked Chinese-named
  `.txt` file are unrelated user files and were not read.
- **Policy:** AGENTS.md. A finding BLOCKS only for correctness, security/privacy, contract or
  milestone-exit failures. Everything else is a non-blocking note for `docs/dev/BACKLOG.md`.
- **Probes:** throwaway scripts in the session scratchpad against temporary Vaults and temporary
  projections only; the owner's Vault was not touched. The b9 comparison used
  `git archive 8f0d140 src` (the parent of `3df9ad0`) extracted into the scratchpad. No source or
  test file was modified.

## Commands and results

| Command | Result |
|---|---|
| `.tools/bin/uv run pytest` | exit 0; 1152 passed, 3 skipped, 62 subtests passed |
| `.tools/bin/uv run ruff check .` | All checks passed |
| `.tools/bin/uv run mypy src` | Success: no issues found in 120 source files |
| `python3.13 tools/check_relay.py` | relay check passed (before and after registering this review) |
| `.tools/bin/uv run python tools/run_evals.py` | `passed: true`; dev FPR 0.0, recall@5 0.992, MRR 1.0 (58 queries); holdout FPR 0.0, recall@5 1.0, MRR 1.0 (15 queries); plain path only |
| `python3.13 -m unittest discover -s tests/dev` | Ran 56 tests, OK |

## Probes

| Probe (temporary Vaults / projections) | Result |
|---|---|
| Plain `SqliteProjection.search` at b9 vs HEAD: 400 random bilingual records, 400 random queries, `modules=` and `module=` variants, random record types and limits | **Identical** on all 800 searches |
| Plain `context()` at b9 vs HEAD on one temporary Vault (120 records, one hidden module, 150 random queries, random modules, limits and `include_evidence`) | **Byte-identical** JSON for all 150 responses |
| `_english_forms` on common plurals | `notes`→`not`, `planes`→`plan`, `themes`→`them`, `news`→`new`, `uses`→`us`, `yes`→`y`, `ies`→`i`,`y`, `rates`→`rat`, `modes`→`mod`, `codes`→`cod`, `sites`→`sit`, `states`→`stat`, `bayes`→`bay` |
| Concept `release notes` vs "We did not release the build." | **Matches** (B1) |
| Concept `lecture notes` vs "The lecture was not recorded this week." | **Matches** (B1) |
| Concepts `planes` / `news` / `uses` / `yes` | Match "Weekly plan for the semester." / "New laptop setup." / "Send it to us." / "Solve for x and y." (B1) |
| Concepts `probability`, `stochastic process`, `box`, `theory of mind` vs "probabilities", "processes", "boxes", "theories of mind" | **Empty**: singular→`-es`/`-ies` plurals are not folded (N1) |
| Concepts `markov chain` + `markov chains` + `stationary distribution` | The Markov record scores 2.33 (two concepts); the expressions differ only in form order (N2) |
| 4 concepts; one record matching 3 at rank 0 vs 150 records matching all 4 | All 101 returned rows match four concepts; the three-concept record is below them (Review 90 N2 fixed) |
| The shipped N2 regression test run under the **old** scoring formula | Still passes (`fct_four` first) (N4) |
| 8 adversarial concepts of about 307 bytes, each word with four forms (1,881-char strict and 3,716-char relaxed expressions), over 50,000 records | 101 rows in 0.30 s; no FTS5 error |
| 320-byte CJK concept (106 characters, 312 lexemes); all-stopword concepts | Correct match / empty; no error |
| Exposure, ungranted module, activation-required gate, 80 astral-plane characters | Hidden and ungranted records never returned; `aptuni_activation_required`; 80 × 4-byte characters now accepted (Review 90 N6 fixed) |

## Findings

### Blocking

1. **B1 — BLOCKING (correctness/contract): plural folding produces unrelated common words and
   brings back the single-word leakage ADR-0030 removes.**
   `src/aptuni/retrieval/lexical.py:121-123` strips a final `s` from every word and also strips
   `es` from every word ending in `es`, whatever comes before it. The derived "forms" are often not
   forms of the word at all, and several are among the most frequent English words: `notes`→`not`,
   `themes`→`them`, `planes`→`plan`, `news`→`new`, `uses`→`us`, `yes`→`y`. Each keyword of a concept
   is an OR of its forms, so one keyword of a multi-word concept can be satisfied by an incidental
   function word. Failure scenario: an Agent following the shipped skill passes
   `concepts=["release notes"]`; the strict expression is
   `("release" OR "releases") AND ("notes" OR "note" OR "not")`, and "We did not release the build."
   is returned (probe). `lecture notes` returns "The lecture was not recorded this week.". A
   single-word concept `planes` returns "Weekly plan for the semester.", which is KI-018's own
   generic-word example. These are exactly the records ADR-0030 promises to exclude: Decision 2
   describes the folding as "regular plural/singular forms (`chain`↔`chains`, `-es`, `-ies`→`-y`)",
   and the CHANGELOG says "unrelated notes that share only one generic word are no longer
   returned". The ADR's own table also shows the cost: the shipped figure on the hosts' original
   wording fell from 0.866 to 0.847 nDCG@5 when folding was added.
   **Required fix (small):** strip `es` only when the remainder ends in `s`, `x`, `z`, `ch` or `sh`
   (`boxes`, `matches`, `buses`, `glasses`); never emit a derived form shorter than three letters;
   optionally leave words ending in `ss`, `us` or `is` exact. Add regressions:
   `_english_forms("notes")` contains no `not`; `release notes` does not match "We did not release
   the build."; `planes` does not match `plan`; `boxes`, `matches` and `probabilities` still fold.
   Then correct the ADR wording to describe the rule exactly, and re-run the real-Vault figures if
   the data still exists or mark them as measured with the earlier rule. `news`→`new` survives this
   rule; record it as a known residual or exclude it explicitly.

### Non-blocking notes

1. **N1 — Folding is one-directional for `-es` and `-ies`.** A singular concept gains only `+s`
   (`lexical.py:119-120`), so `probability`, `process`, `box` and `theory` miss `probabilities`,
   `processes`, `boxes` and `theories` (probe). Hosts usually name concepts in the singular, so this
   is the direction that matters. The ADR's `↔` overstates it. Add `+es` after `s/x/z/ch/sh` and
   consonant+`y`→`ies` alongside the B1 fix.
2. **N2 — De-duplication misses plural spellings.** Expressions are de-duplicated by string
   (`sqlite.py:213`), but `_english_forms` orders forms by input (`chain`→`chain, chains`;
   `chains`→`chains, chain`). As a result, `markov chain` and `markov chains` count as two concepts.
   Canonicalise the form order (for example, sort the forms) or de-duplicate on frozensets of forms.
3. **N3 — Guidance still overclaims.** The second half of Review 90 N1 was not addressed:
   `src/aptuni/adapters/manager.py:255` still says "an empty result means the notes do not cover
   it", and `src/aptuni/mcp/server.py:154` is similar. Empty results remain likely for the N1
   cases, irregular plurals, derivations ("optimize" vs "optimization"), a single CJK character
   inside a longer run, and accented words.
4. **N4 — The ranking regression test does not discriminate.**
   `test_more_matched_concepts_always_rank_first_even_with_many_concepts` passes under the old
   `1 + 1/(rank+2)` formula too (verified), because the four-concept record also wins every bm25 tie
   by id. Use the Review 90 shape: one record matching three concepts at rank 0 and more than six
   records matching four.
5. **N5 — New intent tests stop short.** The Profile test asserts only L3 rows, not the
   `KnowledgeIndex.relevant(named=…)` threading; the Memory test asserts only an empty result for an
   unrelated concept, with no positive Memory match in concept mode.
6. **N6 — Evidence wording is inconsistent.** The ADR Context paragraph still says "graded manual
   judgments" and the research note "graded by hand", while the new Evidence limits paragraph says
   the implementing agent made all judgments; drop "manual"/"by hand". The Evidence limits say the
   data was deleted afterwards, yet folding was measured after Review 90; state when it was deleted.
   The "other plural form" variant appears to invert the same regular rules that folding applies,
   so its 0.843 is partly by construction; say how the variant was generated.
7. **N7 — Relay hygiene.** STATE/HANDOFF still give no checkpoint hashes (Review 90 N10).

### Review 90 notes — disposition

| Note | Status |
|---|---|
| N1 inflection | Partly fixed (plural→singular, `+s`); widened into B1; N1 and N3 above remain |
| N2 ranking | **Fixed**: bonuses total at most 0.5, so more matched concepts always rank first; ADR wording now accurate |
| N3 de-duplication | Fixed for case and punctuation; N2 above remains |
| N4 stopword collapse | Documented in ADR-0030 Decision 2 |
| N5 no searchable keyword | Documented; such concepts are dropped from scoring |
| N6 byte bound | **Fixed** (320 bytes) |
| N7 clarity | **Fixed** (type message, `module` honoured with a both-arguments `ValueError`, comment order) |
| N8 tests | Largely fixed; N4 and N5 above remain |
| N9 evidence framing | Largely fixed (Evidence limits, CHANGELOG); N6 above remains |
| N10 checkpoint hash | Open (N7) |

## Summary

The remediation fixes the ranking contract, bounds, messages and most framing. FTS5 stays safe
under many concepts with many forms: every form is a quoted `[a-z]` string, and the largest
expressions run in 0.3 s on 50,000 records. Plain queries are identical to 0.2.0b9 at the projection
and `context()` levels. One regression blocks. The plural rule strips `s`/`es` unconditionally, so
common concepts such as "release notes", "lecture notes" and "planes" again match records sharing
only one real word, through "not" or "plan". This contradicts ADR-0030's central claim and the
CHANGELOG. The fix is a few lines in `_english_forms` plus regression tests, and a narrow re-review
of that function, its tests and the ADR wording is enough.

**Verdict:** **BLOCK**
