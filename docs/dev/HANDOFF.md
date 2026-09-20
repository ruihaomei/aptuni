# Handoff

Review status manifest: architecture=APPROVE_WITH_NON_BLOCKING_NOTES; execution=APPROVE_WITH_NON_BLOCKING_NOTES; gate0-exit=APPROVE_WITH_NON_BLOCKING_NOTES; m1-advisor-catalog=APPROVE_WITH_NON_BLOCKING_NOTES; m1-ci-supply-chain=APPROVE_WITH_NON_BLOCKING_NOTES; m1-evaluation-harness=APPROVE; m1-github-source=APPROVE; m1-guided-setup=APPROVE; m1-marginnote4-source=APPROVE_WITH_NON_BLOCKING_NOTES; m1-memory-lifecycle=APPROVE_WITH_NON_BLOCKING_NOTES; m1-owner-backup-restore=APPROVE; m1-privacy-purge=APPROVE_WITH_NON_BLOCKING_NOTES; m1-profile-export=APPROVE_WITH_NON_BLOCKING_NOTES; m1-slice1=APPROVE_WITH_NON_BLOCKING_NOTES; relay-claude-code=PASS; relay-codex=PASS; s05b-marginnote-reconciler=APPROVE_WITH_NON_BLOCKING_NOTES; security=APPROVE_WITH_NON_BLOCKING_NOTES

## Current position

Milestone 1. Runnable: Vault/CLI core; Folder, GitHub and direct local MarginNote 4 sources; builtin
interaction memory with quarantined MCP proposals; bilingual SQLite/FTS; bounded Context API; MCP
STDIO; Claude/Codex adapters; owner-readable Profile export; the Plugin Advisor; privacy
inventory/purge with atomic chain-preserving restore; digest-bound guided setup through doctor and
smoke; verified owner backup/restore; locally reviewed CI/supply-chain gates; and the accepted
versioned production evaluation harness. Slice 16 is checkpointed at `390aaf6`; Review 44 is
**APPROVE** after frozen-input mutation and failure-evidence retention fixes. Nothing is pushed and
no remote is configured, so the Slice 15 Ubuntu 24.04/ext4 evidence remains pending and Linux
support is not claimed.

## Read first

1. `AGENTS.md`, `STATE.md` (next tasks), `KNOWN_ISSUES.md`, `BACKLOG.md`
2. `DECISIONS/` for the area you touch; `docs/research/INDEX.md` and `findings/pitfalls.md`
3. `docs/brand/BRAND_GUIDELINES.md` before README, docs or UI work

## Next action

Run **Slice 17 — real-host S12 probes** only with maintainer-authorized Claude Code and Codex hosts,
credentials/quota and a recorded daily task. If that external gate is unavailable, implement
**Slice 18 — post-contract skills**, whose backup/eval/supply contracts are now stable. Separately, a
maintainer must configure/push to a remote and record the successful Slice 15 Ubuntu job before any
Linux support claim; agents must not push.

`docs/dev/plans/07-m1-exit-matrix.md` audits every remaining M1 exit clause and orders Slices 14–18.
Keep all MarginNote access read-only; never commit note text, and do not infer release authorization.

### What just landed

Slice 16 adds `tools/run_evals.py`, frozen-input and checksum mutations, SBOM-bound run manifests,
failure-safe CI evidence retention and a task-language-gated retrieval fallback. The real synthetic
run passes dev and holdout relevance/FPR gates; the context-noise arithmetic reproduces exactly.
The full gate is 459 tests plus 47 subtests; ruff, strict mypy, 32 developer checks and relay are
clean. Review 44 is **APPROVE**.

## Known constraints

- Commits are local only; never push. Toolchain: `.tools/bin/uv` (bootstrap in AGENTS.md).
- `Prompt_PRD.txt` and the design-history file are maintainer-private and gitignored;
  `docs/product/PRD.md` is canonical.
- Product/repository name Aptuni and `@ruihaomei` CODEOWNER are fixed. Private vulnerability
  reporting and name collision checks are release gates, not current blockers.
