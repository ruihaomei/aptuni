# Review 90 — Host-structured concept queries (ADR-0030)

- **Scope:** `3df9ad0` ("feat(context): match host-named concepts whole (ADR-0030)") against its
  parent `8f0d140`: `retrieval/lexical.py` (`concept_expressions`), `retrieval/sqlite.py`
  (`search_concepts`, `_filters` extraction), `application/service.py` (`context`,
  `_check_concepts`, `_stable_search`), activation / Profile / Knowledge State threading, the MCP
  `concepts` parameter, CLI `--concept`, generated skill text, ADR-0030, CHANGELOG and the research
  note. The untracked `.agents/skills/` directory and the untracked Chinese-named `.txt` file are
  unrelated user files and were not read.
- **Policy:** AGENTS.md. A finding BLOCKS only for correctness, security/privacy, contract or
  milestone-exit failures. Everything else is a non-blocking note for `docs/dev/BACKLOG.md`.
- **Probes:** throwaway scripts in the session scratchpad against temporary Vaults and temporary
  projections only; the owner's Vault was not touched. The parent-commit comparison used
  `git archive 3df9ad0^ src` extracted into the scratchpad. No source or test file was modified.

## Commands and results

| Command | Result |
|---|---|
| `.tools/bin/uv run pytest` | exit 0; 1145 passed, 3 skipped, 62 subtests passed |
| `.tools/bin/uv run ruff check .` | All checks passed |
| `.tools/bin/uv run mypy src` | Success: no issues found in 120 source files |
| `python3.13 tools/check_relay.py` | relay check passed (before and after registering this review) |
| `.tools/bin/uv run python tools/run_evals.py` | `passed: true`; dev FPR 0.0, recall@5 0.992, MRR 1.0 (58 queries); holdout FPR 0.0, recall@5 1.0, MRR 1.0 (15 queries). The frozen harness exercises only the plain path, so it confirms the b9 path and says nothing about concept mode (N8) |
| `python3.13 -m unittest discover -s tests/dev` | Ran 56 tests, OK |

## Probes

| Probe (temporary Vaults / projections) | Result |
|---|---|
| Plain `SqliteProjection.search` at parent vs HEAD: 400 random bilingual records, 400 random queries, each with `modules=` and `module=` variants, random record types and limits 1–101 | **Identical** rows, scores and `exact` flags on all 800 searches (798 non-empty) |
| FTS syntax as concepts: `" OR NOT *`, `NEAR(`, `markov OR chain`, `markov" OR "x`, `(`, `*`, `^`, `AND` | Every term is a quoted lexeme or the concept yields no expression; no FTS error, no operator reaches FTS5 |
| Stopword-only (`the of`, `what is it`, `我的`), punctuation-only (`!!!`), emoji | `(None, None)`; empty result, no error (N5) |
| 256-byte concepts: 80 ASCII keywords, one 85-character CJK run (2,485-char expression), CJK words; then 8 long concepts at once | No FTS depth or parse error; results correct |
| Single CJK character `链` / `马` | Matches only an isolated single-character segment (pre-existing lexeme rule, same as plain queries) |
| Mixed script `马尔可夫链 markov` / `马尔可夫链markov` | Both require every lexeme of both scripts (as specified) |
| `help desk`, `Q and A` | Collapse to the single keyword `desk` / `q` through the stopword list; `help desk` matches `desk lamp` (N4) |
| `Machine Learning`, `machine learning`, `machine-learning` + one other concept | Not de-duplicated; the record scores 4.5 vs 1.5 (N3) |
| 4 concepts; a record matching 3 at rank 0 vs 250 records matching all 4 | The 3-concept record ranks 7th, ahead of 244 records that match all four concepts (N2) |
| Concept `markov chain` / `stationary distribution` vs a note saying "Markov chains … stationary distributions" | **Empty** in concept mode; found by `markov chains`, `markov`, and by the plain query `review markov chain` (N1) |
| `context()` with a concept naming a record in an expose-disabled module, with and without that module requested | Never returned |
| Host grant `{knowledge}`, request `projects` with concepts | `mcp_module_denied` (module names only) |
| `aptuni_search_context` with concepts before activation (activation-required server) | `aptuni_activation_required` |
| Profile activation with concept `xgboost` (declared fact in `skills`) / concept for an ungranted module | Knowledge State unit + fact / nothing |
| MCP schema | `anyOf[array(maxItems 8, items 1–80 chars), null]`, default null, not required; 9 items, `""`, 81 chars refused by pydantic; tools without `concepts` and with `concepts: null` behave as before |
| MCP: 80 astral-plane characters (320 bytes) | Passes the schema; refused by the service as a bare `invalid_context` (N6) |
| Service validation: `str`, `None`, non-string element, whitespace-only, 257 bytes, 9 items | `invalid_context` with fixed, content-free messages; 256 bytes and a `list` accepted |
| `limit=1` with two matches | `more_results=true`, one item |
| CLI: 9 × `--concept`; one valid `--concept` | exit 1 `aptuni: Pass at most 8 concepts.` / exit 0 |

