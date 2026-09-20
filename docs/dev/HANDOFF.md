# Handoff

Review status manifest: architecture=APPROVE_WITH_NON_BLOCKING_NOTES; execution=APPROVE_WITH_NON_BLOCKING_NOTES; gate0-exit=APPROVE_WITH_NON_BLOCKING_NOTES; m1-advisor-catalog=APPROVE_WITH_NON_BLOCKING_NOTES; m1-ci-supply-chain=APPROVE_WITH_NON_BLOCKING_NOTES; m1-evaluation-harness=APPROVE; m1-github-source=APPROVE; m1-guided-setup=APPROVE; m1-marginnote4-source=APPROVE_WITH_NON_BLOCKING_NOTES; m1-memory-lifecycle=APPROVE_WITH_NON_BLOCKING_NOTES; m1-owner-backup-restore=APPROVE; m1-post-contract-skills=APPROVE; m1-privacy-purge=APPROVE_WITH_NON_BLOCKING_NOTES; m1-profile-export=APPROVE_WITH_NON_BLOCKING_NOTES; m1-slice1=APPROVE_WITH_NON_BLOCKING_NOTES; relay-claude-code=PASS; relay-codex=PASS; s05b-marginnote-reconciler=APPROVE_WITH_NON_BLOCKING_NOTES; security=APPROVE_WITH_NON_BLOCKING_NOTES

## Current position

Milestone 1. Runnable: Vault/CLI core; Folder, GitHub and direct local MarginNote 4 sources; builtin
interaction memory with quarantined MCP proposals; bilingual SQLite/FTS; bounded Context API; MCP
STDIO; Claude/Codex adapters; owner-readable Profile export; the Plugin Advisor; privacy
inventory/purge with atomic chain-preserving restore; digest-bound guided setup through doctor and
smoke; verified owner backup/restore; locally reviewed CI/supply-chain gates; the accepted versioned
production evaluation harness; and four executable post-contract agent skills. Slice 18 is
checkpointed at `884aabc`; Review 46 is **APPROVE**. Public `origin/main` is at `c86e861`. Hosted
run 35520369299 passed on macOS 15, Ubuntu 24.04/ext4 and the supply-chain job, closing Slice 15.

## Read first

1. `AGENTS.md`, `STATE.md` (next tasks), `KNOWN_ISSUES.md`, `BACKLOG.md`
2. `DECISIONS/` for the area you touch; `docs/research/INDEX.md` and `findings/pitfalls.md`
3. `docs/brand/BRAND_GUIDELINES.md` before README, docs or UI work

## Next action

Continue the authorized **Slice 17 — real-host S12 probes** from `spikes/s12_hosts/run_daily_task.py`
and `docs/dev/plans/12-real-host-s12.md`. Exact frozen packages are resolved through npm without
replacing global installs; sessions are non-persistent and data is synthetic. Diagnose the current
Claude nonzero exit and Codex missing tool evidence as launch/prompt/MCP-contract failures unless a
reproduction identifies an Aptuni defect. Persist only sanitized booleans, versions and reason codes.

`docs/dev/plans/07-m1-exit-matrix.md` audits every remaining M1 exit clause and orders Slices 14–18.
Keep all MarginNote access read-only; never commit note text, and do not infer release authorization.

### What just landed

Slice 15 hosted run 35520369299 passed at `c86e861`: 459 tests plus 47 subtests on Ubuntu, strict
typing and 34 developer checks, the 91-test/11-subtest ext4 durability gate, macOS 15, and the
supply-chain job are green. The two failures in initial run 35520200838 were portability defects in
the Darwin-only fsync constant typing and a repo-local `uv` fixture assumption; `c86e861` fixed both.

## Known constraints

- Do not push new commits without a fresh maintainer instruction. Toolchain: `.tools/bin/uv`
  (bootstrap in AGENTS.md).
- `Prompt_PRD.txt` and the design-history file are maintainer-private and gitignored;
  `docs/product/PRD.md` is canonical.
- Product/repository name Aptuni and `@ruihaomei` CODEOWNER are fixed. Private vulnerability
  reporting and name collision checks are release gates, not current blockers.
