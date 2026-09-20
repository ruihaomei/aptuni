# Handoff

Review status manifest: architecture=APPROVE_WITH_NON_BLOCKING_NOTES; execution=APPROVE_WITH_NON_BLOCKING_NOTES; gate0-exit=APPROVE_WITH_NON_BLOCKING_NOTES; m1-advisor-catalog=APPROVE_WITH_NON_BLOCKING_NOTES; m1-github-source=APPROVE; m1-guided-setup=APPROVE; m1-marginnote4-source=APPROVE_WITH_NON_BLOCKING_NOTES; m1-memory-lifecycle=APPROVE_WITH_NON_BLOCKING_NOTES; m1-owner-backup-restore=APPROVE; m1-privacy-purge=APPROVE_WITH_NON_BLOCKING_NOTES; m1-profile-export=APPROVE_WITH_NON_BLOCKING_NOTES; m1-slice1=APPROVE_WITH_NON_BLOCKING_NOTES; relay-claude-code=PASS; relay-codex=PASS; s05b-marginnote-reconciler=APPROVE_WITH_NON_BLOCKING_NOTES; security=APPROVE_WITH_NON_BLOCKING_NOTES

## Current position

Milestone 1. Runnable: Vault/CLI core; Folder, GitHub and direct local MarginNote 4 sources; builtin
interaction memory with quarantined MCP proposals; bilingual SQLite/FTS; bounded Context API; MCP
STDIO; Claude/Codex adapters; owner-readable Profile export; the Plugin Advisor; privacy
inventory/purge with atomic chain-preserving restore; and digest-bound guided setup through doctor
and smoke; and verified owner backup/restore. Slice 14 is implementation-complete and Review 39 is
**APPROVE** after fresh-state crash injection proved the canonical ledger and restore journal cannot
diverge. Its local checkpoint is being recorded. Nothing is pushed.

## Read first

1. `AGENTS.md`, `STATE.md` (next tasks), `KNOWN_ISSUES.md`, `BACKLOG.md`
2. `DECISIONS/` for the area you touch; `docs/research/INDEX.md` and `findings/pitfalls.md`
3. `docs/brand/BRAND_GUIDELINES.md` before README, docs or UI work

## Next action

Implement **Slice 15 — CI and supply-chain gates** from the accepted exit matrix: recorded
unit/integration/lint/type checks, clean-wheel install, reproducible build, SBOM/license/vulnerability/
secret checks, and Ubuntu LTS/ext4 S01 evidence. Do not claim Linux support until that runner passes.

`docs/dev/plans/07-m1-exit-matrix.md` audits every remaining M1 exit clause and orders Slices 14–18.
Keep all MarginNote access read-only; never commit note text, and do not infer release authorization.

### What just landed

Slice 14 adds manifest-verified `aptuni backup create | verify | list | restore`, exact expiring
preview/confirm/cancel, canonical deletion-ledger migration and a canonical in-flight restore
journal. Restore unions deletions from both sides and remains atomic even if the original disposable
state directory disappears mid-publication. The full gate is 456 tests plus 47 subtests; backup +
Vault focused suites are 84; ruff, strict mypy and relay validation are clean. Review 39 is
**APPROVE**. Real CLI cross-machine dogfood restored a pre-purge backup without resurrecting the
purged marker, kept the survivor and passed `doctor`.

## Known constraints

- Commits are local only; never push. Toolchain: `.tools/bin/uv` (bootstrap in AGENTS.md).
- `Prompt_PRD.txt` and the design-history file are maintainer-private and gitignored;
  `docs/product/PRD.md` is canonical.
- Product/repository name Aptuni and `@ruihaomei` CODEOWNER are fixed. Private vulnerability
  reporting and name collision checks are release gates, not current blockers.
