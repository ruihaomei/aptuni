# S03 result — bilingual SQLite retrieval

**Result:** PASS

**Run date:** 2026-09-19

**Baseline:** CPython 3.13.3 · SQLite 3.53.2 with FTS5 · macOS/APFS Gate 0 host

**ADR impact:** supports ADR-0004 option B; keep the ADR `Proposed` until the batched independent
spike-evidence review.

## Frozen protocol

As attested by the author (the freeze, results and code landed in one commit, so git history
cannot prove the ordering; review 15), before comparison `spikes/s03_fts/FREEZE.json` fixed SHA-256 digests for the 250-document synthetic
Chinese-English corpus, 73 judged queries (58 development, 15 holdout), numeric thresholds, corpus
generator, and metric implementation. Tests prove changed or missing inputs stop the run.

The precommitted selection rule admits only variants clearing every development and 25,000-document
scale threshold, then orders eligible variants by recall@5, MRR, short-CJK found rate, lower negative
false-positive rate, and finally variant name. The holdout was opened only after that rule selected
`cjk_lexemes`; only the selected variant was evaluated on holdout.

## Results

| Variant | Dev recall@5 | Dev MRR | Two-char found | Negative FPR | p95 ms (25k) | Index/text ratio | Gate |
|---|---:|---:|---:|---:|---:|---:|---|
| `unicode61` | 0.431 | 0.431 | 0.000 | 0.000 | 0.60 | 2.27 | FAIL |
| `trigram` | 0.784 | 0.784 | 0.000 | 0.000 | 1.85 | 5.29 | FAIL |
| `cjk_lexemes` | 0.992 | 1.000 | 1.000 | 0.000 | 1.93 | 6.85 | PASS / selected |

The selected variant's holdout recall@5, MRR, and short-CJK found rate were each 1.000; negative FPR
was 0.000. It cleared all frozen gates: recall@5 ≥0.85, MRR ≥0.70, every short-CJK case found,
negative FPR ≤0.10, p95 ≤50 ms, and index/text ratio ≤10.

## Error analysis and limits

- `unicode61` treats unsegmented Chinese runs too coarsely. `trigram` cannot answer two-character
  Chinese terms and also missed the short mixed query `CT图像`.
- `cjk_lexemes` missed two relevant top-5 slots in development: broad `森林` and `生存` queries each
  admitted the synthetic hiking/game distractor. The aggregate metric passes, but the result does
  **not** prove the later context-noise target.
- The templated synthetic corpus is reproducible and license-clean, but easier than personal notes.
  M1 must add dogfood regression judgments and retain per-result noise measurement before claiming
  user-facing retrieval quality.
- The chosen index is about 6.85× the UTF-8 source-text bytes. This is under the gate but materially
  larger than the other variants; production must expose index size and support rebuilds.
- Latency is a warm local measurement on one APFS host, not a power-loss, cold-cache, or Linux result.

## Conclusion

Use SQLite FTS5 `unicode61` over deterministic normalized ASCII terms and overlapping 2–4-character
CJK lexemes as the builtin MVP projection. Keep canonical records outside the index, apply mandatory
permission/current-state filters, and hydrate only canonical IDs. Do not add a segmentation package
for MVP. Carry the broad-short-query noise and synthetic-corpus generalization limits into M1 tests.

Machine-readable evidence is under `spikes/s03_fts/results/`; from that spike directory, the
read-only verification command is `/opt/homebrew/bin/python3.13 run_s03.py verify`.
