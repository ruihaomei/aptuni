# MVP Evaluation Plan

**Status:** Proposed Gate for M1.3+
Fixtures, judgments, metric code, thresholds, and holdouts must be checksummed/committed before the
first scored run. Changing them requires a recorded rationale and a fresh baseline.

## Automated release gates

| Dimension | Definition | MVP threshold |
|---|---|---|
| Unsupported profile claims | exposed Fact/Memory statements without a valid canonical lineage to evidence/review | 0 on golden/adversarial corpus |
| Provenance coverage | exposed L3/L4 records with resolvable source/episode/review lineage ÷ all exposed L3/L4 records | 100% |
| Permission correctness | forbidden module/source/host disclosures or writes across policy matrix | 0 violations |
| Retention/purge correctness | marker occurrences in managed copy classes after terminal managed purge/restore | 0; partial states must not claim completion |
| Temporal correctness | correct answer on world-change/correction/out-of-order/as-known-at cases | 100% on invariants; ≥95% on query corpus |
| Source update correctness | expected idempotent/move/edit/delete/reappear/ambiguity outcomes | 100% fixture cases |
| Backend portability | canonical semantic hash unchanged and accepted memory/profile view reproduced after projection rebuild/switch | 100% |
| Plugin conformance | mandatory contract cases passed by builtin/fixture provider | 100%; no waived security case |
| Retrieval relevance | recall@5 / MRR on frozen bilingual holdout | ≥0.85 / ≥0.70, with every short-CJK blocking case found |
| Context noise | judged irrelevant response units ÷ total response units returned (definitions below) | ≤15% median, ≤25% p95 |
| Budget correctness | response units over requested budget or missing truncation/layer markers | 0 |
| Bilingual parity | semantic scenario assertions passing in both locales | 100%; no untranslated message keys |
| Setup success | eligible success cases completing ÷ eligible success cases; separately, expected safe-refusal cases correctly refusing ÷ refusal cases | 100% / 100%; refusal never counts as successful setup |

### Context-noise definitions (frozen before M1.3 thresholds)

- **Judged unit:** one returned record (an L3 fact/memory or L4 evidence item) or one L0/L1/L2 section.
  Its response units are its UTF-8 payload bytes plus the ADR-0005 fixed overhead, pinned at
  **32 units per record/section** (changing it needs an ADR amendment and a re-baselined holdout).
- **Empty output:** a correct empty answer (no relevant item exists) scores 0% noise and is counted in
  a separate "correct-empty" tally; an empty answer when relevant items exist is a recall failure,
  never a noise pass.
- **Judging:** two independent judges label each unit relevant/irrelevant against the versioned task;
  disagreements go to a third judge or the maintainer; unresolved ties count as irrelevant.
- **Worked example:** `tests/fixtures/eval/context-noise-example-v1.json` with its checksum is added in
  the M1.3 plan before thresholds freeze; runners must reproduce its score exactly.

## Human/dogfood scorecard

These are reported, not silently converted into objective human-competence scores.

| Signal | Measurement |
|---|---|
| Memory precision | accepted candidate memories ÷ reviewed candidate memories; also report count and rejection reasons |
| Memory recall | required known memories retrieved ÷ judged relevant known memories on versioned tasks |
| Preference adaptation | correct preference use without unrelated preference injection; per-task rubric |
| Time to first useful personalization | start of setup → first maintainer-rated useful result; median and raw sample count |
| Setup friction | elapsed time, questions, manual repairs, cancellations, and undisclosed decisions |
| Review burden | candidates reviewed per useful accepted memory and time spent |

Dogfood results must retain denominators and confidence caveats. One maintainer session is qualitative
evidence, not a population claim.

## Corpus and run discipline

- Use synthetic/licensed content plus sanitized maintainer fixtures; never commit private raw exports.
- Include English, Simplified Chinese, mixed-language queries, CJK paths, conflicting authorities,
  stale policies, adversarial instructions, temporal corrections, and unsupported expertise claims.
- Separate development and untouched holdout slices. Metric code exits non-zero on any automated gate.
- Store machine-readable run manifest: commit, schema versions, dependency lock/SBOM hash, OS/Python/
  SQLite/host versions, locale, seed, fixture checksum, thresholds, and outputs.
- Any failed blocking metric keeps the milestone open; exceptions require an ADR/review, never a
  threshold edited after seeing results.
