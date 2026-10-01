# Retrieval experiments — 2026-10-01 (dogfooding Day 1)

Local, read-only MVP experiments on User #1's real Vault (0.2.0b8 working tree; ~50k exposable
Facts/Evidence, almost all MarginNote topics). The harness, the query set and the embeddings lived in
a deleted scratch directory; nothing below contains Vault text or the queries themselves.

**Set-up.** 36 queries in five styles: English keyword lists (10), Chinese keyword lists (7),
cross-lingual (6), task-shaped natural requests (7), and negatives with no expected notes (6).
Judge: a per-query bilingual relevance pattern (biased toward lexical methods), then a manual
spot-check of the top 5 for the cross-lingual and task queries. Metrics at k=10: P@10, precision of
what was returned, distinct relevant concepts, negative false-positive rate, median latency.

| Method | P@10 en / zh / xling / task | Distinct relevant concepts | Negative FP | Verdict |
|---|---|---|---|---|
| M0 0.2.0b8 lexical | 0.99 / 1.00 / 0.82 / 0.86 | 8.5 / 7.1 / 6.0 / 6.6 | 0.67 | baseline |
| M1 + concept collapse (drop) | 0.89 / 1.00 / 0.73 / 0.80 | 8.9 / 10.0 / 7.3 / 8.0 | 0.67 | superseded by M1b |
| **M1b + dedupe and demote (shipped, ADR-0005 2026-10-01)** | 0.98 / 1.00 / 0.73 / 0.84 | 9.8 / 10.0 / 7.3 / 8.4 | 0.67 | **adopted** |
| M2 jieba query segmentation + M1 | 0.89 / 0.96 / 0.82 / 0.76 | 8.9 / 9.6 / 8.2 / 7.6 | 1.00 | rejected |
| M3 dense `BAAI/bge-small-zh-v1.5` (floors 0–0.6) | 0.63 / 0.87 / 0.63 / 0.53 | 6.3 / 8.7 / 6.3 / 5.3 | 0.67–1.00 | rejected for now |
| M4 RRF(M2, dense) | 0.87 / 0.94 / 0.78 / 0.59 | 8.7 / 9.4 / 7.8 / 5.9 | 1.00 | rejected |
| M5 lexical first, dense fill | 0.91 / 0.96 / 0.82 / 0.79 | 9.1 / 9.6 / 8.2 / 7.9 | 1.00 | rejected |

Through the product `context()` path the shipped ordering measured 0.98 / 1.00 / 0.78 / 0.84 P@10
and 9.8 / 10.0 / 7.3 / 8.4 distinct relevant concepts.

**Findings.**

- The biggest real defect was redundancy, not recall: a topic appears as Evidence, its derived Fact
  and nested repeats of its path. Dedupe-and-demote fixes it at near-zero cost.
- Dense retrieval found better *concept neighbourhoods* by hand (e.g. specific sub-topics instead
  of a homonymous SQL clause) but lost overall, and no similarity floor separated negatives (~0.72)
  from true hits (~0.74). Hugging Face was unreachable from the owner's network, so a proper
  multilingual model (paraphrase-multilingual-MiniLM, multilingual-e5) could not be tested; only
  fastembed's GCS-hosted Chinese model was. Revisit with a multilingual model before any claim.
- jieba segmentation removed cross-word CJK fragments but did not improve precision and worsened
  negatives, because the whole-keyword fallback then had more keywords to match.
- Negatives leak through generic single words in the whole-keyword fallback (a "training" or
  "translation" note). No lexical coverage rule separates these from the Day-1 P1 case (one absent
  keyword must not empty the result); tracked in KI-018.
- Embedding ~46k unique texts with a 0.09 GB model took ~13 minutes on the owner's Mac; a dense lane
  would need incremental indexing, not rebuilds.

## 2026-10-02 — Retrieval investigation (ADR-0030)

