# Handoff

Review status manifest: architecture=APPROVE_WITH_NON_BLOCKING_NOTES; execution=APPROVE_WITH_NON_BLOCKING_NOTES; gate0-exit=APPROVE_WITH_NON_BLOCKING_NOTES; m1-advisor-catalog=APPROVE_WITH_NON_BLOCKING_NOTES; m1-github-source=APPROVE; m1-guided-setup=APPROVE; m1-marginnote4-source=APPROVE_WITH_NON_BLOCKING_NOTES; m1-memory-lifecycle=APPROVE_WITH_NON_BLOCKING_NOTES; m1-privacy-purge=APPROVE_WITH_NON_BLOCKING_NOTES; m1-profile-export=APPROVE_WITH_NON_BLOCKING_NOTES; m1-slice1=APPROVE_WITH_NON_BLOCKING_NOTES; relay-claude-code=PASS; relay-codex=PASS; s05b-marginnote-reconciler=APPROVE_WITH_NON_BLOCKING_NOTES; security=APPROVE_WITH_NON_BLOCKING_NOTES

## Current position

Milestone 1. Runnable: Vault/CLI core; Folder, GitHub and direct local MarginNote 4 sources; builtin
interaction memory with quarantined MCP proposals; bilingual SQLite/FTS; bounded Context API; MCP
STDIO; Claude/Codex adapters; owner-readable Profile export; the Plugin Advisor; privacy
inventory/purge with atomic chain-preserving restore; and digest-bound guided setup through doctor
and smoke. Review 34 independently closed guided setup **APPROVE** after Review 33's six blockers and
two follow-up crash/recovery defects were remediated. Nothing is pushed.

## Read first

1. `AGENTS.md`, `STATE.md` (next tasks), `KNOWN_ISSUES.md`, `BACKLOG.md`
2. `DECISIONS/` for the area you touch; `docs/research/INDEX.md` and `findings/pitfalls.md`
3. `docs/brand/BRAND_GUIDELINES.md` before README, docs or UI work

## Next action

Audit the remaining M1.1/M1.3/M1.4/M1.5 exit matrix and write the accepted TDD plan that maps every
open binary gate to evidence or one bounded vertical slice. Then execute the first dependency-ready
slice. The known gaps are backup/restore/migration drills, the versioned evaluation harness, S12
real-host probes, clean artifact/SBOM/license/security gates, and the four post-contract skills.
Keep all MarginNote access read-only; never commit note text, and do not infer release authorization.

### What just landed

Slice 13 adds `aptuni setup plan` and `aptuni setup apply ACTION_ID`: an immutable catalog- and
answer-bound plan, exact Folder/GitHub/MarginNote source consent, complete egress and host-file
disclosure, one honest terminal confirmation, journaled/resumable effects, adapter-bundle repair,
doctor/smoke, and truthful cancellation that revokes only action-owned grants. `local_only` creates
no host egress. The full gate is 393 tests plus 47 subtests, focused setup is 51 tests, ruff/mypy are
clean, and Review 34 is APPROVE with no remaining findings. Review 33 remains the historical BLOCK
report and is superseded in `docs/dev/reviews/STATUS.json`.

## Known constraints

- Commits are local only; never push. Toolchain: `.tools/bin/uv` (bootstrap in AGENTS.md).
- `Prompt_PRD.txt` and the design-history file are maintainer-private and gitignored;
  `docs/product/PRD.md` is canonical.
- Product/repository name Aptuni and `@ruihaomei` CODEOWNER are fixed. Private vulnerability
  reporting and name collision checks are release gates, not current blockers.
