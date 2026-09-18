# S03 — bilingual SQLite retrieval

Disposable Gate 0 evidence for ADR-0004. It compares SQLite FTS5 `unicode61`, `trigram`, and
`unicode61` over deterministic 2–4-character CJK lexemes without native extensions.

The evidence protocol is deliberately staged:

1. `FREEZE.json` fixes the synthetic corpus, query judgments, thresholds, generator, and metric
   definitions before comparison.
2. `python3.13 run_s03.py dev` compares all variants on the development split, measures each on
   25,000 documents, and writes the deterministic selection.
3. `python3.13 run_s03.py holdout` evaluates only that selection on the untouched holdout and exits
   non-zero on a missed relevance threshold.
4. After results exist, `python3.13 run_s03.py verify` is the read-only reproducibility command.

Do not delete or regenerate `results/holdout.json` to make another selection. A new corpus or metric
contract requires a new versioned spike, not an edit to this evidence set.

The spike uses only Python 3.13.3 stdlib SQLite 3.53.2. Run its tests from this directory:

```sh
python3.13 -m unittest discover -s tests -v
python3.13 run_s03.py verify
```

This is evidence, not production code. In particular, the synthetic corpus does not prove quality
on personal notes, and broad two-character terms can still admit top-5 distractors.
