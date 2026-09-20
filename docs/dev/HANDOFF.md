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

Continue **Slice 17 — real-host S12 probes** with the focused Claude built-in Read/Write and Apple
Event observations. The four-version daily-task matrix already passes and is recorded at
`spikes/s12_hosts/results/daily-task-matrix.json`. Persist only sanitized booleans, versions and
reason codes; never retain auth material, raw host output or private Vault content.

`docs/dev/plans/07-m1-exit-matrix.md` audits every remaining M1 exit clause and orders Slices 14–18.
Keep all MarginNote access read-only; never commit note text, and do not infer release authorization.

### What just landed

Slice 17's frozen daily-task matrix passes on Claude Code 2.1.267/2.1.266 and Codex
0.155.0/0.154.0. Fixes preserve `USER` for Claude keychain discovery, hide expected tokens from the
prompt, require structured Codex tool evidence, and make the Codex MCP server required with only
`APTUNI_STATE_DIR` forwarded. Full local gate: 459 tests plus 47 subtests, ruff, mypy, relay and 34
developer checks clean.

## Known constraints

- Do not push new commits without a fresh maintainer instruction. Toolchain: `.tools/bin/uv`
  (bootstrap in AGENTS.md).
- `Prompt_PRD.txt` and the design-history file are maintainer-private and gitignored;
  `docs/product/PRD.md` is canonical.
- Product/repository name Aptuni and `@ruihaomei` CODEOWNER are fixed. Private vulnerability
  reporting and name collision checks are release gates, not current blockers.
