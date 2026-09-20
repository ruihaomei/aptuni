# Review 43 — M1 evaluation harness focused re-review

**Date:** 2026-09-20

Review 42's freeze-mutation and holdout-lifecycle blockers are closed. The real workflow also has a
correct `always() && hashFiles(...)` upload immediately after evaluation. However, the local
workflow contract checker searched independently for the condition and evaluator invocation; moving
the condition to a no-op step or changing the uploader path still passed. This left the required
failure-evidence retention unprotected against workflow drift.

**Verdict:** **BLOCK**
