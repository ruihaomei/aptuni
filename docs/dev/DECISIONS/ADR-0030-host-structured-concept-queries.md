# ADR-0030: Let the host name the concepts and match each concept whole

- **Status:** Accepted (maintainer brief of 2026-10-02: own retrieval quality, ship a clear,
  low-risk, measurable improvement; independent review required)
- **Date:** 2026-10-02
- **Deciders:** maintainer (final say) · implementing agent · independent reviewer
- **Builds on:** ADR-0004 (lexical projection and fallback), ADR-0005 (Context API, MCP tools),
  ADR-0025 (activation intents), ADR-0029 (Knowledge State)
- **Research refs:** `docs/research/findings/retrieval-experiments.md` (2026-10-02 section)
- **Needs maintainer confirmation:** no — no release is cut by this ADR

## Context

KI-018: when a plain multi-keyword query has no all-keyword match, the whole-keyword fallback
(ADR-0004 2026-10-01) admits records that share one generic or homonymous word ("training",
"plan", a "translation" theorem). Lexical rarity cannot fix it: in a real Vault, "learning" is as
common as "training", yet only the first is topical for an ML question, and "machine translation"
is a compound whose words are both legitimately present elsewhere. Only something that understands
the query can tell these apart.

Every Aptuni caller that matters is an LLM Agent. Mainstream memory systems (Mem0 2.2, Graphiti,
basic-memory; see the research note) buy query understanding with embeddings, rerankers and
LLM-extracted atomic memories; none solves generic-word leakage lexically. Aptuni's caller can
instead state what the task is about, at no cost to Aptuni.

A local, read-only experiment on User #1's real Vault (≈50k exposable records; 62 bilingual
queries in nine categories including 12 that should return nothing; 1,282 pooled judgments graded
by the implementing agent) compared b9 with eleven alternatives:

| Method (top 5) | nDCG@5 | P@5 | MRR | Should-be-empty queries that returned items | Cost |
|---|---|---|---|---|---|
| b9 plain query (control) | 0.629 | 0.74 | 0.80 | 67% | — |
| **Host concepts, each matched whole, regular singular/plural folded (this ADR, product path)** | **0.866** | **0.98** | **1.00** | **0%** | none, ~2 ms of search |
| Host concepts matched whole without folding, last English word in the other `+s/−s` form | 0.606 | 0.74 | 0.84 | 0% | none (14% empty) |
| Host concepts through the b9 loose path | 0.834 | 0.94 | 0.98 | 83% | none |
| Host concepts, monolingual host | 0.706 | 0.73 | 0.95 | 0% | none |
| Plain query treated as one strict concept | 0.522 | 0.58 | 0.71 | 0% | none (24% empty) |
| IDF / information-coverage gate on the fallback | 0.46–0.49 | ≤0.51 | ≤0.60 | 17–75% | none |
| Pairs + generic-word suppression on the plain query | 0.634 | 0.75 | 0.80 | 50% | none |
| Multilingual dense (MiniLM-L12, 0.22 GB), floors 0–0.6 | 0.65–0.67 | ≤0.80 | ≤0.84 | 42–100% | model, ONNX runtime, 15-min index |
| b9 + dense gate on fallback rows (τ 0.4) | 0.664 | 0.79 | 0.81 | 25% | same |
| RRF(b9, dense) | 0.704 | 0.82 | 0.90 | 92% | same |
| b9 + cross-encoder gate (bge-reranker-base, 1.04 GB) | 0.640 | 0.72 | 0.82 | 25% | +1.1 s/query |

## Decision

1. The Context API gains optional `concepts`: 0–8 strings of 1–320 UTF-8 bytes (MCP: 1–80
   characters), whitespace-normalised and de-duplicated. `query` stays required: it is the task in
   one sentence, it drives Knowledge State relevance, and it is the retrieval input only when
   `concepts` is empty — then behaviour is exactly 0.2.0b9.
