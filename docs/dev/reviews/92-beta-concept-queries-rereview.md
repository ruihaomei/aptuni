# Review 92 — Host-structured concept queries, second re-review (ADR-0030)

- **Responds to:** Review 91 (`91-beta-concept-queries-rereview.md`), B1 and notes N1–N7.
- **Scope:** `e9b693a` ("fix(context): fold only regular English inflection in concept mode
  (Review 91)"): `_english_forms` in `src/aptuni/retrieval/lexical.py`, the skill and tool texts,
  the new and changed tests in `tests/integration/test_concept_queries.py` and
  `tests/integration/test_knowledge_state.py`, ADR-0030, CHANGELOG, the research note and
  STATE/HANDOFF. Narrow re-review as requested; the rest of the slice was covered by Reviews 90–91.
  The untracked `.agents/skills/` directory and the untracked Chinese-named `.txt` file are
  unrelated user files and were not read.
- **Policy:** AGENTS.md. A finding BLOCKS only for correctness, security/privacy, contract or
  milestone-exit failures. Everything else is a non-blocking note for `docs/dev/BACKLOG.md`.
- **Probes:** throwaway scripts in the session scratchpad against temporary projections and
  temporary Vaults only; the owner's Vault was not touched. The b9 comparison used
  `git archive 8f0d140 src` in the scratchpad. No source or test file was modified.

## Commands and results

| Command | Result |
|---|---|
| `.tools/bin/uv run pytest` | exit 0; 1155 passed, 3 skipped, 62 subtests passed |
| `.tools/bin/uv run ruff check .` | All checks passed |
| `.tools/bin/uv run mypy src` | Success: no issues found in 120 source files |
| `python3.13 tools/check_relay.py` | relay check passed (before and after registering this review) |
| `.tools/bin/uv run python tools/run_evals.py` | `passed: true`; dev FPR 0.0, recall@5 0.992 (58 queries); holdout FPR 0.0, recall@5 1.0 (15 queries); plain path only |
| `python3.13 -m unittest discover -s tests/dev` | Ran 56 tests, OK |

## Probes

| Probe | Result |
|---|---|
| Review 91 B1 words: `notes`, `themes`, `planes`, `news`, `uses`, `yes`, `ies` | `note`, `theme`, `plane`, unchanged, unchanged, unchanged, unchanged; no `not`, `them`, `plan`, `new`, `us`, `y`, `i` |
| `release notes`, `lecture notes`, `planes`, `news` against the Review 91 records | No match (also pinned by the new test) |
| 95 further adversarial words (sibilant, `-ies`, `-ics`, `-ses`, `-ch`, proper nouns, acronyms, irregulars) | Every form is lowercase `[a-z]`, at least three letters, at most two forms per word; remaining collisions listed in N1–N3 |
| Concepts `logistics`, `genetics`, `basics`, `k-means`, `windows` | Match "Logistic regression…", "A genetic algorithm…", "Basic syntax…", "The mean of k samples.", "Sliding window attention." (N1) |
| Concepts `poses`, `loses` | Match "POS tagging…", "Trip to Los Angeles." (N2) |
| Concepts `use cases`, `databases` vs "A use case…", "Database indexing…" | Empty (N2) |
| `epoch` vs "Train for 10 epochs."; `movies` vs "A movie…" | Empty: `epoch`→`epoches`, `movies`→`movy` (N3) |
| `new york` vs "News from York." | Match: generated forms are not checked against `_NOT_PLURAL` (`new`→`news`) (N1) |
| `markov chain` vs `markov chains`; `Machine Learning` / `machine-learning` / `machine learnings` | Identical expressions; counted once (Review 91 N2 fixed) |
| Shipped ranking test re-scored with the old `1 + 1/(rank+2)` bonus | **Still passes**: `fct_three` ranks 10th in each list (behind ten one-word records), so the old formula also puts `fct_four` first (N4) |
| One `alpha beta gamma` record + 12 long four-concept records | Old formula: three-concept record 7th of 13; shipped: last; the shipped formula is correct |
| 8 adversarial 307-byte concepts over 50,000 records | 101 rows in 0.21 s (strict 1,020 / relaxed 2,036 characters); no FTS5 error |
| Plain `SqliteProjection.search` at b9 vs HEAD (800 searches) and plain `context()` at b9 vs HEAD (150 responses, one temporary Vault) | Identical / byte-identical |

## Findings

### Blocking

None. **Review 91 B1 is fixed.** `-es` is stripped only after `s/x/z/ch/sh`, `-ss/-us/-is` and
listed non-plurals are never stripped, and forms under three letters are dropped. Folding no longer
yields `not`, `them`, `plan`, `us`, `y` or `i`, and the new test pins the Review 91 failure cases.
What remains is the usual exception problem of any rule-based inflector: non-plural `-s` nouns and
`-se` plurals. ADR-0030 scopes this with an explicit exception list, and the real-Vault re-measure
reports 0% should-be-empty leakage. FTS input remains quoted `[a-z]` data, and expressions are now
smaller than in `c50f6bf`. Plain queries match 0.2.0b9 exactly.

### Non-blocking notes

1. **N1 — Non-plural `-s` nouns outside `_NOT_PLURAL` widen to a different, common word in this
   Vault's domain.** `-ics` field names fold to `-ic` adjectives: `logistics`→`logistic`,
   `genetics`→`genetic`, `basics`→`basic`, `mechanics`, `optics`, `ethics`, `physics`. Other cases
   are `means`→`mean` (so `k-means` matches "The mean of k samples."), `windows`→`window` and
   `pandas`→`panda` (`lexical.py:135-136`). Generated plural forms are not checked against
   `_NOT_PLURAL` (`lexical.py:141-142`), so `new`→`news` and `doe`→`does`. Suggest protecting `-ics` (keeping a small
   allow-list such as `topics`, `clinics`, `critics`), adding `means`, `windows` and `pandas` to
   `_NOT_PLURAL`, and dropping generated forms that are in `_NOT_PLURAL`.
2. **N2 — `-ses` plurals of `-se` nouns lose their singular.** The sibilant branch
   (`lexical.py:133-134`) yields `cases`→`cas`, `bases`→`bas`, `databases`→`databas`,
   `releases`→`releas`, `responses`→`respons` and `courses`→`cours`, so `use cases` misses "use
   case" and `databases` misses "database". It also yields real short tokens: `poses`→`pos`,
   `loses`→`los`, `doses`→`dos`. Suggest emitting `term[:-1]` as well when the remainder ends in a
   single `s`, and keeping `term[:-2]` only for `-sses` and the listed `-s` singulars (`buses`,
   `gases`, `lenses`, `biases`).
3. **N3 — Smaller recall gaps.** `-ch` read as /k/ gets only `-es` (`lexical.py:137-138`;
   `epoch`→`epoches`, missing
   `epochs`, common in ML notes; also `monarch`, `stomach`). Adding `+s` for `-ch` costs nothing.
   `-ie` nouns map `-ies` to `-y` (`movies`→`movy`, `cookies`→`cooky`); also emitting `term[:-1]`
   would recover `movie`. Plural `-us` words (`menus`, `gurus`) stay exact. The docstring's "Only
   regular inflection is produced" should mention these limits.
4. **N4 — The ranking regression test still does not discriminate.** It passes under the old
   formula (verified), because the ten one-word records outrank `fct_three` in every list, so the
   comment "one short three-concept record tops three lists" does not hold. Use one
   `alpha beta gamma` record and twelve long four-concept records, and assert that every
   four-concept record precedes the three-concept one. The old formula puts it 7th of 13.
5. **N5 — Residual wording.** The research note still says "graded by hand … by the implementing
   agent". Several ADR-0030 lines exceed the file's wrap width (lines 33, 34, 40, 58, 94 and 111).

### Review 91 notes — disposition

| Note | Status |
|---|---|
| B1 folding to unrelated common words | **Fixed** (N1–N2 above are remaining exception-list gaps, not the B1 rule defect) |
| N1 one-directional folding | **Fixed** for `-es` and `-ies`; N3 above remains |
| N2 de-duplication of plural spellings | **Fixed** (sorted forms) |
| N3 guidance overclaim | **Fixed** (skill and tool text say to try a synonym or the other language first) |
| N4 non-discriminating ranking test | Test replaced but still non-discriminating (N4 above); formula verified correct by probe |
| N5 intent tests | **Fixed** (positive Memory match; Profile `named=` Knowledge State test) |
| N6 evidence wording | **Fixed** in ADR-0030 (agent-graded, constructed variant, deletion timing); N5 above for the research note |
| N7 checkpoint hashes | **Fixed** (STATE/HANDOFF list `3df9ad0`, `c50f6bf` and the Review 91 fix) |

## Summary

B1 is resolved. The morphology-aware rule no longer produces function words or unrelated content
words from regular plurals, and the Review 91 failure cases are pinned by tests. De-duplication, the
guidance text, the intent tests and the evidence framing are fixed. Ranking is correct, though its
regression test still would not catch the old formula. Plain queries remain identical to 0.2.0b9,
and FTS5 input stays safe and bounded. The remaining notes are exception-list and recall refinements
for the folding rule (`-ics`, `-ses`, `-ch`, `-ie`) and one test to sharpen. They belong in the
backlog and do not need another review round.

**Verdict:** **APPROVE WITH NON-BLOCKING NOTES**
