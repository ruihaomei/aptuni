# Review 40 — M1 CI and supply-chain review

**Date:** 2026-09-20

**Reviewer:** independent correctness and supply-chain review agent (read-only)

**Scope:** the uncommitted Slice 15 workflow, dependency and legal inventory gates, secret scanner,
reproducible build, clean-wheel smoke, and Linux/ext4 filesystem admission.

## Validation and positives

- The runtime closure matched `uv export`, including `PyJWT[crypto]`, Windows `pywin32`, and
  Emscripten `httpx2-jsfetch`.
- Action references were immutable SHA pins, workflow permissions were read-only, checkout did not
  persist credentials, and local double-build/legal-file checks passed.
- The mountinfo parser regressions and local APFS filesystem gate passed.

## Blocking findings

1. `hatchling>=1.27` was resolved by isolated `uv build` outside `uv.lock`; two builds could agree
   while executing the same newly drifted backend.
2. `uvx pip-audit` resolved its own code outside the lock, while clean-wheel installation freshly
   resolved application dependencies instead of executing the audited/SBOM set.
3. The high-confidence secret scanner missed AWS temporary `ASIA` keys, GitHub fine-grained
   `github_pat_` tokens, and OpenAI project `sk-proj-` keys; direct probes returned no findings.
4. No hosted workflow run exists, so Ubuntu/ext4 durability evidence remains pending and Linux
   support must not yet be claimed.

**Verdict:** **BLOCK**