**Method.** Local, read-only, scratch-only (deleted afterwards). 62 queries written before any run
in nine categories (English, Chinese, mixed, cross-lingual, task-shaped, long natural language,
only-some-terms-matter, generic-term, should-return-nothing ×12) plus dogfooding-derived ones; for
each, a host-style concept list (bilingual alternates as separate entries) also written blind.
Judging: top-5 pooled from every system, graded 0/1/2 by the implementing agent ("would an Agent
understand the user better with this?"), 1,282 judgments; metrics at k=5 where every system is fully judged.

**Results** — see the table in ADR-0030. Shipped: host concepts matched whole (nDCG@5 0.629→0.866,
P@5 0.74→0.98, MRR 0.80→1.00, should-be-empty leakage 67%→0%, distinct useful concepts 3.7→4.9,
~2 ms search; total request latency unchanged at ~0.6 s, dominated by the Vault snapshot). Review 90
found that strict matching missed other word forms: with every concept's last English word in the
other plural form, strict scored 0.606 (14% empty) and prefix matching 0.685. A naive folding rule
(strip any -s/-es) let "notes" match "not" (Review 91); the shipped morphology-aware rule (-es only
after s/x/z/ch/sh, -y↔-ies, -ss/-us/-is and listed non-plurals untouched) scores 0.866 as written.
Concept-count dominance in ranking changed no result. Review 92 notes applied: -ics field names,
means/windows/pandas and generated non-plurals are protected ("k-means" no longer matches
"mean", "new york" no longer matches "News"), -ses plurals fold to -se (cases→case), -ch words
also take -s (epochs); the real-Vault figure is unchanged at 0.866.

**Footprint of the rejected semantic option** (measured in the scratch environment): onnxruntime
76 MB + numpy 22 MB + PIL 13 MB + tokenizers 10 MB + fastembed/huggingface_hub ≈ 4 MB, a 240 MB
quantised MiniLM model and a 76 MB embedding matrix for this Vault; the cross-encoder is 1.1 GB.

**What the failures taught.**

- Lexical rarity (IDF coverage, specificity floors, generic-word lists) cannot separate a topical
  common word ("learning") from a generic one ("training") or a compound ("machine translation")
  from its parts; every gate either empties long/task queries or keeps the leaks.
- Most of the relevance gain comes from the host's decomposition (b9 loose path with host concepts:
  0.834); the strict per-concept match is what removes leakage (83%→0%).
- Plain queries treated strictly lose recall (24% empty), so the b9 plain path stays.
- Semantic options gate leaks on plain queries (dense τ0.4 or a 1 GB cross-encoder: 67%→25%) but
  do not raise relevance; dense fill inside concept mode re-introduces leaks (50%).
- Remaining concept-mode weakness: bilingual alternates of a common concept outrank a rarer
  specific concept (mixed-language queries).

**Operational notes.** Hugging Face model files arrive via a Xet CDN; `huggingface_hub` hung on
the owner's network until `HF_HUB_DISABLE_XET=1`. Embedding ~46k unique short texts with
paraphrase-multilingual-MiniLM-L12 (ONNX, CPU) took 15.5 min and 76 MB; bge-reranker-base
re-scored 30 candidates in ~1.1 s per query.

**Open-source mechanisms inspected (source, not marketing).**

- Mem0 2.2.1 (`mem0/memory/main.py`, `mem0/utils/scoring.py`): candidates come only from vector
  search (over-fetch `max(4k, 60)`); BM25 over lemmatised text is squashed by a query-length-dependent
  sigmoid and *added*; an entity-link boost adds up to 0.5; the only gate is a low semantic threshold
  (0.1); rerankers are opt-in. Its precision rests on embeddings and LLM-extracted short memories.
- Graphiti 0.30.2 (`search/search_utils.py`, `search_config*.py`): BM25 (Lucene) + cosine
  (min 0.6) fused by RRF by default; MMR, node-distance and cross-encoder rerankers optional; again
  over LLM-extracted entities/edges.
- basic-memory 0.23.2 (`repository/sqlite_search_repository.py`, `search_repository_base.py`):
  SQLite FTS5 strict query with an OR-relaxed retry — the same shape as Aptuni's b8/b9 fallback —
  optional sqlite-vec semantic search (fastembed bge-small-en by default) fused as
  `max(vec, fts) + bonus·min(vec, fts)`, optional reranker.
- None solves generic-word leakage lexically; the transferable idea is to move query understanding
  to the component that has it. For Aptuni that is the calling Agent.