## Findings

### Blocking

None. Exposure, module, grant, evidence-scope and activation checks are untouched and still precede
ordering; the projection only holds exposable records and `_stable_search` and `context()` both
re-filter against the final snapshot, so concept mode cannot return anything the plain path could
not. Concepts reach FTS5 only as quoted lexemes. Validation errors are fixed strings, and
`invalid_context` stays outside `GUIDED_ERROR_CODES`, so no message can carry Vault content. The
public MCP change is additive and optional. The plain path is byte-for-byte the b9 path (differential
probe; `_filters` is a verbatim extraction; `context()` never passes `module`).

### Non-blocking notes

1. **N1 — No inflection handling, while the guidance says an empty result means "not covered".**
   Concept keywords are exact unicode61 tokens with no stemming or prefix, so the skill's own
   example `markov chain` and the tool description's `stationary distribution` miss a note that
   says "Markov chains … stationary distributions" (probe), which the plain query finds. The
   generated skill (`src/aptuni/adapters/manager.py:255`, "an empty result means the notes do not
   cover it") and the tool description (`src/aptuni/mcp/server.py:154`) invite the Agent to tell the
   owner that their notes lack a topic they do cover. The research note reports leakage on
   should-be-empty queries but not the empty-result rate on positive queries for the shipped
   method. Suggest, before a release advertises concepts: soften both texts ("probably not under
   this wording; try singular/plural or the other language") and ask hosts to add inflected
   variants as separate concepts, or match the final ASCII keyword of a concept as an FTS5 prefix
   (`"chain"*`) in concept mode only; report the positive-query empty rate in the ADR.
2. **N2 — Ranking is not strictly by concept count with four or more concepts.** Each matched
   concept adds `1 + 1/(rank+2)` (`src/aptuni/retrieval/sqlite.py:217`), so the per-concept bonus is
   below one point but the summed bonus is not: three concepts at rank 0 (4.5) beat four concepts
   at rank ≥ 7 (≤ 4.44). The docstring (`sqlite.py:202`, "rank records by how many concepts they
   match") and ADR-0030 Consequences ("Ranking … is by concept count", line 73) overstate it. Sort by
   `(count, bonus)` or divide the summed bonus by `len(concepts) + 1`, or correct the wording.
3. **N3 — De-duplication is exact-string only.** `_check_concepts` (`src/aptuni/application/service.py:446-447`)
   collapses whitespace, but `Machine Learning`, `machine learning` and `machine-learning` yield the
   same expression and each adds a point, tripling that concept's weight. De-duplicate on the
   normalised keyword groups (or on the strict expression) in `search_concepts`.
4. **N4 — Stopword filtering can reduce a concept to one keyword.** `_keyword_groups`
   (`src/aptuni/retrieval/lexical.py:81`) drops task-language words that are also content words in
   noun phrases (`help`, `like`, `need`, `can`, `do`, `tell`, `give`, `a`, `i`): `help desk` becomes
   `desk` and matches `desk lamp`. The "never degrades to a single keyword" claim
   (`lexical.py:116`) is true of relaxation only. Consider not applying the task-language stopword
   list inside a multi-keyword concept, or only dropping stopwords when two or more keywords remain.
5. **N5 — Concepts with no searchable keyword are accepted and silently match nothing.** A
   stopword-only, punctuation-only or emoji concept passes validation and contributes no expression;
   if all concepts are like this the response is "no matching permitted context", which the skill
   text tells the Agent to read as "not covered". Either refuse such a concept with a fixed
   `invalid_context` message or fall back to the plain query when no concept yields an expression.
6. **N6 — MCP and service bounds disagree for 4-byte characters.** The schema allows 80 characters
   (`src/aptuni/mcp/server.py:41`); the service allows 256 bytes. 80 astral-plane characters (CJK
   Extension B, emoji) are 320 bytes and get a bare `invalid_context` with no guidance. Use 64
   characters in the schema, or document that the byte bound wins.
7. **N7 — Small code clarity items.** `_stable_search` silently ignores `concepts` when `module` is
   set (`service.py:360`); unreachable today, but a `ValueError` would make misuse visible. A
   non-sequence `concepts` gets "Pass at most 8 concepts." (`service.py:437`). The new
   `CONCEPTS_PARAMETER` was inserted between the `GUIDED_ERROR_CODES` comment and its constant
   (`mcp/server.py:38-43`).
8. **N8 — Test coverage gaps.** No test for Profile with concepts (`KnowledgeIndex.relevant(named=…)`
   is untested), Memory intent with concepts (`record_types=("memory",)` in concept mode),
   `more_results` in concept mode, the MCP schema bounds, ranking with four or more concepts, or
   that concepts cannot bypass the activation-required gate. There is no CI-level quality check for
   concept mode; a small frozen concept fixture (positive, negative, inflected) in `run_evals.py`
   would protect the ADR's 0% leakage behaviour and expose N1.
9. **N9 — Evidence framing.** The ADR states that the numbers come from a local experiment on the
   owner's Vault and the research note says the scratch data was deleted. That is honest about
   provenance, but the ADR should also say: the evaluation cannot be re-run in CI or by a reviewer;
   twelve methods were compared on the same 62 queries with no held-out split, so the winner's
   score is optimistic; the host concept lists were written by the experimenter, so 0.866 is the
   score of a compliant host, not of measured host behaviour; and who made the 1,158 "manual"
   judgments. ADR-0030 Verification lists the real-Vault evaluation, which no one else can
   reproduce. The CHANGELOG (`CHANGELOG.md:14-15`) turns 12 test topics into "stopped unrelated
   items for topics the notes do not contain"; prefer "in a local evaluation on one Vault (62
   queries), useful top-5 items rose from 74% to 98% and none of 12 off-topic test requests
   returned items".
10. **N10 — Relay hygiene.** STATE/HANDOFF describe the slice as local but give no checkpoint hash
    (AGENTS.md execution policy 10).

### Observations (no action required for this change)

- The P1 dogfooding entry about a folder-source note with credentials (BETA_DOGFOODING
  2026-10-02) is pre-existing and recorded as an open owner decision. Concept mode does not widen
  access to it: strict concept matching returns a subset of what the plain any-term fallback can
  already return within the same grants.
- A single CJK character, accented Latin and kana or Hangul behave as in the plain path (lexeme
  rules unchanged). Inside a multi-keyword concept, one such keyword now empties that concept where
  the plain fallback would still match the other keywords, which adds to N1.

## Summary

The change is additive and contained. Concepts can only narrow retrieval within the existing
exposure, grant and activation gates, FTS input stays data, error messages stay content-free, the
MCP parameter is optional, and plain queries match 0.2.0b9 exactly in a differential probe. The
notes concern retrieval quality and wording rather than safety. The most important is N1: inflected
note text produces false "not covered" answers that the shipped guidance tells Agents to trust. The
others are ranking and de-duplication details, test gaps, and how firmly the private evaluation is
stated.

**Verdict:** **APPROVE WITH NON-BLOCKING NOTES**