2. With concepts, Fact/Memory/Evidence retrieval is **concept mode**
   (`SqliteProjection.search_concepts`): each concept's distinct non-stopword keywords (split on
   whitespace and punctuation; a CJK keyword is the AND of its 2–4-character lexemes) must all
   occur in a record. An English word of three or more letters also matches its regular singular
   or plural form (`chain`/`chains`, `box`/`boxes` after s/x/z/ch/sh, `probability`/`probabilities`),
   because the index does not stem and the host cannot know the notes' word forms. Words ending in
   -ss/-us/-is or listed as not plural (`news`, `series`, …) are not stripped, and no form shorter
   than three letters is produced, so folding cannot turn `notes` into `not` (Review 91 B1); -ics
   field names and words such as `means` are protected and listed non-plurals are never generated
   (Review 92). A concept of three or more keywords that matches nothing may relax
   to its adjacent keyword pairs; relaxation never reaches a single keyword (a concept the stopword
   list reduces to one keyword, e.g. "help desk", is that one keyword). Concepts that normalise to
   the same expression count once; a concept with no searchable keyword matches nothing. Each
   concept reads up to 200 matches; a record scores one point per matched concept plus a rank bonus
   whose total over all concepts stays below one point, so more matched concepts always rank first;
   ties break by record id. There is no any-term fallback: an empty result means no permitted record
   matched any concept. Concept diversification (ADR-0005 2026-10-01) then orders the result.
3. Exposure, module, host scope and grant checks are unchanged and still precede ordering; concepts
   are data in quoted FTS expressions, never FTS syntax.
4. `aptuni_activate_context` and `aptuni_search_context` accept `concepts`; their descriptions,
   and the generated Profile/Memory/Full skills, ask the Agent for 1–8 short concepts as they would
   appear in the notes, with English and Chinese forms as separate entries. `aptuni context` gains
   a repeatable `--concept`. Profile passes concepts to Knowledge State relevance. The versioned
   developer SDK (`aptuni.api.v1`) is unchanged.

**Evidence limits.** The experiment ran once, locally and read-only, on one owner's Vault; its
queries, concept lists, judgments and embeddings were deleted afterwards and cannot be re-run in CI.
The implementing agent (not the owner) wrote the 62 queries and the host-style concept lists
before any run and graded all 1,282 pooled judgments itself; twelve methods were compared on the
same queries without a held-out set, so the winning figure is optimistic. The figures describe what
a host that follows the guidance obtains. Word-form robustness was checked with each concept's last
English word replaced by its other regular form; that variant is built from the same rules as the
folding, so its equal score (0.866) only shows the rule works, not that hosts phrase concepts so.
The scratch data were deleted at the end of the investigation, after Review 91.

## Consequences

- KI-018 is solved for callers that pass concepts (0% should-be-empty leakage on the evaluation)
  and unchanged for plain queries, which keep the b9 behaviour.
- Quality depends on the host naming concepts well: a monolingual host loses cross-lingual recall
  (0.29 nDCG on those queries), and over-long concepts rely on pair relaxation. The tool
  descriptions and skills carry the guidance; dogfooding should watch whether hosts comply.
- Ranking among relevant results is by concept count, so bilingual alternates of a common concept
  can outrank a rarer specific one (mixed-language category 0.73 vs 0.83 for b9). A bounded
  specificity weight did not help measurably and was not adopted. Prefix matching was tried for
  word forms and rejected (it only extends a word: 0.685 on the other-plural variant); a first, naive folding rule
  (strip any -s/-es) let `notes` match "not" and was replaced (Review 91).
- No dependency, model, schema, Vault or grant change. Older bundles keep working without
  concepts; regenerated bundles carry the new skill text.

## Rejected for now

An optional semantic backend: a multilingual dense gate on plain-query fallback rows cut
should-be-empty leakage from 67% to 25% at flat relevance, and a 1 GB cross-encoder did no better,
while costing a model download, an ONNX runtime, a ~15-minute first index on this Vault and
incremental re-embedding. Reconsider only if dogfooding shows hosts often omit concepts.

## Verification

`tests/integration/test_concept_queries.py` (strict match, plural folding, no single-word leak, pair
relaxation, ranking with many concepts, de-duplication, exposure, validation, Profile/Memory/Full
and search tools, activation refusal, schema bounds, CLI, skill text) and
`tests/integration/test_knowledge_state.py::test_profile_concepts_select_the_knowledge_state_the_query_does_not_name`;
Reviews 90–92; frozen S03 evaluation unchanged; the real-Vault
evaluation above through the product `context()` path.
