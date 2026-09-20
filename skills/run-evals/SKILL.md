---
name: run-evals
description: This skill should be used when the user asks to "run the evaluations", "check retrieval quality", or produce Aptuni evaluation evidence.
---

# Run Aptuni Evaluations

## Goal

Run the frozen production retrieval evaluation and retain a reproducible, privacy-safe manifest.

## Boundaries

- Read `docs/dev/EVALUATION_PLAN.md` and `docs/dev/plans/10-versioned-evaluation-harness.md` before
  changing thresholds, corpora, metric definitions, or claims.
- Never edit a frozen input to make a run pass. A new protocol needs a new version and review.
- Keep dev and holdout results separate. Describe the corpus as synthetic and the context-noise case
  as a worked example, not measured user behavior.
- A missing or mismatched SBOM must block an SBOM-bound run; never omit it silently.

## Workflow

1. With the locked environment ready, run:

   ```sh
   mkdir -p artifacts
   .tools/bin/uv run --no-sync python tools/run_evals.py --output artifacts/eval-run.json
   ```

   Add `--sbom artifacts/aptuni.cdx.json` when supply-chain evidence exists.
2. On failure, inspect the named checksum or split/metric. Fix production behavior or intentionally
   version the protocol; do not weaken frozen evidence in place.
3. Preserve the JSON manifest with the commit, dirty state, lock/input hashes, environment, metrics,
   thresholds, and ranked outputs. Confirm it contains no private Vault data.
4. Run `tests/dev/test_run_evals.py` plus affected retrieval tests, then the full repository gate for
   code changes.

## Completion evidence

Report the manifest path, SBOM binding, dev and holdout metrics, context-noise arithmetic, commit and
dirty state, failures, and the exact limits on what the run proves.
