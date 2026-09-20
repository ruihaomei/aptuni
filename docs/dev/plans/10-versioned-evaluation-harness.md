# Slice 16 — Versioned evaluation harness

**Status:** Complete locally (2026-09-20; Review 44 APPROVE)
**Owns:** M1.3 evaluation-plan acceptance; frozen production retrieval relevance; reproducible run
manifests. It does not convert qualitative dogfood signals into population claims.

## Runnable outcome

`python tools/run_evals.py [--sbom PATH] [--output PATH]` verifies the precommitted S03 corpus,
queries, thresholds, metric sources and the context-noise worked example before scoring Aptuni's
production SQLite retriever. It exits non-zero on input drift or any blocking threshold miss and can
write one atomic machine-readable run manifest.

CI runs the command from its locked environment after generating the CycloneDX SBOM and retains the
manifest with the verified distributions. The manifest records the commit/dirty state, package and
evaluator versions, schema/lexeme versions, lock/SBOM/input hashes, OS/Python/SQLite, locales, seed,
thresholds, aggregate metrics and per-query ranked outputs.

## Frozen inputs

- `spikes/s03_fts/FREEZE.json` protects the 240-document synthetic bilingual corpus, 73 dev/holdout
  queries, thresholds and original metric definitions. The holdout was already opened and recorded
  during S03; Slice 16 treats it only as a regression split and keeps dev/holdout results separate.
- `tests/fixtures/eval/context-noise-example-v1.json` and its companion checksum protect the judged
  unit arithmetic and reproduce 328 total units, 82 irrelevant units and a 0.25 ratio.
- Thresholds remain the values committed before S03 selection: recall@5 ≥0.85, MRR ≥0.70, every
  two-character CJK blocking case found, and false-positive rate ≤0.10 on each split.

## Acceptance

1. Mutating any frozen input or companion checksum blocks before scoring.
2. Production retrieval, not the disposable spike implementation, supplies ranked results.
3. Dev and holdout thresholds pass; negative queries count every non-empty result as a false
   positive and correct empty results never become a noise pass substitute.
4. A compact query without task-language stopwords never silently degrades into broad any-term
   matching; the natural task-shaped English and Chinese fallbacks continue to work.
5. The context-noise example reproduces its checksum and exact arithmetic.
6. The JSON manifest has enough hashes, versions, thresholds and outputs to identify a run without
   containing private profile data.
7. CI produces and retains a manifest tied to its generated SBOM from the first committed harness;
   a written failing-threshold manifest uploads under `always()` before the job stops.
8. `EVALUATION_PLAN.md` becomes Accepted only after an independent review finds no blocking metric,
   corpus-integrity, privacy or claim defect.

## Non-goals

- Replacing existing permission, purge, temporal, source-update, portability, plugin or setup test
  matrices with one synthetic score.
- Claiming retrieval quality beyond this synthetic corpus or treating the context-noise worked
  example as a measured distribution.
- Automating human/dogfood scorecards or host journeys.
