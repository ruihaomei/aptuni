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
