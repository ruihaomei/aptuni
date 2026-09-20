# Review 45 remediation — M1 post-contract skills

- **Responds to:** `45-m1-post-contract-skills-review.md`
- **Date:** 2026-09-20

Both `run-evals` and `audit-licenses` now require the already prepared locked environment and use
`uv run --no-sync`; their executable fixtures enforce the same command shape. The integrity test
also checks the currently referenced root and `.github/` files, and every fixture declares a trigger
phrase that must appear in its skill description.
