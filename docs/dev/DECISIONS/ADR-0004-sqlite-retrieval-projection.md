# ADR-0004: Use SQLite as the builtin retrieval projection

- **Status:** Accepted (2026-09-19, Gate 0 exit review 15)
- **Date:** 2026-09-18
- **Deciders:** maintainer (final say) · proposing agent · reviewing agent(s)
- **PRD refs:** §18–§19, §30, §43, §46, §48
- **Research refs:** `docs/research/upstream/local-retrieval-and-packaging.md`
- **Needs maintainer confirmation:** no

## Context

MVP needs local, no-key bilingual retrieval. SQLite FTS5 is available, but its built-in tokenizers
do not by themselves give reliable Chinese and English relevance: `unicode61` does not segment a
Chinese run and `trigram` misses two-character queries while increasing substring noise.

## Decision drivers

- Local installability and rebuildability
- Chinese and English relevance
- Token-efficient progressive disclosure

## Options considered

### A — FTS5 `trigram` only

Simple, but weak on short Chinese terms and noisy English substrings.

### B — `unicode61` plus deterministic application-generated CJK lexemes

Portable and controllable, but adds index-time/query-time normalization logic.

### C — Add a segmentation/native extension dependency

Potentially better language quality, but increases packaging and platform risk.

## Decision

Use SQLite as a disposable retrieval projection. Select **B provisionally**, subject to the bilingual
retrieval spike. Index canonical IDs, modules, normalized text, provenance facets, temporal state,
and permission state; return IDs and scores, then hydrate canonical records. Never return a disabled
module, expired state when current state was requested, or content outside the caller's budget.

Keep `RetrieverProvider` independent so hybrid, LlamaIndex, or graph retrieval can arrive later.
Embeddings are not required for MVP.

## Consequences

- **Positive:** Zero-service default and transparent rebuilds.
- **Negative / risks:** Custom CJK lexeme quality must be measured; ranking remains modest.
- **Follow-ups:** Freeze a bilingual golden corpus before schema implementation.

## Verification

Spike compares `unicode61`, `trigram`, and deterministic CJK n-grams on recall@k, noise, latency,
database size, and two-character queries. Permission and temporal filters get mandatory tests.

## Amendments

### 2026-09-19 — Gate 0 acceptance

Accepted with option B final: SQLite FTS5 `unicode61` over normalized ASCII terms plus overlapping 2–4-character CJK lexemes (S03: dev recall@5 0.992, MRR 1.0, holdout 1.0, 25k-document p95 1.93 ms, index/text ratio 6.85). The "noisy English substrings" concern about trigram is not supported by S03 (trigram negative FPR 0.000 on that corpus). Carried limits: synthetic corpus, broad short-query noise (KI-018), and exposed index size with rebuild.

### 2026-09-19 — Ranked any-term fallback for task-shaped queries

Dogfooding the README quickstart showed that all-terms (`AND`) matching returns nothing for natural
requests such as "help me prepare for a data science interview" or "教我生存分析", so the Context API
starved on the PRD's own examples. Search now runs the S03 all-terms query first and, only when it
fills fewer than `limit` slots, adds bm25-ranked any-term (`OR`) matches over stopword-filtered
lexemes, keeping those scoring at least 25% of the best fallback hit. The lexeme scheme is unchanged
(S03 evidence stays valid); all-terms hits always rank first; permission filters and final hydration
checks are unchanged. Broad-query noise remains tracked by KI-018 and needs dogfood judgments.
